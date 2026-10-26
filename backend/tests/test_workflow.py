import asyncio
import pytest
from app.config import settings
from app.store import get,put
from app.providers import sec,market,ProviderError
from app.research import run,ResearchRequest,synthesize


def inputs(**kw):
    return {'revenue':1000,'growth':0,'operating_margin':.2,'tax_rate':0,'capex_ratio':0,'da_ratio':0,'nwc_ratio':0,'wacc':.1,'terminal_growth':0,'net_debt':0,'shares':100,**kw}


def test_api_valuation_and_audit(client):
    first=client.post('/valuations',json={'symbol':'TEST','inputs':inputs(),'justification':'Controlled test case, not real financial data.'}).json()
    second=client.post('/valuations',json={'symbol':'TEST','inputs':inputs(net_debt=500),'justification':'Debt change for controlled test.','parent_id':first['id']}).json()
    assert second['fair_value']==pytest.approx(15)
    assert second['value_effect']==pytest.approx(-5)
    assert second['changes']==[{'field':'net_debt','old':0,'new':500}]
    assert client.get('/records/'+second['id']).json()['fair_value']==second['fair_value']
    assert client.get('/reports/'+first['id']).json()['record']['id']==first['id']


def test_nonexistent_parent_or_source_rejected(client):
    base={'symbol':'TEST','inputs':inputs(),'justification':'Controlled test case.'}
    assert client.post('/valuations',json={**base,'parent_id':'missing'}).status_code==422
    assert client.post('/valuations',json={**base,'source_id':'invented'}).status_code==422


def test_watchlist_persists_and_deletes(client):
    assert client.post('/watchlist',json={'symbol':'TEST','note':'test only'}).status_code==200
    assert any(r['symbol']=='TEST' for r in client.get('/watchlist').json())
    client.delete('/watchlist/TEST')
    assert not any(r['symbol']=='TEST' for r in client.get('/watchlist').json())


def test_secrets_never_returned(client,monkeypatch):
    monkeypatch.setattr(settings,'research_api_key','secret-value-do-not-leak')
    response=client.get('/settings')
    assert 'secret-value' not in response.text
    assert response.json()['providers']['openai']['configured'] is True


def test_auth_required_when_configured(client,monkeypatch):
    monkeypatch.setattr(settings,'app_token','test-server-token')
    assert client.get('/watchlist').status_code==401
    assert client.get('/health').status_code==200
    assert client.get('/watchlist',headers={'Authorization':'Bearer test-server-token'}).status_code==200


def test_scenarios_no_mixed_currencies(client):
    assert client.post('/scenarios',json={'bear':inputs(),'base':inputs(),'bull':inputs(currency='EUR')}).status_code==422


def test_relative_ev_equity_bridge(client):
    r=client.post('/relative',json={'metric':'ev_ebitda','peer_multiples':[10,12,20],'target_fundamental':100,'net_debt':200,'shares':100,'comparability_rationale':'Manual peers: same industry and normalized annual period.'})
    assert r.status_code==200
    assert r.json()['median']==12
    assert r.json()['implied_per_share']==10


def test_screen_excludes_missing_values(client):
    put('snapshot:SCREEN','snapshot','SCREEN',{'company':{'name':'Controlled fixture','statements':[]},'metrics':{'pe':None,'operating_margin':.1},'created_at':'2024-01-01'})
    r=client.get('/screen?max_pe=15').json()
    assert not any(row['symbol']=='SCREEN' for row in r['rows'])

@pytest.mark.asyncio
async def test_research_cannot_invent_success(client,monkeypatch):
    async def fail(symbol): raise ProviderError('SEC blocked','network_error')
    monkeypatch.setattr(sec,'company',fail)
    id='test-failed-research'; req=ResearchRequest(symbol='TEST')
    put(id,'research','TEST',{'symbol':'TEST','status':'queued','request':req.model_dump(),'sources':[]})
    await run(id,req)
    assert get(id)['status']=='failed'
    assert get(id)['sources']==[]

@pytest.mark.asyncio
async def test_research_tracks_inaccessible_documents(client,monkeypatch):
    async def company(symbol):
        return {'symbol':symbol,'name':'Controlled TEST fixture','currency':'USD','filings':[{'id':'f1','title':'test document','publisher':'SEC EDGAR','url':'https://www.sec.gov/Archives/edgar/data/1/doc.htm','read_status':'not_read','full_text':False}]}
    async def fail_read(url): raise ProviderError('Blocked document')
    async def no_news(*args): raise ProviderError('Missing key','missing_credentials')
    monkeypatch.setattr(sec,'company',company); monkeypatch.setattr(sec,'read_document',fail_read); monkeypatch.setattr(market,'news',no_news)
    id='test-partial'; req=ResearchRequest(symbol='TEST',mode='deep')
    put(id,'research','TEST',{'symbol':'TEST','status':'queued','request':req.model_dump()})
    await run(id,req); job=get(id)
    assert job['status']=='partial'
    assert job['stats']['inaccessible']==1
    assert job['stats']['read_documents']==0
    assert job['ai']['status']=='not_requested'

@pytest.mark.asyncio
async def test_ai_budget_blocks_before_charge(client,monkeypatch):
    monkeypatch.setattr(settings,'ai_provider','openai')
    monkeypatch.setattr(settings,'paid_ai_enabled',True)
    monkeypatch.setattr(settings,'research_api_key','controlled-test-key')
    monkeypatch.setattr(settings,'ai_input_usd_per_million',100)
    monkeypatch.setattr(settings,'ai_output_usd_per_million',100)
    with pytest.raises(ProviderError) as error: await synthesize([],ResearchRequest(symbol='TEST',use_ai=True,budget_usd=.01))
    assert error.value.code=='budget_exceeded'

@pytest.mark.asyncio
@pytest.mark.parametrize('quote,expected',[('Revenue increased during the reported period.','generated_quote_verified'),('Invented statement not in the document.','rejected')])
async def test_ai_quotes_must_match_retrieved_source(client,monkeypatch,quote,expected):
    import httpx
    import json
    from app.horizon import investment_horizon
    horizon=investment_horizon(started_at='2024-01-31T12:00:00Z')
    monkeypatch.setattr(settings,'ai_provider','openai')
    monkeypatch.setattr(settings,'paid_ai_enabled',True)
    monkeypatch.setattr(settings,'research_api_key','controlled-test-key')
    monkeypatch.setattr(settings,'ai_input_usd_per_million',1)
    monkeypatch.setattr(settings,'ai_output_usd_per_million',1)
    data={'claims':[{'side':'neutral','kind':'reported_fact','text':'Controlled claim.','source_id':'test-source','evidence_quote':quote,'financial_mechanism':'Review cash flows; no automatic modification.'}],'unresolved':[],'contradictions':[]}
    def handler(request):
        body=json.loads(request.content)
        assert body['store'] is False and body['text']['format']['strict'] is True
        assert json.loads(body['input'][1]['content'])['investment_horizon']==horizon
        return httpx.Response(200,json={'status':'completed','usage':{'input_tokens':100,'output_tokens':200},'output':[{'content':[{'type':'output_text','text':json.dumps(data)}]}]})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler)))
    r=await synthesize([{'id':'test-source','title':'Controlled document','text':'Revenue increased during the reported period.','read_status':'read'}],ResearchRequest(symbol='TEST',use_ai=True,budget_usd=.1),horizon)
    assert r['status']==expected
    assert r['billing']['usage']['input_tokens']==100
    assert r['billing']['estimated_cost_usd']==pytest.approx(.0003)


def test_evidence_based_change_is_audited(client):
    put('research-audit','research','TEST',{'symbol':'TEST','sources':[{'id':'filing-1','read_status':'read','title':'Controlled evidence fixture','url':'https://www.sec.gov/Archives/edgar/data/1/test.htm'}]})
    a=client.post('/valuations',json={'symbol':'TEST','inputs':inputs(),'justification':'Controlled valuation fixture.'}).json()
    b=client.post('/valuations',json={'symbol':'TEST','inputs':inputs(operating_margin=.25),'justification':'Conditional margin change based on controlled test evidence.','parent_id':a['id'],'research_id':'research-audit','source_id':'filing-1'}).json()
    assert b['source']['id']=='filing-1'
    assert b['changes']==[{'field':'operating_margin','old':.2,'new':.25}]
    assert b['value_effect']==pytest.approx(5)
    report=client.get('/reports/research-audit').json()
    assert any(v['id']==b['id'] for v in report['related_valuations'])


def test_report_preserves_research_snapshot(client):
    put('research-old','research','TEST',{'symbol':'TEST','financial_snapshot':{'name':'Old controlled snapshot'},'valuation_ids':[]})
    put('snapshot:TEST','snapshot','TEST',{'name':'New unrelated snapshot'})
    assert client.get('/reports/research-old').json()['snapshot']['name']=='Old controlled snapshot'
