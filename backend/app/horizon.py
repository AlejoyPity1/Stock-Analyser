"""Investment horizon metadata. Dates describe the research window, not forecasts."""
import calendar
import re
from datetime import datetime, timezone
from typing import Literal

HorizonCode = Literal['3-6m', '3m', '6m']
HORIZONS = {'3-6m': (3, 6, '3–6 meses'), '3m': (3, 3, '3 meses'), '6m': (6, 6, '6 meses')}

_HALF_YEAR = re.compile(
    r'\b(?:(?P<word>first|second)\s+half(?:\s+of)?\s+(?:calendar\s+)?|'
    r'H(?P<number>[12])\s*)(?P<year>20\d{2})\b', re.I)
_CALENDAR_QUARTER = re.compile(
    r'\b(?:(?P<word>first|second|third|fourth)\s+calendar\s+quarter(?:\s+of)?\s+|'
    r'calendar\s+Q(?P<number>[1-4])\s*)(?P<year>20\d{2})\b', re.I)
_MONTHS = {name.lower(): month for month in range(1, 13)
           for name in (calendar.month_name[month], calendar.month_abbr[month])}
_MONTH_YEAR = re.compile(r'\b(?P<month>' + '|'.join(_MONTHS) + r')\s+(?P<year>20\d{2})\b', re.I)
_INCLUSION = re.compile(
    r'\b(?:falls?|lies?|occurs?|closes?|is|are)\s+(?:entirely\s+)?within\s+'
    r'(?:(?:the|a|our|this|defined)\s+)*(?:(?:\d+|three|six)\s*[-–]?\s*months?|'
    r'investment|analysis|research|holding|horizon)\b', re.I)


def horizon_description(horizon):
    """Present the holding/research period separately from target outcome dates."""
    first, last = horizon['window_start_date'], horizon['window_end_date']
    target = f'Target date: {last}.' if first == last else f'Target dates: {first} to {last}.'
    return f"Analysis period: {horizon['as_of']} to {last}. {target} Events before the target dates can affect the outcome."


def calendar_periods(text):
    """Recognize explicit English calendar periods; never infer fiscal quarters."""
    periods = []
    for pattern, precision in ((_HALF_YEAR, 'half_year'), (_CALENDAR_QUARTER, 'calendar_quarter'), (_MONTH_YEAR, 'month')):
        for match in pattern.finditer(text):
            if re.search(r'\bfiscal\s*$', text[max(0, match.start() - 20):match.start()], re.I):
                continue
            if re.match(r'\s*fiscal\b', text[match.end():match.end() + 15], re.I):
                continue
            year = int(match['year'])
            if precision == 'month':
                first_month = last_month = _MONTHS[match['month'].lower()]
            else:
                number = int(match['number']) if match['number'] else {'first': 1, 'second': 2, 'third': 3, 'fourth': 4}[match['word'].lower()]
                length = 6 if precision == 'half_year' else 3
                first_month = (number - 1) * length + 1
                last_month = first_month + length - 1
            periods.append({'start': f'{year:04d}-{first_month:02d}-01',
                            'end': f'{year:04d}-{last_month:02d}-{calendar.monthrange(year, last_month)[1]}',
                            'precision': precision, 'expression': match.group()})
    return periods


def horizon_inclusion_issue(text, evidence_quote, horizon):
    """Withhold a strong inclusion assertion when its cited period extends outside.

    This deliberately bounded check is not date extraction for a confirmed
    catalyst calendar, event prediction, or general semantic verification.
    """
    if not horizon or not horizon.get('as_of') or not horizon.get('window_end_date'):
        return None
    assertion = _INCLUSION.search(text)
    if not assertion:
        return None
    prefix = text[max(0, assertion.start() - 35):assertion.start()]
    if re.search(r'\b(?:may|might|could|not|never)\s+(?:\w+\s+){0,3}$', prefix, re.I):
        return None
    if re.search(r'\b(?:partly|partially|overlaps?|not (?:guaranteed|fully|entirely)|uncertain whether)\b', text, re.I):
        return None
    stated = {(period['start'], period['end']) for period in calendar_periods(text)}
    for period in calendar_periods(evidence_quote):
        if (period['start'], period['end']) not in stated:
            continue
        if not horizon['as_of'] <= period['start'] <= period['end'] <= horizon['window_end_date']:
            return {'reason_code': 'source_period_not_within_horizon',
                    'reason': 'The cited calendar period is not wholly within the analysis period; an event date within the horizon is not established.',
                    'source_period_start': period['start'], 'source_period_end': period['end'],
                    'analysis_start': horizon['as_of'], 'analysis_end': horizon['window_end_date']}
    return None


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
