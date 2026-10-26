"""Conditional price scenarios, independent of the long-term FCFF model."""
from datetime import datetime, timezone
import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .horizon import HorizonCode, investment_horizon


class PriceCase(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, str_strip_whitespace=True)
    forward_eps: float = Field(gt=0)
    pe: float = Field(gt=0)
    dividends_per_share: float = Field(ge=0)
    rationale: str = Field(min_length=30, max_length=4000)
    invalidation: str = Field(min_length=20, max_length=2000)


class PriceCases(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bear: PriceCase
    base: PriceCase
    bull: PriceCase


class PriceScenarioRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    symbol: str = Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    currency: str = Field(pattern=r'^[A-Z]{3}$')
    horizon: HorizonCode = '3-6m'
    three_months: PriceCases | None = None
    six_months: PriceCases | None = None
    catalyst_ids: list[str] = Field(default_factory=list, max_length=20)
    research_id: str | None = Field(default=None, max_length=100)

    @model_validator(mode='after')
    def horizons_match(self):
        if (self.three_months is not None) != (self.horizon in ('3m', '3-6m')):
            raise ValueError('Los casos a 3 meses deben coincidir con el horizonte elegido')
        if (self.six_months is not None) != (self.horizon in ('6m', '3-6m')):
            raise ValueError('Los casos a 6 meses deben coincidir con el horizonte elegido')
        if len(self.catalyst_ids) != len(set(self.catalyst_ids)):
            raise ValueError('No repitas un catalizador')
        return self


def calculate_price_scenarios(request, quote, catalysts=None, asof=None):
    asof = asof or datetime.now(timezone.utc)
    if asof.tzinfo is None:
        asof = asof.replace(tzinfo=timezone.utc)
    if quote.get('currency') != request.currency:
        raise ValueError('La divisa del EPS y dividendos debe coincidir con la cotización del instrumento')
    timestamp = datetime.fromisoformat(quote['timestamp'])
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    age = (asof - timestamp).total_seconds()
    if not -300 <= age <= 7 * 86400:
        raise ValueError('Se necesita una cotización de hasta 7 días y sin fecha futura')
    price = quote['price']
    if not math.isfinite(price) or price <= 0:
        raise ValueError('Se necesita un precio de referencia positivo')
    catalysts = catalysts or []
    event_ids = [event['event_id'] for event in catalysts]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError('Dos versiones del mismo evento no pueden contarse como catalizadores distintos')
    horizons = {}
    for months, group in ((3, request.three_months), (6, request.six_months)):
        if group is None:
            continue
        context = investment_horizon(f'{months}m', asof)
        cases = {}
        for name in ('bear', 'base', 'bull'):
            case = getattr(group, name)
            target = case.forward_eps * case.pe
            total = target + case.dividends_per_share
            if not all(math.isfinite(value) for value in (target, total, total / price, (price - case.dividends_per_share) / case.forward_eps)):
                raise ValueError('Los supuestos exceden el rango numérico admitido')
            cases[name] = {
                'inputs': case.model_dump(), 'price': target,
                'price_return': target / price - 1,
                'gross_return_with_dividends': total / price - 1,
                'breakeven_pe': (price - case.dividends_per_share) / case.forward_eps if price >= case.dividends_per_share else None,
            }
        if any(cases[a]['price'] > cases[b]['price'] or cases[a]['gross_return_with_dividends'] > cases[b]['gross_return_with_dividends'] for a, b in (('bear', 'base'), ('base', 'bull'))):
            raise ValueError('Ordena los casos: bajista ≤ base ≤ alcista en precio y retorno con dividendos')
        downside = cases['bear']['gross_return_with_dividends']
        upside = cases['bull']['gross_return_with_dividends']
        reward_risk = upside / abs(downside) if downside < 0 < upside else None
        if reward_risk is not None and not math.isfinite(reward_risk):
            reward_risk = None
        horizons[str(months)] = {
            'target_date': context['window_end_date'], 'cases': cases,
            'conditional_reward_risk': reward_risk,
            'reward_risk_interpretation': 'Retorno alcista / pérdida absoluta bajista, solo cuando existe ganancia y pérdida. No es una expectativa estadística.',
        }
    return {
        'model_version': 'price-horizon-1.0', 'record_type': 'price_scenario',
        'symbol': request.symbol, 'currency': request.currency,
        'created_at': asof.isoformat(), 'inputs': request.model_dump(),
        'investment_horizon': investment_horizon(request.horizon, asof),
        'reference_quote': quote, 'catalysts': catalysts, 'horizons': horizons,
        'formula': 'Precio condicional = EPS forward 12 meses en la fecha objetivo × P/E supuesto; retorno bruto = (precio condicional + dividendos del horizonte) / precio inicial − 1.',
        'limitations': [
            'Supuestos introducidos por el usuario, no consenso, previsión IA ni recomendación.',
            'El EPS corresponde a los 12 meses siguientes a la fecha objetivo; no es el beneficio de 3 o 6 meses ni se obtiene prorrateando el anual.',
            'EPS y dividendos deben corresponder a la misma acción/ADR y divisa que la cotización, sin conversión automática.',
            'Dividendos hipotéticos en efectivo, sin reinversión, impuestos, comisiones ni ajuste automático por splits.',
            'P/E con EPS positivo; empresas en pérdidas requieren otro método, todavía no implementado.',
            'Sin probabilidades ni retorno esperado ponderado. Los catalizadores son referencias y no se suman automáticamente al EPS.',
        ],
    }
