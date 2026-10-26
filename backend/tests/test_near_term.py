"""Hand-checkable price scenarios and catalyst revisions; providers are controlled."""
from datetime import datetime, timezone
from io import BytesIO
import pytest
from pydantic import ValidationError
from pypdf import PdfReader

from app.near_term import PriceScenarioRequest, calculate_price_scenarios
from app.catalysts import CatalystRequest, save_catalyst, event_position
from app.store import get, put

ASOF = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
QUOTE = {'price': 100, 'currency': 'USD', 'timestamp': '2026-10-23T20:00:00+00:00', 'source': 'https://example.org/controlled-quote'}


def case(eps, pe, dividends=0):
    return {'forward_eps': eps, 'pe': pe, 'dividends_per_share': dividends,
            'rationale': 'CONTROLLED TEST: explicit assumptions, not a real forecast.',
            'invalidation': 'Controlled earnings assumption is no longer supported.'}


def request(**changes):
    values = {'symbol': 'CUSTOM', 'currency': 'USD', 'horizon': '3-6m',
              'three_months': {'bear': case(4, 20, 1), 'base': case(5, 20, 1), 'bull': case(6, 20, 1)},
              'six_months': {'bear': case(4, 15, 2), 'base': case(6, 20, 2), 'bull': case(7, 25, 2)}}
    return PriceScenarioRequest(**(values | changes))


def event_request(**changes):
    return CatalystRequest(**({'symbol': 'CUSTOM', 'title': 'Controlled earnings event',
        'event_date': '2026-11-15', 'date_status': 'estimated',
        'hypothesis': 'CONTROLLED TEST: validate persisted catalyst context and evidence.',
        'invalidation': 'Controlled event is cancelled or rescheduled.',
        'source_url': 'https://example.org/controlled-event'} | changes))


def test_prices_returns_dividends_and_calendar_horizons():
    value = calculate_price_scenarios(request(), QUOTE, asof=ASOF)
    three = value['horizons']['3']; six = value['horizons']['6']
    assert three['target_date'] == '2027-01-26' and six['target_date'] == '2027-04-26'
    assert three['cases']['base']['price'] == 100
    assert three['cases']['base']['price_return'] == 0
    assert three['cases']['base']['gross_return_with_dividends'] == pytest.approx(.01)
    assert three['cases']['base']['breakeven_pe'] == 19.8
    assert three['conditional_reward_risk'] == pytest.approx(.21 / .19)
    assert six['cases']['base']['price'] == 120  # Independent EPS hypothesis; not 3m × 2.
    assert six['cases']['base']['gross_return_with_dividends'] == pytest.approx(.22)


@pytest.mark.parametrize('change', [{'currency': 'EUR'}, {'timestamp': '2026-09-01T12:00:00Z'}, {'timestamp': '2026-10-27T12:00:00Z'}, {'price': 0}])
def test_incompatible_reference_never_generates_a_price_model(change):
    with pytest.raises(ValueError): calculate_price_scenarios(request(), QUOTE | change, asof=ASOF)


@pytest.mark.parametrize('field,value', [('forward_eps', 0), ('forward_eps', -1), ('pe', -2), ('dividends_per_share', -1), ('pe', float('nan'))])
def test_invalid_case_inputs(field, value):
    group = {'bear': case(4, 20), 'base': case(5, 20), 'bull': case(6, 20)}
    group['base'][field] = value
    with pytest.raises(ValidationError): request(three_months=group)


def test_missing_horizon_or_unordered_cases_are_rejected():
    with pytest.raises(ValidationError): request(six_months=None)
    group = {'bear': case(8, 20), 'base': case(5, 20), 'bull': case(6, 20)}
    with pytest.raises(ValueError): calculate_price_scenarios(request(three_months=group), QUOTE, asof=ASOF)


def test_no_reward_risk_when_every_case_is_positive():
    result = calculate_price_scenarios(request(), QUOTE | {'price': 10}, asof=ASOF)
    assert result['horizons']['3']['conditional_reward_risk'] is None


def test_unrepresentable_reward_risk_is_not_published_as_infinity():
    group = {'bear': case(.9999999999999999,1), 'base': case(1,1), 'bull': case(1e308,1)}
    result = calculate_price_scenarios(request(horizon='3m',three_months=group,six_months=None), QUOTE | {'price':1}, asof=ASOF)
    assert result['horizons']['3']['conditional_reward_risk'] is None


def test_catalyst_versions_remain_immutable_and_cannot_be_counted_twice(client):
    first = save_catalyst(event_request())
    second = save_catalyst(event_request(previous_id=first['id'], status='cancelled'))
    assert second['event_id'] == first['event_id']
    assert get(first['id'])['status'] == 'planned'
    assert get(second['id'])['status'] == 'cancelled'
    with pytest.raises(ValueError): save_catalyst(event_request(previous_id=first['id']))
    rows = client.get('/catalysts?symbol=CUSTOM').json()['items']
    assert next(e for e in rows if e['event_id'] == first['event_id'])['id'] == second['id']
    with pytest.raises(ValueError): calculate_price_scenarios(request(), QUOTE, [first, second], ASOF)


@pytest.mark.parametrize('changes', [
    {'date_status': 'unknown'}, {'event_date': None},
    {'source_url': 'http://example.org/test'}, {'source_url': 'https://user:pass@example.org/test'},
    {'date_status': 'reported'}, {'source_url': None},
])
def test_catalyst_date_and_evidence_requirements(changes):
    with pytest.raises(ValidationError): event_request(**changes)


def test_catalyst_literal_quote_is_verified_against_its_own_company(client):
    quote = 'The release is scheduled for November 15, 2026.'
    put('controlled-catalyst-research', 'research', 'CUSTOM', {'symbol': 'CUSTOM', 'sources': [{'id': 'source-1', 'title': 'Controlled document', 'url': 'https://example.org/controlled-event', 'read_status': 'read', 'text': quote}]})
    event = save_catalyst(event_request(research_id='controlled-catalyst-research', source_id='source-1', evidence_quote=quote, date_status='reported'))
    assert event['verification'] == 'literal_quote_matched'
    assert 'text' not in event['source_snapshot']
    with pytest.raises(ValueError): save_catalyst(event_request(research_id='controlled-catalyst-research', source_id='source-1', evidence_quote='An invented statement that was never retrieved.'))
    with pytest.raises(ValueError): save_catalyst(event_request(symbol='OTHER', research_id='controlled-catalyst-research'))


@pytest.mark.parametrize('day,status,position', [('2026-10-01','planned','past'), ('2026-11-15','planned','within_horizon'), ('2027-12-01','planned','beyond_horizon'), (None,'planned','undated'), ('2026-11-15','cancelled','cancelled')])
def test_event_window_does_not_confuse_publication_and_event_date(day,status,position):
    assert event_position({'event_date':day,'status':status}, {'as_of':'2026-10-26','window_end_date':'2027-04-26'}) == position


def test_price_model_api_freezes_quote_evidence_and_exports_pdf(client, monkeypatch):
    from app import main
    async def quote(symbol):
        assert symbol == 'CUSTOM'
        return QUOTE
    original = main.calculate_price_scenarios
    monkeypatch.setattr(main.market, 'quote', quote)
    monkeypatch.setattr(main, 'calculate_price_scenarios', lambda req, q, ev: original(req, q, ev, ASOF))
    put('price-model-report', 'research', 'CUSTOM', {'symbol': 'CUSTOM', 'status': 'completed', 'sources': [], 'investment_horizon': {'code': '3-6m', 'label': '3–6 meses', 'as_of': '2026-10-26', 'window_start_date': '2027-01-26', 'window_end_date': '2027-04-26', 'interpretation': 'Controlled test', 'focus': []}})
    event = save_catalyst(event_request(research_id='price-model-report'))
    body = request(catalyst_ids=[event['id']], research_id='price-model-report').model_dump()
    preview = client.post('/price-scenarios/preview', json=body)
    assert preview.status_code == 200
    saved = client.post('/price-scenarios', json=body)
    assert saved.status_code == 200
    value = saved.json(); id = value['id']
    assert client.get('/records/' + id).json()['reference_quote']['price'] == 100
    save_catalyst(event_request(previous_id=event['id'], status='cancelled'))
    assert get(id)['catalysts'][0]['status'] == 'planned'
    report = client.get('/reports/price-model-report').json()
    assert report['price_scenarios'][0]['id'] == id
    assert report['catalysts'][0]['id'] == event['id']  # Unlinked later revision cannot rewrite this report.
    pdf = client.get('/reports/price-model-report/pdf')
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert id in text and '2027-01-26' in text and 'forward' in text
    bad = body | {'symbol': 'OTHER'}
    assert client.post('/price-scenarios', json=bad).status_code == 422


@pytest.mark.asyncio
async def test_earnings_calendar_filters_identity_dates_and_duplicates(client, monkeypatch):
    from app import providers
    async def instrument(symbol): return {'symbol':symbol, 'currency':'USD'}
    async def transport(url, params=None, **kwargs):
        return {'earningsCalendar': [
            {'symbol':'CUSTOM','date':'2026-11-15','year':2026,'quarter':3},
            {'symbol':'CUSTOM','date':'2026-11-15','year':2026,'quarter':3},
            {'symbol':'OTHER','date':'2026-11-15'}, {'symbol':'CUSTOM','date':'2028-01-01'},
            {'symbol':'CUSTOM','date':'invalid'},
        ]}
    monkeypatch.setattr(providers.market, 'instrument', instrument)
    monkeypatch.setattr(providers.settings, 'finnhub_api_key', 'controlled-test')
    monkeypatch.setattr(providers, 'fetch', transport)
    value = await providers.market.earnings_calendar('CUSTOM','2026-10-26','2027-04-26')
    assert len(value['items']) == 1
    assert value['items'][0]['date_status'] == 'estimated'
