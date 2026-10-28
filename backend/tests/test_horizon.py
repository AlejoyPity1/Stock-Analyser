"""Calendar horizons and immutable report context; no live providers or AI calls."""
import time
from datetime import datetime, timezone
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.horizon import investment_horizon, calendar_periods, horizon_description, horizon_inclusion_issue
from app.providers import ProviderError
from app.store import put


@pytest.mark.parametrize('as_of,first,last',[
    ('2026-10-31T12:00:00+00:00', '2027-01-31', '2027-04-30'),
    ('2023-11-30T12:00:00+00:00', '2024-02-29', '2024-05-30'),
    ('2024-11-30T12:00:00+00:00', '2025-02-28', '2025-05-30'),
    ('2026-12-31T23:30:00-02:00', '2027-04-01', '2027-07-01'),
])
def test_three_to_six_calendar_months(as_of, first, last):
    h = investment_horizon(started_at=as_of)
    assert h['window_start_date'] == first
    assert h['window_end_date'] == last
    assert h['min_months'] == 3 and h['max_months'] == 6


def test_fixed_horizon_is_distinct_from_range():
    h = investment_horizon('3m', datetime(2026, 10, 26, tzinfo=timezone.utc))
    assert h['window_start_date'] == h['window_end_date'] == '2027-01-26'
    assert h['max_months'] == 3


@pytest.mark.parametrize('text,start,end', [
    ('The first half of 2027.', '2027-01-01', '2027-06-30'),
    ('H2 2026.', '2026-07-01', '2026-12-31'),
    ('The first calendar quarter of 2027.', '2027-01-01', '2027-03-31'),
    ('calendar Q4 2026.', '2026-10-01', '2026-12-31'),
    ('February 2024.', '2024-02-01', '2024-02-29'),
    ('Feb 2025.', '2025-02-01', '2025-02-28'),
])
def test_calendar_periods_preserve_full_uncertain_date_ranges(text, start, end):
    period = calendar_periods(text)[0]
    assert period['start'] == start and period['end'] == end


@pytest.mark.parametrize('text', ['Fiscal H1 2027', 'the first half of fiscal 2027', 'fiscal Q1 2027', 'Q1 2027'])
def test_fiscal_or_unqualified_quarters_do_not_gain_invented_calendar_dates(text):
    assert calendar_periods(text) == []


@pytest.mark.parametrize('code', ['3m', '6m', '3-6m'])
def test_half_year_cannot_be_asserted_within_a_shorter_holding_period(code):
    horizon = investment_horizon(code, '2026-10-28T12:00:00Z')
    text = 'The transaction is expected to close in the first half of 2027, which falls within the defined investment horizon.'
    issue = horizon_inclusion_issue(text, 'Closing is expected in the first half of 2027, subject to approval.', horizon)
    assert issue['source_period_end'] == '2027-06-30'
    assert issue['analysis_start'] == '2026-10-28'
    assert issue['analysis_end'] == horizon['window_end_date']


def test_a_wholly_contained_period_and_qualified_overlap_are_not_rejected():
    h = investment_horizon('3m', '2026-10-28T12:00:00Z')
    assert horizon_inclusion_issue('November 2026 falls within the three-month horizon.', 'Expected in November 2026.', h) is None
    quote = 'Expected in the first half of 2027.'
    for text in ('The first half of 2027 only partly overlaps the horizon.',
                 'The first half of 2027 does not fall within the three-month horizon.',
                 'An event in the first half of 2027 could fall within the investment horizon.'):
        assert horizon_inclusion_issue(text, quote, h) is None


def test_no_timing_verdict_is_invented_for_uncited_or_missing_date_context():
    text = 'The first half of 2027 falls within the investment horizon.'
    assert horizon_inclusion_issue(text, 'No timing was specified.', investment_horizon()) is None
    assert horizon_inclusion_issue(text, 'Expected in the first half of 2027.', None) is None


def test_analysis_period_starts_at_as_of_while_target_date_remains_three_months_away():
    h = investment_horizon('3m', '2026-10-28T12:00:00Z')
    assert 'Analysis period: 2026-10-28 to 2027-01-28.' in horizon_description(h)
    assert 'Target date: 2027-01-28.' in horizon_description(h)
    assert 'Target dates: 2027-01-28 to 2027-04-28.' in horizon_description(investment_horizon('3-6m', '2026-10-28T12:00:00Z'))


def test_report_preserves_original_horizon_in_json_and_pdf(client):
    h = investment_horizon(started_at='2025-01-31T12:00:00Z')
    put('horizon-report', 'research', 'CUSTOM', {
        'symbol': 'CUSTOM', 'status': 'completed', 'sources': [], 'investment_horizon': h,
    })
    report = client.get('/reports/horizon-report').json()
    assert report['investment_horizon'] == h
    assert report['investment_horizon']['window_end_date'] == '2025-07-31'
    assert '2025-04-30' in report['sections'][0]['text']
    pdf = client.get('/reports/horizon-report/pdf')
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert '2025-04-30' in text and '2025-07-31' in text
    assert 'no predice' in ' '.join(text.split())


def test_legacy_report_does_not_gain_an_invented_horizon(client):
    put('legacy-horizon', 'research', 'CUSTOM', {'symbol': 'CUSTOM', 'status': 'completed'})
    report = client.get('/reports/legacy-horizon').json()
    assert report['investment_horizon'] is None
    assert 'no tiene horizonte registrado' in report['sections'][0]['text']


@pytest.mark.parametrize('symbol,code', [('CUSTOM', '3-6m'), ('OTHER', '3m'), ('CLASS-B', '6m')])
def test_research_uses_requested_symbol_and_horizon(client, monkeypatch, symbol, code):
    from app.providers import sec, market
    calls = []

    async def company(requested):
        calls.append(requested)
        return {'symbol': requested, 'name': 'Controlled fixture ' + requested,
                'currency': 'USD', 'filings': [], 'statements': []}

    async def quote(requested):
        raise ProviderError('No controlled quote')

    async def news(requested, days):
        assert requested == symbol
        return []

    monkeypatch.setattr(sec, 'company', company)
    monkeypatch.setattr(market, 'quote', quote)
    monkeypatch.setattr(market, 'news', news)
    response = client.post('/research', json={'symbol': symbol, 'horizon': code})
    assert response.status_code == 202
    queued = response.json()
    assert queued['symbol'] == symbol and queued['investment_horizon']['code'] == code
    for _ in range(40):
        job = client.get('/records/' + queued['id']).json()
        if job['status'] not in ('queued', 'running'):
            break
        time.sleep(.01)
    assert calls == [symbol] and job['status'] == 'partial'
    assert job['investment_horizon'] == queued['investment_horizon']
    assert client.get('/reports/' + queued['id']).json()['investment_horizon'] == queued['investment_horizon']


def test_invalid_horizon_rejected_before_provider_access(client):
    assert client.post('/research', json={'symbol': 'CUSTOM', 'horizon': '5years'}).status_code == 422
