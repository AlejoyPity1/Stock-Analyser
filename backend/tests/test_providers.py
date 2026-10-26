import pytest
from app.providers import normalize_facts,ProviderError,sec,fetch
from app.research import deduplicate


def filing(val,start='2023-01-01',end='2023-12-31',filed='2024-02-01',form='10-K'):
    return {'val':val,'start':start,'end':end,'filed':filed,'form':form,'accn':'0000000001-24-000001'}


def raw_data():
    return {'facts':{'us-gaap':{'Revenues':{'units':{'USD':[filing(1000),filing(250,start='2023-10-01'),filing(9999,filed='2028-02-01')] }},'WeightedAverageNumberOfDilutedSharesOutstanding':{'units':{'shares':[filing(100)]}},'CashAndCashEquivalentsAtCarryingValue':{'units':{'USD':[filing(30)]}}}}}


def test_annual_filters_quarters_and_future_filings():
    result=normalize_facts(raw_data(),'1',asof='2025-01-01')
    assert len(result['statements'])==1
    v=result['statements'][0]['values']
    assert v['revenue']['value']==1000
    assert v['shares']['unit']=='shares'
    assert 'debt' not in v
    assert v['revenue']['accession']=='0000000001-24-000001'


def test_currency_not_relabelled():
    raw=raw_data(); raw['facts']['us-gaap']['Revenues']['units']={'EUR':[filing(1000)]}
    r=normalize_facts(raw,'1'); assert r['currency']=='EUR'
    assert 'cash' not in r['statements'][0]['values']


def test_restated_latest_as_of():
    raw=raw_data(); raw['facts']['us-gaap']['Revenues']['units']['USD'].append(filing(1200,filed='2024-03-01'))
    assert normalize_facts(raw,'1',asof='2024-04-01')['statements'][0]['values']['revenue']['value']==1200
    assert normalize_facts(raw,'1',asof='2024-02-15')['statements'][0]['values']['revenue']['value']==1000


def test_no_revenue_currency():
    with pytest.raises(ProviderError): normalize_facts({'facts':{}},'1')


def test_news_dedup_by_canonical_url():
    r=deduplicate([{'url':'https://example.org/story?utm_source=a','id':'a'},{'url':'https://example.org/story?utm_source=b#x','id':'b'}])
    assert len(r)==1

@pytest.mark.asyncio
async def test_no_arbitrary_document_fetch():
    with pytest.raises(ProviderError) as error: await sec.read_document('http://169.254.169.254/latest/meta-data')
    assert error.value.code=='unsafe_url'

@pytest.mark.asyncio
async def test_network_whitelist_not_bypassable():
    with pytest.raises(ProviderError): await fetch('https://evil.example/test')


def test_actual_missing_config_is_explicit(client):
    r=client.get('/companies/AAPL'); assert r.status_code==503
    assert r.json()['code']=='missing_configuration'


def test_invalid_ticker_not_a_network_url(client):
    assert client.get('/companies/invalid%20ticker').status_code==422

@pytest.mark.asyncio
async def test_transport_retries_then_caches(client,monkeypatch):
    import httpx
    from app import providers
    calls=[]
    async def no_sleep(seconds): pass
    monkeypatch.setattr(providers.asyncio,'sleep',no_sleep)
    def handler(request):
        calls.append(1)
        return httpx.Response(503 if len(calls)==1 else 200,json={'value':42})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler)))
    a=await fetch('https://finnhub.io/api/v1/test-controlled-cache',ttl=3600)
    b=await fetch('https://finnhub.io/api/v1/test-controlled-cache',ttl=3600)
    assert a==b=={'value':42}
    assert len(calls)==2
