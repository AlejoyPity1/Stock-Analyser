"""Deterministic financial calculations. Currency amounts use full units, rates decimals."""
import math
from statistics import median
from typing import Literal
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

class DCFInput(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    revenue: float = Field(gt=0, le=1e16)
    growth: float = Field(default=.05, ge=-.5, le=.5)
    operating_margin: float = Field(default=.2, ge=-1, le=1)
    tax_rate: float = Field(default=.21, ge=0, le=.6)
    capex_ratio: float = Field(default=.05, ge=0, le=1)
    da_ratio: float = Field(default=.03, ge=0, le=1)
    nwc_ratio: float = Field(default=.1, ge=-1, le=1)
    wacc: float = Field(default=.1, gt=0, le=.5)
    terminal_growth: float = Field(default=.025, ge=-.05, le=.05)
    net_debt: float = Field(ge=-1e16, le=1e16)
    shares: float = Field(gt=0, le=1e16)
    years: int = Field(default=5, ge=5, le=10)
    price: float | None = Field(default=None, gt=0)
    currency: str = Field(default='USD', pattern=r'^[A-Z]{3}$')
    price_currency: str | None = Field(default=None, pattern=r'^[A-Z]{3}$')
    basis: Literal['nominal'] = 'nominal'
    rationale: str = Field(default='Supuestos introducidos por el usuario; no son previsiones de consenso.', max_length=4000)

    @model_validator(mode='after')
    def coherent(self):
        if self.wacc <= self.terminal_growth: raise ValueError('WACC debe superar el crecimiento terminal')
        if self.price is not None and self.price_currency != self.currency:
            raise ValueError('Precio y flujos deben usar la misma divisa; no hay conversión implícita')
        return self


def dcf(m: DCFInput):
    revenue=m.revenue; cashflows=[]
    for year in range(1,m.years+1):
        previous=revenue; revenue*=1+m.growth
        ebit=revenue*m.operating_margin
        # Negative EBIT receives no immediate tax credit.
        nopat=ebit-max(ebit,0)*m.tax_rate
        da=revenue*m.da_ratio; capex=revenue*m.capex_ratio
        delta_nwc=(revenue-previous)*m.nwc_ratio
        fcff=nopat+da-capex-delta_nwc
        cashflows.append(dict(year=year,revenue=revenue,ebit=ebit,nopat=nopat,da=da,capex=capex,delta_nwc=delta_nwc,fcff=fcff,pv=fcff/(1+m.wacc)**year))
    # Stable operations at the terminal growth rate, including terminal reinvestment.
    terminal_revenue=revenue*(1+m.terminal_growth)
    terminal_ebit=terminal_revenue*m.operating_margin
    terminal_fcff=terminal_ebit-max(terminal_ebit,0)*m.tax_rate+terminal_revenue*(m.da_ratio-m.capex_ratio)-(terminal_revenue-revenue)*m.nwc_ratio
    terminal=terminal_fcff/(m.wacc-m.terminal_growth)
    pv_terminal=terminal/(1+m.wacc)**m.years
    ev=sum(c['pv'] for c in cashflows)+pv_terminal
    equity=ev-m.net_debt; value=equity/m.shares
    warnings=[]
    if terminal_fcff<=0: warnings.append('Flujo terminal no positivo: Gordon no es una base económica fiable; usa otro modelo.')
    if equity<=0: warnings.append('Equity no positivo; no se interpreta como precio objetivo negociable.')
    if ev>0 and pv_terminal/ev>.8: warnings.append('Más del 80% del valor depende del período terminal.')
    return dict(model_version='fcff-1.0',inputs=m.model_dump(),projections=cashflows,terminal_fcff=terminal_fcff,terminal_value=terminal,pv_terminal=pv_terminal,enterprise_value=ev,equity_value=equity,fair_value=value,upside=value/m.price-1 if m.price and value>0 else None,margin_of_safety=1-m.price/value if m.price and value>0 else None,currency=m.currency,warnings=warnings,formula='FCFF = EBIT − max(EBIT,0)×tax + D&A − capex − ΔNWC; EV = Σ FCFF/(1+WACC)^t + terminal FCFF/(WACC−g)/(1+WACC)^N; Equity = EV − net debt')


def sensitivity(m):
    rows=[]
    for dw in [-.02,-.01,0,.01,.02]:
        w=round(m.wacc+dw,4); cells=[]
        for dg in [-.01,-.005,0,.005,.01]:
            g=round(m.terminal_growth+dg,4)
            cells.append(dcf(DCFInput(**{**m.model_dump(),'wacc':w,'terminal_growth':g}))['fair_value'] if 0<w<=.5 and -.05<=g<=.05 and w>g else None)
        rows.append({'wacc':w,'values':cells})
    growth_margin=[]
    for dg in [-.02,0,.02]:
        for dm in [-.02,0,.02]:
            g=m.growth+dg; margin=m.operating_margin+dm
            if -.5<=g<=.5 and -1<=margin<=1:
                growth_margin.append({'growth':g,'margin':margin,'fair_value':dcf(DCFInput(**{**m.model_dump(),'growth':g,'operating_margin':margin}))['fair_value']})
    return {'terminal_growth':[round(m.terminal_growth+x,4) for x in [-.01,-.005,0,.005,.01]],'rows':rows,'growth_margin':growth_margin}


def reverse_dcf(m):
    if not m.price: return {'growth':None,'reason':'Falta precio compatible'}
    lo,hi=-.5,.5
    f=lambda g: dcf(DCFInput(**{**m.model_dump(),'growth':g}))['fair_value']-m.price
    vals=[f(lo+i*(hi-lo)/50) for i in range(51)]
    if any(vals[i+1]<vals[i] for i in range(50)):
        return {'growth':None,'reason':'La valoración no es monótona en crecimiento bajo estos supuestos.'}
    if vals[0]>0 or vals[-1]<0: return {'growth':None,'reason':'Precio fuera del rango de crecimiento −50% a 50%'}
    for _ in range(100):
        mid=(lo+hi)/2
        if f(mid)>0: hi=mid
        else: lo=mid
    return {'growth':(lo+hi)/2,'interpretation':'Crecimiento constante implícito condicionado al resto de supuestos; no es una previsión.'}


def ratio(a,b,positive=False):
    return a/b if a is not None and b is not None and b!=0 and (not positive or b>0) else None


def owners_equity(v):
    fact=v.get('equity')
    if not isinstance(fact,dict):return fact
    tag=fact.get('tag','')
    if tag and tag not in ('us-gaap:StockholdersEquity','ifrs-full:EquityAttributableToOwnersOfParent'):return None
    return fact.get('value')


def ratios(v, price=None):
    r={k:x.get('value') if isinstance(x,dict) else x for k,x in v.items()}
    revenue=r.get('revenue'); ebit=r.get('ebit'); ni=r.get('net_income')
    income_fact=v.get('net_income',{})
    income_tag=income_fact.get('tag','') if isinstance(income_fact,dict) else ''
    owner_income=r.get('net_income_owners')
    if owner_income is None and (not income_tag or income_tag=='us-gaap:NetIncomeLoss'):owner_income=ni
    cash=r.get('cash'); debt=r.get('debt'); shares=r.get('shares')
    fcf=r.get('ocf')-r.get('capex') if r.get('ocf') is not None and r.get('capex') is not None else None
    nd=debt-cash if debt is not None and cash is not None else None
    mc=price*shares if price and shares else None
    ev=mc+nd if mc is not None and nd is not None else None
    ebitda=ebit+r['da'] if ebit is not None and r.get('da') is not None else None
    return {'free_cash_flow':fcf,'net_debt':nd,'market_cap':mc,'enterprise_value':ev,'equity_earnings':owner_income,'gross_margin':ratio(r.get('gross_profit'),revenue),'operating_margin':ratio(ebit,revenue),'net_margin':ratio(ni,revenue),'fcf_margin':ratio(fcf,revenue),'pe':ratio(mc,owner_income,True),'p_fcf':ratio(mc,fcf,True),'ev_revenue':ratio(ev,revenue,True),'ev_ebitda':ratio(ev,ebitda,True),'fcf_yield':ratio(fcf,mc,True),'earnings_yield':ratio(owner_income,mc,True),'debt_ebitda':ratio(debt,ebitda,True),'interest_coverage':ratio(ebit,r.get('interest'),True),'roe_end_equity':ratio(owner_income,owners_equity(v),True),'roa_end_assets':ratio(ni,r.get('assets'),True)}


def ttm(periods, weighted_average=False):
    """Four contiguous standalone quarters only; never sum cumulative YTD/annual data."""
    from datetime import date
    if len(periods)!=4 or len({p['currency'] for p in periods})!=1: raise ValueError('Cuatro trimestres y una divisa requeridos')
    ps=sorted(periods,key=lambda p:p['end']); days=[]
    for i,p in enumerate(ps):
        d=(date.fromisoformat(p['end'])-date.fromisoformat(p['start'])).days+1
        if not 70<=d<=110: raise ValueError('No es un trimestre independiente')
        if i and (date.fromisoformat(p['start'])-date.fromisoformat(ps[i-1]['end'])).days!=1: raise ValueError('Períodos no contiguos')
        days.append(d)
    return sum(p['value']*d for p,d in zip(ps,days))/sum(days) if weighted_average else sum(p['value'] for p in ps)


def quant(prices,adjusted=True):
    if len(prices)<3 or any(not math.isfinite(p) or p<=0 for p in prices): raise ValueError('Se requieren al menos 3 precios positivos')
    a=np.array(prices,dtype=float); ret=a[1:]/a[:-1]-1
    ma=lambda n: float(a[-n:].mean()) if len(a)>=n else None
    gains=np.maximum(np.diff(a),0); losses=np.maximum(-np.diff(a),0)
    rsi=None
    if len(gains)>=14:
        ag=gains[:14].mean(); al=losses[:14].mean()
        for g,l in zip(gains[14:],losses[14:]): ag=(ag*13+g)/14; al=(al*13+l)/14
        rsi=100-100/(1+ag/al) if al else (100.0 if ag else 50.0)
    return {'price_return':float(a[-1]/a[0]-1),'annualized_volatility':float(np.std(ret,ddof=1)*np.sqrt(252)),'maximum_drawdown':float(np.min(a/np.maximum.accumulate(a)-1)),'ma50':ma(50),'ma200':ma(200),'rsi14_wilder':rsi,'methodology':('Rendimientos diarios de cierre ajustado. ' if adjusted else 'Cierres SIN AJUSTAR: splits/dividendos pueden distorsionar las métricas. ')+'252 sesiones/año. RSI Wilder. Descriptivo; no predictivo.'}


def wacc(risk_free,beta,equity_premium,cost_debt,tax,debt_weight):
    if not 0<=debt_weight<=1 or not 0<=tax<=1: raise ValueError('Pesos/tasa fuera de rango')
    return (risk_free+beta*equity_premium)*(1-debt_weight)+cost_debt*(1-tax)*debt_weight


def benchmark_metrics(stock,benchmark):
    """Align observed sessions, then calculate covariance; never align by array position."""
    left={p['date']:p['value'] for p in stock};right={p['date']:p['value'] for p in benchmark}
    dates=sorted(left.keys() & right.keys())
    if len(dates)<21:raise ValueError('Se requieren al menos 21 sesiones comunes para comparar')
    a=np.array([left[d] for d in dates],dtype=float);b=np.array([right[d] for d in dates],dtype=float)
    if np.any(~np.isfinite(a)) or np.any(~np.isfinite(b)) or np.any(a<=0) or np.any(b<=0):raise ValueError('Precios positivos y finitos requeridos')
    ar=a[1:]/a[:-1]-1;br=b[1:]/b[:-1]-1;variance=float(np.var(br,ddof=1))
    beta=float(np.cov(ar,br,ddof=1)[0,1]/variance) if variance>0 else None
    corr=float(np.corrcoef(ar,br)[0,1]) if variance>0 and float(np.var(ar))>0 else None
    return {'beta':beta,'correlation':corr,'observations':len(dates)-1,'start':dates[0],'end':dates[-1],'stock_return':float(a[-1]/a[0]-1),'benchmark_return':float(b[-1]/b[0]-1),'relative_performance':float((a[-1]/a[0])/(b[-1]/b[0])-1),'methodology':'Retornos entre las mismas sesiones observadas; beta = cov(stock, benchmark)/var(benchmark), ddof=1. No es una predicción.'}
