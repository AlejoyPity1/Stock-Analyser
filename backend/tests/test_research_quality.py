import json
from copy import deepcopy

import pytest
import time
from io import BytesIO

from app.config import settings
from app.horizon import investment_horizon
from app.local_ai import _parse_completion, _windows, completion_payload, make_batches
from app.research_quality import financial_facts, numerical_financial_claim, screen_sources
from app.research import ResearchRequest
from test_local_ai import completion, evidence_answer
from test_local_ai import local, directory, mock_transport


def company(currency='USD'):
    values = {}
    for metric, value, unit in [('net_income', 29578000000, currency), ('eps', 2.01, currency + '/shares'), ('shares', 14725873000, 'shares')]:
        values[metric] = {'value': value, 'unit': unit, 'currency': None if metric == 'shares' else currency,
                          'period_start': '2025-12-28', 'period_end': '2026-03-28',
                          'filed': '2026-05-01', 'source_id': 'controlled-fact-' + metric,
                          'source': 'https://www.sec.gov/Archives/controlled', 'quality': 'reported'}
    return {'name': 'Example Hardware plc', 'quarterly': [{'start': '2025-12-28', 'end': '2026-03-28', 'values': values}]}


@pytest.mark.parametrize('currency', ['USD', 'EUR'])
def test_financial_facts_keep_individual_share_units_currency_and_exact_period(currency):
    source = company(currency)
    original = deepcopy(source)
    facts = financial_facts(source, '2026-10-26')
    assert source == original
    assert facts[0]['period_type'] == 'quarter'
    assert facts[0]['values']['net_income']['value'] == 29578000000
    assert facts[0]['values']['eps']['value'] == 2.01
    assert facts[0]['values']['shares']['value'] == 14725873000
    assert facts[0]['values']['shares']['unit'] == 'shares'
    assert facts[0]['values']['net_income']['unit'] == currency
    assert facts[0]['period_start'] == '2025-12-28' and facts[0]['period_end'] == '2026-03-28'


def test_invalid_or_future_financial_values_are_not_filled_or_rescaled():
    source = company()
    source['quarterly'][0]['values']['net_income']['unit'] = 'EUR'
    source['quarterly'][0]['values']['eps']['value'] = float('nan')
    source['quarterly'][0]['values']['shares']['filed'] = '2027-05-01'
    assert financial_facts(source, '2026-10-26') == []


def test_cumulative_half_year_cannot_be_presented_as_a_quarter():
    source = company()
    for fact in source['quarterly'][0]['values'].values():
        fact['period_start'] = '2025-09-28'
    assert financial_facts(source, '2026-10-26') == []


def test_wrong_cumulative_quarter_claim_is_withheld_even_when_quotation_is_valid():
    data = evidence_answer()
    data['claims'][0]['text'] = 'Q2 2026 net income was $71,675 million and diluted EPS was $4.85 based on 14,768,115 shares.'
    parsed, rejected = _parse_completion(completion(data).json(), {'E1': {'id': 'controlled-table', 'excerpt': 'Net income 29,578 24,780 71,675 61,110. Diluted EPS 2.01 1.65 4.85 4.05.'}})
    assert rejected is None
    assert parsed.synthesis.claims == []
    assert parsed.withheld[0]['reason'].startswith('Numerical financial statement withheld')
    assert '71,675' not in json.dumps(parsed.withheld)


def test_operating_order_percentage_and_calendar_dates_are_not_financial_statement_values():
    assert numerical_financial_claim('The article reports production orders increased by 30%.', 'Revenue depends on sell-through.') is False
    assert numerical_financial_claim('Results were released for Q2 2026.', 'Reported earnings context.') is False
    assert numerical_financial_claim('The stated net profit was seventy billion dollars.') is True


@pytest.mark.parametrize('statement', [
    'Alpha and Beta faced a combined fine of $32 million for Beta.',
    'The fine imposed on Beta was 20.81 billion won.',
    'Beta received a penalty of KRW 20,810,000,000.',
    'The regulator ordered a payment of 32 million dollars.',
    'The analyst assigned a EUR 125 price target.',
    'The device costs £2,899.',
    'The settlement was thirty thousand dollars.',
])
def test_monetary_claims_require_verification_beyond_a_copied_excerpt(statement):
    assert numerical_financial_claim(statement) is True


def test_combined_fine_cannot_be_published_with_an_unverified_issuer_allocation():
    data = evidence_answer()
    data['claims'][0]['text'] = 'Alpha and Beta faced a combined fine of $32 million for Beta.'
    parsed, rejected = _parse_completion(completion(data).json(), {
        'E1': {'id': 'truncated-abstract', 'excerpt': 'Alpha and Beta were fined 42.9 billion won ($32 million) and 20.81 billi'},
    })
    assert rejected is None
    assert parsed.synthesis.claims == []
    assert parsed.withheld[0]['source_id'] == 'truncated-abstract'
    assert 'entity, period and unit verification' in parsed.withheld[0]['reason']
    assert '$32' not in json.dumps(parsed.withheld)


def test_monetary_comparison_is_withheld_even_with_two_valid_citations():
    data = evidence_answer()
    data['claims'] = []
    data['contradictions'] = [{'description': 'The reports disagree whether Beta paid $32 million or $16 million.',
                               'first_evidence_id': 'E1', 'second_evidence_id': 'E2'}]
    parsed, rejected = _parse_completion(completion(data).json(), {
        'E1': {'id': 'one', 'excerpt': 'The total combines two companies.'},
        'E2': {'id': 'two', 'excerpt': 'Only one issuer is covered.'},
    })
    assert rejected is None
    assert parsed.synthesis.contradictions == []
    assert parsed.withheld[0]['type'] == 'contradiction'


@pytest.mark.parametrize('symbol', ['NVDA', 'MSFT', 'ASML', 'CUSTOM'])
def test_cited_event_period_must_fit_the_requested_horizon_for_every_issuer(symbol):
    data = evidence_answer()
    data['claims'][0]['text'] = f'{symbol} expects closing in the first half of 2027, which falls within the defined 3-month horizon.'
    data['claims'][0]['financial_mechanism'] = 'Closing is conditional on regulatory approvals.'
    parsed, rejected = _parse_completion(completion(data).json(), {
        'E1': {'id': 'dated-transaction', 'excerpt': 'The transaction is expected to close in the first half of 2027, subject to approval.'},
    }, investment_horizon('3m', '2026-10-28T12:00:00Z'))
    assert rejected is None
    assert parsed.synthesis.claims == []
    assert parsed.withheld[0]['category'] == 'horizon_inclusion'
    assert parsed.withheld[0]['source_period_end'] == '2027-06-30'


def test_horizon_check_also_covers_a_claims_causal_mechanism():
    data = evidence_answer()
    data['claims'][0]['text'] = 'The issuer expects closing in the first half of 2027.'
    data['claims'][0]['financial_mechanism'] = 'The first half of 2027 falls within the three-month investment horizon.'
    parsed, rejected = _parse_completion(completion(data).json(), {
        'E1': {'id': 'dated-transaction', 'excerpt': 'Expected closing is in the first half of 2027, subject to approval.'},
    }, investment_horizon('3m', '2026-10-28T12:00:00Z'))
    assert rejected is None
    assert parsed.synthesis.claims == []
    assert parsed.withheld[0]['mechanism_sha256']


def test_complete_sentence_selection_preserves_negation_and_executive_transition_date():
    text = ('Metadata without financial context. ' * 20 +
            'On April 20, 2026, Example Hardware announced the CEO transition effective September 1, 2026. '
            'The Board appointed Morgan Smith as Chief Executive Officer effective on that transition date. '
            'There are no family relationships requiring disclosure under Regulation S-K. '
            'The company expects continued operations. ' * 8)
    windows = _windows(text, 600)
    assert windows
    assert any('September 1, 2026' in excerpt and 'appointed' in excerpt for _, _, excerpt in windows)
    for start, end, excerpt in windows:
        assert text[start:end] == excerpt
        assert len(excerpt.encode()) <= 600
        if 'family relationships' in excerpt:
            assert 'There are no family relationships' in excerpt


def test_quarterly_cover_and_transition_elections_do_not_displace_operating_context():
    cover = ('FORM 10-Q QUARTERLY REPORT PURSUANT TO SECTION 13 of the Exchange Act. '
             'TRANSITION REPORT PURSUANT TO SECTION 13 of the Exchange Act. '
             'Commission File Number 001-00000 Example Hardware plc. '
             'Large accelerated filer checked; emerging growth company unchecked. '
             'The registrant has not elected an extended transition period. ')
    body = ('Demand depends on customer adoption of the new service. '
            'Lower demand could reduce revenue and gross margin. '
            'The company has not provided guidance for the next quarter. '
            'Supply constraints could increase input costs. '
            'Management expects these constraints to affect operating income. ')
    trailer = ('Certifications of Chief Executive Officer and Chief Financial Officer. '
               'Information is incorporated by reference. ')
    text = cover * 3 + body + trailer * 3
    windows = _windows(text, 650, official=True)
    assert windows
    joined = ' '.join(excerpt for _, _, excerpt in windows)
    assert 'has not provided guidance' in joined
    assert 'revenue and gross margin' in joined
    for start, end, excerpt in windows:
        assert text[start:end] == excerpt
        assert 'FORM 10-Q' not in excerpt
        assert 'emerging growth company' not in excerpt
        assert 'Certifications of Chief' not in excerpt


def test_earnings_filing_supplies_release_context_instead_of_cover_and_checkboxes():
    text = ('FORM 8-K CURRENT REPORT PURSUANT TO SECTION 13 of the Exchange Act. '
            'Exact name of Registrant is Example Hardware plc. '
            'The address of principal executive offices is Example Street. '
            'Emerging growth company unchecked; extended transition period unchecked. '
            'Item 2.02 Results of Operations and Financial Condition. '
            'On July 30, 2026, Example Hardware issued a press release regarding its financial results. '
            'A copy of the release is attached as Exhibit 99.1. '
            'The information shall not be deemed filed for purposes of the Exchange Act. '
            'Item 9.01 Financial Statements and Exhibits. ')
    windows = _windows(text, 500, official=True)
    assert windows
    joined = ' '.join(excerpt for _, _, excerpt in windows)
    assert 'financial results' in joined and 'Exhibit 99.1' in joined
    assert 'executive offices' not in joined and 'emerging growth company' not in joined
    assert 'shall not be deemed' not in joined


def test_official_short_cover_does_not_gain_a_boilerplate_claim():
    assert _windows('Emerging growth company unchecked. Commission File Number: 001-00000.', 900, official=True) == []


def test_news_about_accounting_status_is_not_discarded_as_filing_boilerplate():
    text = 'Example is no longer an emerging growth company, according to the article.'
    assert _windows(text, 900) == [(0, len(text), text)]


@pytest.mark.parametrize('symbol,name', [('AAPL', 'Apple Inc.'), ('NVDA', 'NVIDIA Corporation'), ('ASML', 'ASML Holding NV')])
def test_issuer_filter_is_generic_and_audits_excluded_articles(symbol, name):
    sources = [{'id': 'issuer', 'title': name + ' releases results', 'summary': 'The company describes demand.', 'publisher': 'News'},
               {'id': 'unlinked', 'title': 'Different business reports results', 'summary': 'No issuer link is supplied.', 'publisher': 'News'}]
    kept, audit = screen_sources(sources, symbol, {'name': name})
    assert [row['id'] for row in kept] == ['issuer']
    assert audit['excluded'][0]['id'] == 'unlinked'
    assert audit['method'] == 'issuer_link_heuristic'


def test_portfolio_lawsuit_is_not_apple_operating_evidence_but_remains_relevant_to_named_broker():
    source = {'id': 'case', 'publisher': 'News',
              'title': 'Retiree Alleges Morgan Stanley Covered Call Strategy Cost Him His Apple and NVIDIA Shares; Elder Abuse Claims',
              'summary': 'A covered-call portfolio dispute.'}
    assert screen_sources([source], 'AAPL', {'name': 'Apple Inc.'})[0] == []
    assert screen_sources([source], 'MS', {'name': 'Morgan Stanley'})[0] == [source]


def test_ambiguous_ticker_ai_does_not_match_every_artificial_intelligence_article():
    sources = [{'id': 'macro', 'title': 'AI spending across technology', 'publisher': 'News', 'summary': 'AI demand rises.'},
               {'id': 'issuer', 'title': 'C3.ai releases results (NYSE:AI)', 'publisher': 'News', 'summary': 'Company results.'}]
    assert [s['id'] for s in screen_sources(sources, 'AI', {'name': 'C3.ai Inc.'})[0]] == ['issuer']


def test_financial_context_is_included_in_the_complete_input_budget(monkeypatch):
    monkeypatch.setattr(settings, 'local_ai_context_tokens', 8192)
    issuer = company()
    sources = [{'id': str(i), 'publisher': 'SEC EDGAR', 'title': 'Official statement', 'read_status': 'read',
                'text': 'Revenue demand is subject to uncertainty. Management discusses the outlook. ' * 30} for i in range(10)]
    batches, coverage = make_batches(sources, ResearchRequest(symbol='EXMP'), investment_horizon('3-6m', '2026-10-26T00:00:00Z'), issuer)
    from app.local_ai import LOCAL_SYSTEM
    assert batches and batches[0]['financial_context'][0]['values']['eps']['value'] == 2.01
    for batch in batches:
        payload = completion_payload(batch)
        size = lambda value: len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode())
        assert size(batch) + size(payload['response_format']['json_schema']['schema']) + len(LOCAL_SYSTEM.encode()) + 512 + settings.local_ai_max_output_tokens <= settings.local_ai_context_tokens


def test_grounded_facts_and_withheld_numbers_survive_research_persistence_and_pdf(local, monkeypatch):
    from app.providers import sec, market, ProviderError
    from pypdf import PdfReader
    issuer = {**company(), 'symbol': 'TEST', 'currency': 'USD', 'filings': [], 'statements': []}
    async def company_call(symbol): return issuer
    async def quote_call(symbol): raise ProviderError('Controlled test has no quote')
    async def news_call(*args): return [{'id': 'controlled-source', 'title': 'TEST controlled source',
        'publisher': 'Controlled fixture', 'url': 'https://example.org/test', 'full_text': False,
        'summary': 'The issuer reports improved demand. Future profitability depends on margins.', 'read_status': 'abstract_only'}]
    monkeypatch.setattr(sec, 'company', company_call)
    monkeypatch.setattr(market, 'quote', quote_call)
    monkeypatch.setattr(market, 'news', news_call)
    data = evidence_answer()
    wrong = deepcopy(data['claims'][0])
    wrong['text'] = 'Q2 net income was $71,675 million and diluted EPS was $4.85.'
    data['claims'].append(wrong)
    mock_transport(monkeypatch, lambda request: directory() if request.method == 'GET' else completion(data))
    response = local.post('/research', json={'symbol': 'TEST', 'use_ai': True})
    assert response.status_code == 202
    identifier = response.json()['id']
    for _ in range(100):
        job = local.get('/records/' + identifier).json()
        if job['status'] not in ('queued', 'running'): break
        time.sleep(.01)
    assert job['ai']['data']['quality_control']['withheld_count'] == 1
    assert len(job['ai']['data']['claims']) == 1
    assert job['ai']['data']['financial_facts'][0]['values']['net_income']['value'] == 29578000000
    report = local.get('/reports/' + identifier).json()
    assert report['record']['ai']['data']['financial_facts'][0]['period_type'] == 'quarter'
    pdf = local.get('/reports/' + identifier + '/pdf')
    assert pdf.status_code == 200
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert '29,578,000,000' in text and '14,725,873,000' in text
    assert '71,675' not in text


@pytest.mark.parametrize('symbol,code', [('NVDA', '3m'), ('MSFT', '6m'), ('CUSTOM', '3-6m')])
def test_horizon_publication_guard_persists_across_issuers_json_and_pdf(local, monkeypatch, symbol, code):
    from app.providers import sec, market, ProviderError
    from app import research
    from pypdf import PdfReader
    horizon = investment_horizon(code, '2026-10-28T12:00:00Z')
    monkeypatch.setattr(research, 'investment_horizon', lambda requested, started_at=None: horizon)
    async def issuer_call(requested):
        return {'symbol': requested, 'name': requested + ' Controlled Company', 'currency': 'USD', 'filings': [], 'statements': []}
    async def quote_call(requested): raise ProviderError('Controlled test has no quote')
    async def news_call(*args):
        return [{'id': 'dated-source', 'title': symbol + ' controlled transaction', 'publisher': 'Controlled fixture',
                 'url': 'https://example.org/dated-source', 'summary': 'Closing is expected in the first half of 2027, subject to approval.',
                 'read_status': 'abstract_only'}]
    monkeypatch.setattr(sec, 'company', issuer_call)
    monkeypatch.setattr(market, 'quote', quote_call)
    monkeypatch.setattr(market, 'news', news_call)
    data = evidence_answer()
    bad = deepcopy(data['claims'][0])
    bad['text'] = 'Closing is expected in the first half of 2027, which falls within the investment horizon.'
    bad['financial_mechanism'] = 'Closing may change the business.'
    data['claims'][0]['text'] = 'The proposed transaction remains subject to approval.'
    data['claims'][0]['financial_mechanism'] = 'Approval is a condition of closing.'
    data['claims'].append(bad)
    mock_transport(monkeypatch, lambda request: directory() if request.method == 'GET' else completion(data))
    response = local.post('/research', json={'symbol': symbol, 'horizon': code, 'use_ai': True})
    assert response.status_code == 202
    identifier = response.json()['id']
    for _ in range(100):
        job = local.get('/records/' + identifier).json()
        if job['status'] not in ('queued', 'running'): break
        time.sleep(.01)
    assert job['investment_horizon'] == horizon
    assert len(job['ai']['data']['claims']) == 1
    quality = job['ai']['data']['quality_control']
    assert quality['withheld_count'] == 1
    assert quality['withheld_financial_count'] == 0
    assert quality['withheld_horizon_count'] == 1
    report = local.get('/reports/' + identifier).json()
    assert report['record'] == job
    assert f"Analysis period: 2026-10-28 to {horizon['window_end_date']}" in report['sections'][0]['text']
    pdf = local.get('/reports/' + identifier + '/pdf')
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert '1 timing claim(s) withheld' in text
    assert '2027-06-30' in text
    assert bad['text'] not in text
    assert '1 numerical financial statement' not in text
    assert local.get('/records/' + identifier).json() == job
