"""Controlled, hand-checkable fixtures. No real company claims or external calls."""
from datetime import datetime,timezone
import pytest
from app.analytics import advanced_analytics

ASOF=datetime(2026,10,25,tzinfo=timezone.utc)

def value(number,end='2025-12-31'):
    return {'value':number,'unit':'USD','currency':'USD','period_end':end,'filed':'2026-02-01','source':'https://example.org/controlled-test'}

def company():
    current={k:value(v) for k,v in {'revenue':1000,'ebit':200,'tax_expense':30,'pretax_income':150,'net_income':120,'assets':1000,'liabilities':500,'equity':500,'equity_total':500,'debt':200,'cash':100}.items()}
    previous={k:value(v,'2024-12-31') for k,v in {'revenue':800,'assets':800,'liabilities':400,'equity':400,'equity_total':400,'debt':100,'cash':50}.items()}
    return {'symbol':'TEST','currency':'USD','sic':'3571','statements':[{'end':'2025-12-31','values':current},{'end':'2024-12-31','values':previous}]}


def test_average_balances_and_roic_effective_tax():
    a=advanced_analytics(company(),asof=ASOF)['metrics']
    assert a['roe_average']['value']==pytest.approx(120/450)
    assert a['roa_average']['value']==pytest.approx(120/900)
    assert a['roic_average']['value']==pytest.approx(160/525)
    assert a['roic_average']['inputs']['nopat_proxy']==160
    assert a['revenue_growth']['value']==pytest.approx(.25)


def test_financial_sector_does_not_receive_generic_roic():
    c=company();c['sic']='6021';a=advanced_analytics(c,asof=ASOF)
    assert a['metrics']['roic_average']['value'] is None
    assert 'sectorial' in a['metrics']['roic_average']['reason']

@pytest.mark.parametrize('field,number',[('tax_expense',-10),('tax_expense',200),('pretax_income',0),('cash',1000)])
def test_uninterpretable_tax_or_capital_never_imputed(field,number):
    c=company();c['statements'][0]['values'][field]['value']=number
    assert advanced_analytics(c,asof=ASOF)['metrics']['roic_average']['value'] is None


def test_nonconsecutive_years_do_not_create_average_return():
    c=company();c['statements'][1]['end']='2023-12-31'
    a=advanced_analytics(c,asof=ASOF)
    assert a['metrics']['roic_average']['value'] is None
    assert a['metrics']['revenue_growth']['value'] is None


def test_balance_check_is_independent_and_flags_difference():
    c=company();a=advanced_analytics(c,asof=ASOF)
    assert a['coverage']['balance_check']['status']=='consistent'
    c['statements'][0]['values']['equity_total']['value']=450
    assert advanced_analytics(c,asof=ASOF)['coverage']['balance_check']['status']=='requires_review'
    del c['statements'][0]['values']['equity_total']
    assert advanced_analytics(c,asof=ASOF)['coverage']['balance_check']['status']=='not_checked'
    assert advanced_analytics(c,asof=ASOF)['metrics']['roic_average']['value'] is not None


def test_coverage_detects_missing_fields_currency_and_future_publication():
    c=company();c['statements'][0]['values']['revenue']['currency']='EUR';c['statements'][0]['values']['ebit']['filed']='2027-01-01'
    q=advanced_analytics(c,asof=ASOF)['coverage']
    assert 'revenue' in q['currency_mismatches'] and 'ebit' in q['chronology_issues']
    assert 'capex' in q['missing_fields']
    assert q['present_count']<q['expected_count']


def test_five_year_cagr_requires_six_consecutive_closes():
    c=company();c['statements']=[{'end':f'{2025-i}-12-31','values':{'revenue':value(100*1.1**(5-i),f'{2025-i}-12-31')}} for i in range(6)]
    assert advanced_analytics(c,asof=ASOF)['metrics']['revenue_cagr_5y']['value']==pytest.approx(.1)
    c['statements'].pop()
    assert advanced_analytics(c,asof=ASOF)['metrics']['revenue_cagr_5y']['value'] is None


def test_ifrs_total_income_is_not_assumed_to_belong_to_parent():
    c=company();c['statements'][0]['values']['net_income']['tag']='ifrs-full:ProfitLoss'
    assert advanced_analytics(c,asof=ASOF)['metrics']['roe_average']['value'] is None
    c['statements'][0]['values']['net_income_owners']=value(100)
    assert advanced_analytics(c,asof=ASOF)['metrics']['roe_average']['value']==pytest.approx(100/450)


def test_total_equity_is_not_assumed_to_belong_to_parent():
    from app.finance import ratios
    c=company();v=c['statements'][0]['values']
    v['equity']['tag']='ifrs-full:Equity'
    assert advanced_analytics(c,asof=ASOF)['metrics']['roe_average']['value'] is None
    assert ratios(v)['roe_end_equity'] is None
    v['equity']['tag']='ifrs-full:EquityAttributableToOwnersOfParent'
    assert advanced_analytics(c,asof=ASOF)['metrics']['roe_average']['value']==pytest.approx(120/450)


def test_mixed_currency_or_future_fact_is_excluded_from_calculations():
    c=company();c['statements'][0]['values']['tax_expense']['currency']='EUR'
    a=advanced_analytics(c,asof=ASOF)
    assert a['metrics']['roic_average']['value'] is None
    assert {'field':'tax_expense','reason':'Divisa inconsistente'} in a['coverage']['excluded_fields']
    c=company();c['statements'][0]['values']['net_income']['filed']='2027-01-01'
    assert advanced_analytics(c,asof=ASOF)['metrics']['roe_average']['value'] is None


def test_mismatched_flow_duration_does_not_produce_roic():
    c=company();v=c['statements'][0]['values']
    v['revenue']['period_start']='2025-01-01';v['ebit']['period_start']='2024-10-01'
    assert advanced_analytics(c,asof=ASOF)['metrics']['roic_average']['value'] is None


def test_old_financials_are_flagged_separately_from_field_coverage():
    c=company();a=advanced_analytics(c,asof=datetime(2028,1,1,tzinfo=timezone.utc))
    assert a['coverage']['annual_data_outdated'] is True
    assert a['coverage']['present_count']>0


@pytest.mark.parametrize('field,bad_value',[('currency','EUR'),('filed','2027-01-01'),('period_end','2021-01-01')])
def test_cagr_checks_oldest_fact_before_combining_years(field,bad_value):
    c=company();c['statements']=[{'end':f'{2025-i}-12-31','values':{'revenue':value(100*1.1**(5-i),f'{2025-i}-12-31')}} for i in range(6)]
    c['statements'][-1]['values']['revenue'][field]=bad_value
    a=advanced_analytics(c,asof=ASOF)
    assert a['metrics']['revenue_cagr_5y']['value'] is None
    assert any(v['field']=='five_years_ago.revenue' for v in a['coverage']['excluded_fields'])
