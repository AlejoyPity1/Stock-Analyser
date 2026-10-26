import math
import pytest
from pydantic import ValidationError
from app.finance import DCFInput,dcf,ratios,ttm,quant,wacc,reverse_dcf,sensitivity


def model(**kwargs):
    return DCFInput(**{'revenue':1000,'growth':0,'operating_margin':.2,'tax_rate':0,'capex_ratio':0,'da_ratio':0,'nwc_ratio':0,'wacc':.1,'terminal_growth':0,'net_debt':0,'shares':100,**kwargs})


def test_perpetuity_matches_closed_form():
    r=dcf(model())
    assert r['enterprise_value']==pytest.approx(200/.1)
    assert r['fair_value']==pytest.approx(20)
    assert r['projections'][0]['fcff']==200


def test_terminal_nwc_uses_terminal_growth_not_projection_growth():
    r=dcf(model(growth=.1,nwc_ratio=.2,terminal_growth=.02))
    revenue=1000*1.1**5
    assert r['terminal_fcff']==pytest.approx(revenue*1.02*.2-revenue*.02*.2)

@pytest.mark.parametrize('debt,expected',[(0,20),(500,15),(-500,25)])
def test_equity_bridge(debt,expected): assert dcf(model(net_debt=debt))['fair_value']==pytest.approx(expected)


def test_margin_safety_different_from_upside():
    r=dcf(model(price=10,price_currency='USD'))
    assert r['upside']==pytest.approx(1)
    assert r['margin_of_safety']==pytest.approx(.5)

@pytest.mark.parametrize('kwargs',[{'wacc':.02,'terminal_growth':.02},{'shares':0},{'revenue':float('nan')},{'years':4},{'price':10,'price_currency':'EUR'},{'basis':'real'},{'terminal_growth':.08}])
def test_invalid_inputs(kwargs):
    with pytest.raises(ValidationError): model(**kwargs)


def test_negative_fcf_warns_no_fictitious_tax_asset():
    r=dcf(model(operating_margin=-.1,tax_rate=.3))
    assert r['projections'][0]['nopat']==-100
    assert r['margin_of_safety'] is None
    assert len(r['warnings'])>=2


def test_missing_price_no_upside():
    assert dcf(model())['upside'] is None


def test_dilution_halves_value(): assert dcf(model(shares=200))['fair_value']==pytest.approx(10)


def test_reverse_dcf_recovers_known_growth():
    m=model(growth=.08); price=dcf(m)['fair_value']
    assert reverse_dcf(model(price=price,price_currency='USD'))['growth']==pytest.approx(.08,abs=1e-8)


def test_reverse_dcf_does_not_force_solution(): assert reverse_dcf(model(price=1e9,price_currency='USD'))['growth'] is None


def test_sensitivity_center_matches_model():
    m=model(); s=sensitivity(m)
    assert s['rows'][2]['values'][2]==pytest.approx(dcf(m)['fair_value'])
    assert s['rows'][0]['values'][2]>s['rows'][4]['values'][2]


def test_ratios_use_known_units_and_avoid_negative_pe():
    r=ratios({'revenue':1000,'ebit':200,'net_income':-20,'ocf':150,'capex':50,'debt':100,'cash':200,'shares':10,'da':20},price=20)
    assert r['free_cash_flow']==100
    assert r['net_debt']==-100
    assert r['enterprise_value']==100
    assert r['pe'] is None
    assert r['operating_margin']==.2


def test_missing_not_zero():
    r=ratios({'revenue':100})
    assert r['net_debt'] is None and r['free_cash_flow'] is None


def test_ifrs_total_profit_does_not_become_parent_equity_earnings():
    values={'net_income':{'value':120,'tag':'ifrs-full:ProfitLoss'},'shares':10,'equity':100}
    r=ratios(values,20)
    assert r['pe'] is None and r['earnings_yield'] is None and r['roe_end_equity'] is None
    values['net_income_owners']={'value':100,'tag':'ifrs-full:ProfitLossAttributableToOwnersOfParent'}
    r=ratios(values,20)
    assert r['pe']==2 and r['equity_earnings']==100
    assert r['earnings_yield']==.5 and r['roe_end_equity']==1


def quarters():
    return [{'start':s,'end':e,'value':v,'currency':'USD'} for s,e,v in [('2023-01-01','2023-03-31',10),('2023-04-01','2023-06-30',20),('2023-07-01','2023-09-30',30),('2023-10-01','2023-12-31',40)]]


def test_ttm_flow_and_weighted_shares():
    q=quarters(); assert ttm(q)==100
    assert ttm(q,weighted_average=True)==pytest.approx((10*90+20*91+30*92+40*92)/365)

@pytest.mark.parametrize('case',['gap','currency','annual','overlap'])
def test_invalid_ttm(case):
    q=quarters()
    if case=='gap': q[1]['start']='2023-04-02'
    if case=='currency': q[2]['currency']='EUR'
    if case=='annual': q[3]['start']='2023-01-01'
    if case=='overlap': q[2]['start']='2023-06-29'
    with pytest.raises(ValueError): ttm(q)


def test_wacc_capm(): assert wacc(.04,1.2,.05,.06,.25,.2)==pytest.approx(.089)


def test_quant_known_drawdown():
    r=quant([100,120,90,110]); assert r['maximum_drawdown']==pytest.approx(-.25)
    assert r['price_return']==pytest.approx(.1)
    assert r['ma50'] is None


def test_flat_rsi_neutral(): assert quant([100]*20)['rsi14_wilder']==50

@pytest.mark.parametrize('data',[[0,1,2],[1,float('nan'),2],[1,2]])
def test_bad_prices(data):
    with pytest.raises(ValueError): quant(data)


def test_negative_equity_does_not_present_more_than_total_loss_as_upside():
    assert dcf(model(net_debt=3000,price=10,price_currency='USD'))['upside'] is None


def test_benchmark_alignment_and_known_beta():
    from datetime import date,timedelta
    from app.finance import benchmark_metrics
    days=[(date(2024,1,1)+timedelta(days=i)).isoformat() for i in range(30)]
    prices=[100]
    for i in range(29):prices.append(prices[-1]*(1+(.01 if i%2 else -.005)))
    a=[{'date':d,'value':p} for d,p in zip(days,prices)]
    b=[{'date':d,'value':p*2} for d,p in zip(days,prices)]
    r=benchmark_metrics(a,list(reversed(b)))
    assert r['beta']==pytest.approx(1)
    assert r['correlation']==pytest.approx(1)
    assert r['relative_performance']==pytest.approx(0)
    assert r['observations']==29


def test_benchmark_insufficient_common_dates_is_explicit():
    from app.finance import benchmark_metrics
    with pytest.raises(ValueError):benchmark_metrics([{'date':'2024-01-01','value':100}],[])
