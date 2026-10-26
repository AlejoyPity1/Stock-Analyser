"""Calendar horizons and immutable report context; no live providers or AI calls."""
import time
from datetime import datetime, timezone
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.horizon import investment_horizon
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
    assert 'no predice' in text


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
