"""Investment horizon metadata. Dates describe the research window, not forecasts."""
import calendar
from datetime import datetime, timezone
from typing import Literal

HorizonCode = Literal['3-6m', '3m', '6m']
HORIZONS = {'3-6m': (3, 6, '3–6 meses'), '3m': (3, 3, '3 meses'), '6m': (6, 6, '6 meses')}


def investment_horizon(code: HorizonCode = '3-6m', started_at=None):
    start = started_at or datetime.now(timezone.utc)
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    day = start.astimezone(timezone.utc).date()
    minimum, maximum, label = HORIZONS[code]

    def months_after(months):
        year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
        month += 1
        return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1])).isoformat()

    return {
        'code': code, 'label': label, 'as_of': day.isoformat(),
        'min_months': minimum, 'max_months': maximum,
        'window_start_date': months_after(minimum), 'window_end_date': months_after(maximum),
        'focus': [
            'Resultados, guidance y catalizadores con fecha confirmada dentro del horizonte.',
            'Noticias recientes y riesgos que puedan cambiar la tesis en este período.',
            'Momentum, volatilidad y comparación con benchmark cuando exista cobertura.',
            'Fundamentales y valoración como contexto; escenarios e invalidación de la tesis pendientes de evidencia.',
        ],
        'interpretation': 'Ventana de análisis elegida, no fecha de compra o venta ni promesa de rentabilidad. El DCF estima valor presente y no predice la cotización a este horizonte.',
    }
