"""Deterministic input grounding. These checks do not certify investment quality."""
from copy import deepcopy
from datetime import date
import math
import re

METRICS = ('revenue', 'net_income', 'eps', 'shares')
_SUFFIX = re.compile(r'\b(?:incorporated|corporation|company|limited|holdings?|inc|corp|ltd|plc|nv|sa|se|ag)\.?\s*$', re.I)
_AMBIGUOUS = {'AI', 'IT', 'ON', 'ALL', 'FOR', 'NOW', 'ARE', 'HAS', 'CAN', 'CEO', 'USA'}
_NUMBER = re.compile(r'\d[\d,.]*')
_FINANCIAL_METRIC = re.compile(
    r'\b(?:net (?:income|profit)|revenue|net sales|earnings per share|EPS|'
    r'(?:diluted|outstanding|weighted.average) shares|share count|market cap(?:italization)?|'
    r'(?:gross|operating|profit|net) margin|cash flow|EBITDA|operating income)\b', re.I)


def financial_facts(company, as_of=None):
    """Copy only dated, unit-labelled facts; never reinterpret a printed table."""
    if not company:
        return []
    candidates = [('quarter', row) for row in sorted(company.get('quarterly') or [], key=lambda r: r.get('end', ''), reverse=True)[:2]]
    annual = sorted(company.get('statements') or [], key=lambda r: r.get('end', ''), reverse=True)
    if annual:
        candidates.append(('annual', annual[0]))
    if company.get('ttm'):
        candidates.append(('ttm', company['ttm']))
    result = []
    for period_type, row in candidates:
        values = {}
        for metric in METRICS:
            fact = (row.get('values') or {}).get(metric)
            if not isinstance(fact, dict):
                continue
            value = fact.get('value')
            currency = fact.get('currency')
            unit = fact.get('unit')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                continue
            if metric == 'shares' and value <= 0:
                continue
            expected = 'shares' if metric == 'shares' else f'{currency}/shares' if metric == 'eps' else currency
            if not expected or unit != expected or not fact.get('source_id') or not fact.get('source'):
                continue
            try:
                start = date.fromisoformat(fact['period_start'])
                end = date.fromisoformat(fact['period_end'])
                if start >= end or fact['period_end'] != row.get('end'):
                    continue
                duration = (end - start).days
                if not (60 <= duration <= 120 if period_type == 'quarter' else 300 <= duration <= 400):
                    continue
                if as_of and (end > date.fromisoformat(as_of) or (fact.get('filed') and fact['filed'] > as_of)):
                    continue
            except (ValueError, TypeError, KeyError):
                continue
            values[metric] = deepcopy(fact)
        if values:
            starts = {item['period_start'] for item in values.values()}
            # Do not put values from different durations under one period label.
            if len(starts) != 1:
                continue
            result.append({'period_type': period_type, 'period_start': starts.pop(),
                           'period_end': row['end'], 'values': values,
                           'shares_definition': 'Weighted-average diluted shares for this period, not current shares outstanding.'})
    return result


def compact_facts(periods):
    # Two recent periods keep the native 8192-token setup practical. Full
    # provenance and the annual/TTM rows remain in the exported financial table.
    return [{'period_type': row['period_type'], 'start': row['period_start'], 'end': row['period_end'],
             'values': {key: {'value': fact['value'], 'unit': fact['unit']} for key, fact in row['values'].items()}}
            for row in periods[:2]]


def _issuer_terms(symbol, company):
    name = str((company or {}).get('name') or '').strip()
    while name:
        cleaned = _SUFFIX.sub('', name).strip(' .,')
        if cleaned == name:
            break
        name = cleaned
    terms = [term for term in (name, (company or {}).get('name')) if term and len(term) > 2]
    # Optional caller-provided aliases must be explicit; no ticker-specific brands.
    terms.extend(term for term in (company or {}).get('research_aliases', []) if isinstance(term, str) and len(term) > 2)
    return list(dict.fromkeys(terms))


def screen_sources(sources, symbol, company=None):
    """Conservative issuer-link heuristic, not a semantic relevance verdict."""
    if not company or not company.get('name'):
        return sources, {'method': 'issuer_link_heuristic', 'available': False, 'excluded': []}
    terms = _issuer_terms(symbol, company)
    patterns = [re.compile(r'(?<!\w)' + re.escape(term) + r'(?!\w)', re.I) for term in terms]
    marked_ticker = re.compile(r'(?:\$|\b(?:NASDAQ|NYSE|AMEX|XETRA)\s*:\s*|\()' + re.escape(symbol) + r'(?!\w)', re.I)
    plain_ticker = re.compile(r'(?<!\w)' + re.escape(symbol) + r'(?!\w)') if len(symbol) >= 3 and symbol not in _AMBIGUOUS else None
    included = []; excluded = []
    for source in sources:
        if source.get('publisher') == 'SEC EDGAR' or source.get('source_type') == 'official_filing':
            included.append(source)
            continue
        title = str(source.get('title') or '')
        abstract = str(source.get('summary') or source.get('text') or '')
        text = title + ' ' + abstract
        linked = any(pattern.search(text) for pattern in patterns) or marked_ticker.search(text) or (plain_ticker and plain_ticker.search(text))
        reason = None
        if not linked:
            reason = 'No explicit issuer link in the available title/abstract; product-only references require explicit aliases.'
        portfolio_dispute = (re.search(r'covered.call', text, re.I) and
                             re.search(r'retiree|elder abuse|brokerage client', text, re.I) and
                             re.search(r'allege|claims|sues|lawsuit', text, re.I))
        legal_actor = any(re.search(r'(?:alleges?|against|sues)\s+' + re.escape(term), text, re.I) for term in terms)
        if linked and portfolio_dispute and not legal_actor:
            reason = 'A third-party portfolio/broker dispute mentions the shares without establishing issuer exposure.'
        if reason:
            excluded.append({'id': source['id'], 'title': title[:200], 'reason': reason})
        else:
            included.append(source)
    return included, {'method': 'issuer_link_heuristic', 'available': True,
                      'included_count': len(included), 'excluded_count': len(excluded), 'excluded': excluded,
                      'limitation': 'Issuer mentions are not confirmation of economic relevance. Product/subsidiary coverage needs explicit aliases.'}


def numerical_financial_claim(text, mechanism=''):
    for value in (text, mechanism):
        # Calendar years and fiscal-quarter labels alone are not monetary figures.
        value = re.sub(r'\b(?:19|20)\d{2}\b|\bQ[1-4]\b', '', value, flags=re.I)
        amount = _NUMBER.search(value) or re.search(r'\b(?:million|billion|trillion|percent)\b', value, re.I)
        if _FINANCIAL_METRIC.search(value) and amount:
            return True
    return False
