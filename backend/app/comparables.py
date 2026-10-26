"""Conditional relative valuation from explicitly selected, auditable peer snapshots."""
import math
from datetime import datetime, timezone, date
from statistics import median
import numpy as np
from pydantic import BaseModel,ConfigDict,Field,model_validator
from typing import Literal
from .analytics import number
from .finance import ratios
from .store import now


class ComparableRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,str_strip_whitespace=True)
    target:str=Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    peers:list[str]=Field(min_length=2,max_length=8)
    metric:Literal['pe','ev_ebitda','ev_revenue','p_fcf']='pe'
    basis:Literal['annual','ttm']='annual'
    rationale:str=Field(min_length=30,max_length=4000)
    research_id:str|None=Field(default=None,max_length=100)

    @model_validator(mode='after')
    def distinct(self):
        import re
        if len(set(self.peers))!=len(self.peers) or self.target in self.peers:raise ValueError('Selecciona pares distintos y excluye la empresa objetivo')
        if any(not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',s) for s in self.peers):raise ValueError('Ticker de comparable no válido')
        return self


def evaluate(snapshot,metric,basis,asof):
    if snapshot.get('error'):return {'symbol':snapshot['symbol'],'eligible':False,'reasons':[snapshot['error']]}
    company=snapshot['company'];quote=snapshot.get('quote')
    period=company.get('ttm') if basis=='ttm' else next(iter(company.get('statements',[])),None)
    reasons=[]
    try:financial=6000<=int(company.get('sic') or 0)<=6999
    except ValueError:financial=False
    if financial and metric!='pe':reasons.append('Entidad financiera: este múltiplo industrial requiere un modelo sectorial específico')
    if not period:reasons.append('No hay datos para la base seleccionada')
    if not quote:reasons.append('No hay cotización')
    if quote and quote.get('currency')!=company.get('currency'):reasons.append('Precio y estados en distinta divisa; no hay conversión implícita')
    if company.get('multiple_share_classes'):reasons.append('No se han asignado las acciones a esta clase cotizada')
    if quote:
        timestamp=datetime.fromisoformat(quote['timestamp'])
        if timestamp.tzinfo is None:timestamp=timestamp.replace(tzinfo=timezone.utc)
        age=(asof-timestamp).total_seconds()/86400
        if age>7 or age<-(5/1440):reasons.append('Cotización de más de siete días o fecha futura')
    metrics={};multiple=None
    if period:
        age=(asof.date()-date.fromisoformat(period['end'])).days
        if age<0 or age>(550 if basis=='annual' else 200):reasons.append('Período financiero fuera del rango de antigüedad admitido')
        v=period['values']
        earnings_key='net_income_owners' if number(v,'net_income_owners') is not None else 'net_income'
        needed=['shares']+([earnings_key] if metric=='pe' else ['ocf','capex'] if metric=='p_fcf' else ['ebit','da','debt','cash'] if metric=='ev_ebitda' else ['revenue','debt','cash'])
        balances={'debt','cash','shares'}
        start=v.get('revenue',{}).get('period_start') if isinstance(v.get('revenue'),dict) else None
        for key in needed:
            fact=v.get(key)
            if not isinstance(fact,dict) or not fact.get('source') or not fact.get('filed'):
                reasons.append('Falta procedencia verificable para '+key);continue
            if fact.get('currency') and fact['currency']!=company.get('currency'):reasons.append('Divisa de partida incompatible: '+key)
            if fact.get('period_end') and fact['period_end']!=period['end']:reasons.append('Cierre de partida incompatible: '+key)
            if key not in balances and start and fact.get('period_start') and fact['period_start']!=start:reasons.append('Duración de partida incompatible: '+key)
            if fact['filed']>asof.date().isoformat() or fact['filed']<period['end']:reasons.append('Fecha de presentación incompatible: '+key)
        metrics=ratios(v,quote['price'] if quote and quote.get('currency')==company.get('currency') else None)
        shares=number(v,'shares')
        if shares is None or shares<=0:reasons.append('Acciones diluidas medias no disponibles o no positivas')
        multiple=metrics.get(metric)
        if multiple is None or not math.isfinite(multiple) or multiple<=0:reasons.append('Múltiplo no positivo o inputs insuficientes; no se utiliza un denominador negativo')
    return {'symbol':company['symbol'],'name':company.get('name'),'sic':company.get('sic'),'industry':company.get('industry'),'currency':company.get('currency'),'period_end':period['end'] if period else None,'multiple':multiple,'eligible':not reasons,'reasons':reasons,'operating_margin':metrics.get('operating_margin'),'net_margin':metrics.get('net_margin'),'fundamentals':metrics,'snapshot':{'company':{'symbol':company['symbol'],'name':company.get('name'),'sic':company.get('sic'),'currency':company.get('currency'),'multiple_share_classes':company.get('multiple_share_classes',False)},'period':period,'quote':quote,'retrieved_at':snapshot.get('created_at')}}


def relative_analysis(request,snapshots,asof=None):
    asof=asof or datetime.now(timezone.utc)
    target=evaluate(snapshots[request.target],request.metric,request.basis,asof)
    peers=[]
    for symbol in request.peers:
        row=evaluate(snapshots[symbol],request.metric,request.basis,asof)
        if row.get('currency') and target.get('currency') and row['currency']!=target['currency']:row['reasons'].append('Moneda de reporte diferente de la del objetivo')
        if row.get('period_end') and target.get('period_end'):
            if abs((date.fromisoformat(row['period_end'])-date.fromisoformat(target['period_end'])).days)>92:row['reasons'].append('Cierres separados por más de 92 días')
        row['eligible']=not row['reasons'];peers.append(row)
    accepted=[r for r in peers if r['eligible']]
    result={'model_version':'relative-1.0','symbol':request.target,'created_at':now(),'inputs':request.model_dump(),'target':target,'peers':peers,'selected_count':len(peers),'accepted_count':len(accepted),'status':'available' if target['eligible'] and len(accepted)>=2 else 'insufficient_data','distribution':None,'implied_per_share':None,'implied_equity':None,'upside':None,'currency':target.get('currency'),'limitations':['Pares elegidos y justificados por el usuario; la aplicación no certifica comparabilidad económica por sector o ticker.','Múltiplos sobre estados anuales o TTM seleccionados; acciones diluidas medias, no acciones puntuales actuales.','Sin consenso forward, ajustes por ciclo o normalización automática de márgenes. Fechas de cierres pueden diferir hasta 92 días.','Mediana descriptiva del grupo disponible, no una recomendación ni predicción de cotización.']}
    if len(accepted)<5:result['limitations'].append('Menos de cinco pares válidos: distribución sensible a cada observación y muestra pequeña.')
    if result['status']!='available':return result
    values=[r['multiple'] for r in accepted];multiple=median(values)
    result['distribution']={'count':len(values),'min':min(values),'q25':float(np.quantile(values,.25)),'median':multiple,'q75':float(np.quantile(values,.75)),'max':max(values),'method':'Percentiles con interpolación lineal; sin exclusión automática de outliers.'}
    v=target['snapshot']['period']['values'];metric=request.metric
    fundamental=target['fundamentals']['equity_earnings'] if metric=='pe' else target['fundamentals']['free_cash_flow'] if metric=='p_fcf' else (number(v,'ebit')+number(v,'da')) if metric=='ev_ebitda' else number(v,'revenue')
    debt=target['fundamentals']['net_debt'] if metric.startswith('ev_') else 0
    shares=number(v,'shares')
    def implied(m):return (m*fundamental-debt)/shares
    equity=multiple*fundamental-debt;value=equity/shares
    result.update(implied_equity=equity,implied_per_share=value,upside=value/target['snapshot']['quote']['price']-1 if value>0 else None,market_multiple_gap=target['multiple']/multiple-1,fundamental=fundamental,net_debt_bridge=debt,shares=shares,formula='Implied equity = peer median × target fundamental − net debt (EV multiples only); implied value per share = implied equity / diluted average shares',sensitivity=[{'multiple':m,'implied_per_share':implied(m)} for m in [min(values),float(np.quantile(values,.25)),multiple,float(np.quantile(values,.75)),max(values)]])
    if value<=0:result['limitations'].append('Equity implícito no positivo; no se interpreta como precio objetivo negociable.')
    return result
