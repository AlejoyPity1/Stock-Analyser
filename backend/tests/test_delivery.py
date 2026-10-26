import pytest
from app.store import put,get
from app.config import settings
from app.providers import market,ProviderError
from app.research import ResearchRequest,synthesize
from test_workflow import inputs

@pytest.mark.asyncio
async def test_paid_ai_disabled_even_with_a_key(client,monkeypatch):
    monkeypatch.setattr(settings,'paid_ai_enabled',False)
    monkeypatch.setattr(settings,'research_api_key','controlled-test-key')
    with pytest.raises(ProviderError) as e:await synthesize([],ResearchRequest(symbol='TEST',use_ai=True))
    assert e.value.code=='paid_ai_disabled'

@pytest.mark.asyncio
async def test_quote_uses_trading_currency_not_company_reporting_currency(client,monkeypatch):
    from app import providers
    async def transport(url,params=None,**kwargs):
        if url.endswith('/quote'):return {'c':100,'t':1700000000}
        if url.endswith('/stock/symbol'):return [{'symbol':'ASML','currency':'USD','mic':'XNAS','figi':'test'}]
        raise AssertionError('Company profile currency must not be used for quote')
    monkeypatch.setattr(settings,'finnhub_api_key','test')
    monkeypatch.setattr(providers,'fetch',transport)
    quote=await market.quote('ASML')
    assert quote['currency']=='USD' and quote['exchange']=='XNAS'

@pytest.mark.asyncio
async def test_unknown_instrument_currency_never_inferred(client,monkeypatch):
    from app import providers
    async def transport(url,params=None,**kwargs):return {'c':100,'t':1700000000} if url.endswith('/quote') else []
    monkeypatch.setattr(settings,'finnhub_api_key','test');monkeypatch.setattr(providers,'fetch',transport)
    with pytest.raises(ProviderError) as e:await market.quote('TEST')
    assert e.value.code=='ambiguous_currency'


def test_scenario_set_persistence_report_and_pdf(client):
    put('report-scenarios','research','TEST',{'symbol':'TEST','status':'completed','sources':[],'financial_snapshot':{'name':'Controlled <test> & fixture','statements':[]}})
    data={'symbol':'TEST','bear':inputs(growth=-.01),'base':inputs(),'bull':inputs(growth=.01),'research_id':'report-scenarios','justification':'Controlled scenario fixture, not actual financial forecasts.'}
    saved=client.post('/scenario-sets',json=data)
    assert saved.status_code==200
    id=saved.json()['id'];assert get(id)['results']['base']['fair_value']==pytest.approx(20)
    r=client.get('/reports/report-scenarios').json()
    assert len(r['sections'])==18
    assert any(s['id']==id for s in r['related_scenarios'])
    assert r['sections'][11]['status']=='available'
    pdf=client.get('/reports/report-scenarios/pdf')
    assert pdf.status_code==200 and pdf.headers['content-type']=='application/pdf'
    assert pdf.content.startswith(b'%PDF')
    from pypdf import PdfReader
    from io import BytesIO
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert 'Bear / Base / Bull Scenarios' in text and id in text
    assert 'Sources and Methodology' in text and 'Controlled <test> & fixture' in text


def test_mismatched_scenario_baselines_rejected(client):
    d={'symbol':'TEST','bear':inputs(revenue=2000),'base':inputs(),'bull':inputs(),'justification':'Controlled fixture with inconsistent starting inputs.'}
    assert client.post('/scenario-sets',json=d).status_code==422


def test_screen_requires_currency_for_capitalization_filters(client):
    assert client.get('/screen?min_cap=1').status_code==422


def test_screen_growth_sort_and_missing_values(client):
    for symbol,revenue,previous,margin in [('SORTA',150,100,.2),('SORTB',110,100,.3)]:
        put('snapshot:'+symbol,'snapshot',symbol,{'company':{'name':symbol,'currency':'USD','industry':'Test industry','statements':[{'end':'2024-12-31','values':{'revenue':{'value':revenue}}},{'end':'2023-12-31','values':{'revenue':{'value':previous}}}]},'metrics':{'operating_margin':margin,'pe':10},'created_at':'2025-01-01'})
    r=client.get('/screen?industry=Test%20industry&min_growth=0.05&sort=revenue_growth&order=desc').json()
    assert [row['symbol'] for row in r['rows']]==['SORTA','SORTB']
    assert r['rows'][0]['metrics']['revenue_growth']==pytest.approx(.5)

@pytest.mark.asyncio
async def test_directory_redirect_is_constrained_to_provider_cdn(client,monkeypatch):
    import httpx
    from app import providers
    async def no_sleep(seconds):pass
    monkeypatch.setattr(providers.asyncio,'sleep',no_sleep)
    def handler(request):return httpx.Response(302,headers={'location':'https://attacker.example/collect'})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderError) as e:await providers.fetch('https://finnhub.io/api/v1/stock/symbol',{'exchange':'CONTROLLEDTEST'})
    assert e.value.code=='unsafe_redirect'

@pytest.mark.asyncio
async def test_unadjusted_history_never_claims_adjustments(client,monkeypatch):
    from app import providers
    from app.providers import historical
    async def transport(url,params=None,**kwargs):
        return {'Meta Data':{'2. Symbol':'TEST'},'Time Series (Daily)':{'2024-01-02':{'4. close':'100','5. volume':'200'}}}
    async def instrument(symbol):return {'symbol':symbol,'currency':'USD'}
    monkeypatch.setattr(settings,'alphavantage_api_key','test');monkeypatch.setattr(providers,'fetch',transport);monkeypatch.setattr(market,'instrument',instrument)
    d=await historical.history('TEST',adjusted=False)
    assert d['adjusted'] is False and d['points'][0]['close']==100
    assert 'adjusted_close' not in d['points'][0]
    assert 'SIN AJUSTAR' in d['adjustment']


def test_schema_initialization_does_not_interrupt_another_running_process(client):
    from app.store import initialize
    put('active-process-test','research','TEST',{'symbol':'TEST','status':'running'})
    initialize()
    assert get('active-process-test')['status']=='running'
    initialize(recover_jobs=True)
    assert get('active-process-test')['status']=='interrupted'


def test_research_endpoint_starts_on_running_event_loop(client,monkeypatch):
    import time
    from app.providers import sec,market
    async def company(symbol):return {'symbol':symbol,'name':'Controlled endpoint fixture','currency':'USD','filings':[],'statements':[]}
    async def quote(symbol):raise ProviderError('No controlled quote')
    async def news(*args):return [{'id':'controlled-news','title':'Controlled endpoint source','publisher':'Controlled fixture','url':'https://example.org/test','read_status':'abstract_only','summary':'Controlled test only','full_text':False}]
    monkeypatch.setattr(sec,'company',company);monkeypatch.setattr(market,'quote',quote);monkeypatch.setattr(market,'news',news)
    response=client.post('/research',json={'symbol':'TEST','mode':'quick','use_ai':False})
    assert response.status_code==202
    id=response.json()['id']
    for _ in range(40):
        job=client.get('/records/'+id).json()
        if job['status'] not in ('queued','running'):break
        time.sleep(.01)
    assert job['status']=='completed' and job['stats']['abstract_only']==1
    assert job['ai']['status']=='not_requested'

@pytest.mark.asyncio
async def test_share_class_symbol_mapping_is_confirmed_by_directory(client,monkeypatch):
    from app import providers
    async def transport(url,params=None,**kwargs):
        if url.endswith('/quote'):
            assert params['symbol']=='BRK.B'
            return {'c':100,'t':1700000000}
        return [{'symbol':'BRK.B','currency':'USD','mic':'XNYS'}]
    monkeypatch.setattr(settings,'finnhub_api_key','test');monkeypatch.setattr(providers,'fetch',transport)
    quote=await market.quote('BRK-B')
    assert quote['instrument']['symbol']=='BRK.B'

@pytest.mark.parametrize('stale_annual',[True,False])
def test_market_multiples_require_recent_quote_and_financial_period(client,monkeypatch,stale_annual):
    from datetime import datetime,timezone,timedelta
    from app import main
    clock=datetime.now(timezone.utc);year=clock.year-(3 if stale_annual else 1)
    c={'symbol':'TEST','name':'Controlled stale-data fixture','currency':'USD','statements':[{'end':f'{year}-12-31','values':{'revenue':{'value':100},'net_income':{'value':10},'shares':{'value':10}}}]}
    async def company(symbol):return c
    async def quote(symbol):return {'price':20,'currency':'USD','timestamp':(clock-timedelta(days=1 if stale_annual else 30)).isoformat()}
    monkeypatch.setattr(main.sec,'company',company);monkeypatch.setattr(main.market,'quote',quote)
    r=client.get('/companies/TEST')
    assert r.status_code==200
    assert r.json()['metrics']['pe'] is None
    assert any(w['code']==('annual_too_old' if stale_annual else 'quote_too_old') for w in r.json()['warnings'])
