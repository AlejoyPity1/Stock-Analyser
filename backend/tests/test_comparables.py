from datetime import datetime,timezone
from io import BytesIO
import pytest
from pydantic import ValidationError
from pypdf import PdfReader
from app.comparables import ComparableRequest,relative_analysis
from app.store import put,get

ASOF=datetime(2026,10,25,tzinfo=timezone.utc)

def snapshot(symbol,price=20,end='2025-12-31',currency='USD'):
    def val(x):return {'value':x,'unit':currency,'currency':currency,'source':'https://example.org/test','filed':'2026-02-01','period_end':end}
    return {'created_at':ASOF.isoformat(),'company':{'symbol':symbol,'name':'CONTROLLED TEST '+symbol,'sic':'7372','currency':currency,'statements':[{'end':end,'values':{k:val(v) for k,v in {'revenue':1000,'net_income':100,'ebit':180,'da':20,'ocf':150,'capex':50,'shares':100,'debt':300,'cash':100}.items()}}]},'quote':{'price':price,'currency':currency,'timestamp':'2026-10-23T20:00:00+00:00'}}

def request(**kwargs):
    return ComparableRequest(**{'target':'TARGET','peers':['PEERA','PEERB'],'metric':'pe','rationale':'Controlled test group. Comparability is a manual hypothesis, not financial data.',**kwargs})

def bundle():return {'TARGET':snapshot('TARGET'),'PEERA':snapshot('PEERA',10),'PEERB':snapshot('PEERB',20)}


def test_pe_distribution_and_equity_value_known_result():
    r=relative_analysis(request(),bundle(),ASOF)
    assert r['status']=='available'
    assert r['distribution']['median']==15
    assert r['distribution']['q25']==12.5
    assert r['implied_per_share']==15
    assert r['upside']==pytest.approx(-.25)
    assert r['market_multiple_gap']==pytest.approx(20/15-1)
    assert r['target']['snapshot']['period']['values']['net_income']['value']==100


def test_enterprise_multiple_subtracts_net_debt_once():
    b=bundle();b['PEERA']['quote']['price']=18;b['PEERB']['quote']['price']=38
    r=relative_analysis(request(metric='ev_ebitda'),b,ASOF)
    # Peers EV: 2000, 4000; EBITDA 200 → 10× and 20×. Target EV 3000 less net debt 200.
    assert r['distribution']['median']==15
    assert r['implied_equity']==2800
    assert r['implied_per_share']==28
    assert r['net_debt_bridge']==200

@pytest.mark.parametrize('case',['currency','period','stale_quote','classes','negative_income','missing_shares','no_ttm'])
def test_incompatible_peer_excluded_instead_of_filled(case):
    b=bundle();p=b['PEERB'];kwargs={}
    if case=='currency':p['company']['currency']='EUR'
    if case=='period':p['company']['statements'][0]['end']='2025-06-30'
    if case=='stale_quote':p['quote']['timestamp']='2025-01-01T00:00:00+00:00'
    if case=='classes':p['company']['multiple_share_classes']=True
    if case=='negative_income':p['company']['statements'][0]['values']['net_income']['value']=-100
    if case=='missing_shares':del p['company']['statements'][0]['values']['shares']
    if case=='no_ttm':kwargs['basis']='ttm'
    r=relative_analysis(request(**kwargs),b,ASOF)
    assert r['status']=='insufficient_data' and r['implied_per_share'] is None
    assert not r['peers'][1]['eligible'] and r['peers'][1]['reasons']


def test_target_must_also_be_eligible():
    b=bundle();b['TARGET']['quote']['currency']='EUR'
    r=relative_analysis(request(),b,ASOF)
    assert r['status']=='insufficient_data' and r['target']['reasons']

@pytest.mark.parametrize('kwargs',[{'peers':['TARGET','PEERA']},{'peers':['PEERA','PEERA']},{'peers':['bad ticker','PEERA']},{'rationale':'short'}])
def test_selection_is_explicit_and_validated(kwargs):
    with pytest.raises(ValidationError):request(**kwargs)


def test_relative_api_persists_exact_inputs_and_report(client,monkeypatch):
    from app import main
    b=bundle()
    monkeypatch.setattr(main,'relative_analysis',lambda req,rows:relative_analysis(req,rows,ASOF))
    async def controlled_snapshot(symbol):return b[symbol]
    monkeypatch.setattr(main,'snapshot',controlled_snapshot)
    put('relative-test-report','research','TARGET',{'symbol':'TARGET','status':'completed','financial_snapshot':b['TARGET']['company'],'sources':[]})
    payload=request(research_id='relative-test-report').model_dump()
    preview=client.post('/relative-analysis',json=payload)
    assert preview.status_code==200 and preview.json()['implied_per_share']==15
    saved=client.post('/relative-valuations',json=payload)
    assert saved.status_code==200
    id=saved.json()['id'];assert get(id)['inputs']['rationale']==payload['rationale']
    assert get(id)['target']['snapshot']['quote']['price']==20
    report=client.get('/reports/relative-test-report').json()
    assert any(v['id']==id for v in report['relative_valuations'])
    pdf=client.get('/reports/relative-test-report/pdf');text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
    assert id in text and 'relative' in text.lower()


def test_peer_cannot_hide_currency_mismatch_inside_a_fact():
    b=bundle();b['PEERB']['company']['statements'][0]['values']['net_income']['currency']='EUR'
    r=relative_analysis(request(),b,ASOF)
    assert not r['peers'][1]['eligible']
    assert r['implied_per_share'] is None


def test_peer_without_provenance_is_not_used():
    b=bundle();del b['PEERB']['company']['statements'][0]['values']['net_income']['source']
    r=relative_analysis(request(),b,ASOF)
    assert r['accepted_count']==1 and r['status']=='insufficient_data'


def test_financials_do_not_receive_generic_enterprise_multiples():
    b=bundle()
    for s in b.values():s['company']['sic']='6021'
    assert relative_analysis(request(metric='ev_revenue'),b,ASOF)['status']=='insufficient_data'
    assert relative_analysis(request(metric='pe'),b,ASOF)['status']=='available'


def test_pe_uses_parent_income_for_both_multiple_and_implied_equity():
    from copy import deepcopy
    b=bundle();values=b['TARGET']['company']['statements'][0]['values']
    values['net_income']['tag']='ifrs-full:ProfitLoss'
    assert relative_analysis(request(),b,ASOF)['status']=='insufficient_data'
    values['net_income_owners']=deepcopy(values['net_income'])
    values['net_income_owners'].update(value=80,tag='ifrs-full:ProfitLossAttributableToOwnersOfParent')
    r=relative_analysis(request(),b,ASOF)
    assert r['target']['multiple']==25
    assert r['fundamental']==80 and r['implied_equity']==15*80
    del values['net_income_owners']['source']
    assert relative_analysis(request(),b,ASOF)['status']=='insufficient_data'
