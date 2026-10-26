import pytest
from app.providers import normalize_facts

def fact(value,start,end,form='10-Q',filed='2024-03-01'):
    return {'val':value,'start':start,'end':end,'form':form,'filed':filed,'accn':'0000000001-24-000001'}

def cumulative_raw():
    durations=[('2023-01-01','2023-03-31','10-Q'),('2023-01-01','2023-06-30','10-Q'),('2023-01-01','2023-09-30','10-Q'),('2023-01-01','2023-12-31','10-K')]
    def data(values):return [fact(v,s,e,f) for v,(s,e,f) in zip(values,durations)]
    return {'facts':{'us-gaap':{
        'Revenues':{'units':{'USD':data([10,30,60,100])}},
        'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':data([2,7,13,20])}},
        'WeightedAverageNumberOfDilutedSharesOutstanding':{'units':{'shares':data([100,110,120,130])}},
        'EarningsPerShareDiluted':{'units':{'USD/shares':data([1,2,3,4])}},
    }}}

def test_ytd_is_differenced_and_terminal_quarter_is_annual_minus_nine_months():
    d=normalize_facts(cumulative_raw(),'1',asof='2024-04-01')
    q=list(reversed(d['quarterly']))
    assert [x['values']['revenue']['value'] for x in q]==[10,20,30,40]
    assert [x['values']['ocf']['value'] for x in q]==[2,5,6,7]
    assert q[-1]['values']['revenue']['quality']=='derived'
    assert len(q[-1]['values']['revenue']['components'])==2
    assert d['ttm']['values']['revenue']['value']==100
    assert d['ttm']['values']['ocf']['value']==20

def test_weighted_shares_reconcile_to_annual_and_eps_is_not_subtracted():
    d=normalize_facts(cumulative_raw(),'1',asof='2024-04-01')
    assert d['ttm']['values']['shares']['value']==pytest.approx(130)
    assert 'eps' not in d['ttm']['values']
    assert 'eps' not in d['quarterly'][0]['values']

def test_missing_quarter_does_not_create_ttm():
    raw=cumulative_raw();raw['facts']['us-gaap']['Revenues']['units']['USD'].pop(1)
    d=normalize_facts(raw,'1',asof='2024-04-01')
    assert d['ttm'] is None

def test_mixed_taxonomy_uses_ifrs_revenue_instead_of_incidental_us_gaap():
    raw={'facts':{'us-gaap':{'Assets':{'units':{'USD':[fact(100,'2023-01-01','2023-12-31','20-F')]}}},'ifrs-full':{'Revenue':{'units':{'USD':[fact(500,'2023-01-01','2023-12-31','20-F')]}},'AdjustedWeightedAverageShares':{'units':{'shares':[fact(25,'2023-01-01','2023-12-31','20-F')]}},'Borrowings':{'units':{'USD':[fact(40,'2023-01-01','2023-12-31','20-F')]}}}}}
    d=normalize_facts(raw,'1',asof='2024-04-01')
    assert d['taxonomy']=='ifrs-full'
    assert d['statements'][0]['values']['revenue']['value']==500
    assert d['statements'][0]['values']['shares']['value']==25
    assert d['statements'][0]['values']['debt']['value']==40


def test_annual_flows_with_different_start_are_not_mixed():
    raw={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[fact(1000,'2025-01-01','2025-12-31','10-K','2026-02-01')]}},'OperatingIncomeLoss':{'units':{'USD':[fact(100,'2025-02-01','2025-12-31','10-K','2026-02-01')]}}}}}
    d=normalize_facts(raw,'1',asof='2026-10-25')
    assert 'ebit' not in d['statements'][0]['values']
