"""Reproducible annual profitability and coverage. Coverage is not an investment score."""
import math
from datetime import date, datetime, timezone
from .store import now
from .finance import owners_equity

CORE = ('revenue','ebit','net_income','eps','shares','cash','assets','liabilities','equity','debt','ocf','capex','da','gross_profit','sbc','dividends','buybacks','current_assets','current_liabilities','interest')


def number(values, key):
    fact=values.get(key)
    value=fact.get('value') if isinstance(fact,dict) else fact
    return value if isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) else None


def total_equity(values):
    total=number(values,'equity_total')
    if total is not None:return total,{'equity_total':values['equity_total']},'Reported total equity'
    assets=number(values,'assets');liabilities=number(values,'liabilities')
    if assets is not None and liabilities is not None:
        return assets-liabilities,{'assets':values['assets'],'liabilities':values['liabilities']},'Total equity = assets − liabilities (derived)'
    return None,{},'Total equity unavailable'


def advanced_analytics(company, quote=None, asof=None):
    asof=asof or datetime.now(timezone.utc)
    if asof.tzinfo is None:asof=asof.replace(tzinfo=timezone.utc)
    annual=company.get('statements',[]);latest=annual[0] if annual else None
    original=latest['values'] if latest else {};previous=annual[1] if len(annual)>1 else None
    excluded=[];currency_issues=[];chronology_issues=[]
    balances={'assets','liabilities','equity','equity_total','cash','debt','current_assets','current_liabilities'}
    def valid_values(values,end,prefix):
        result={};start=values.get('revenue',{}).get('period_start') if isinstance(values.get('revenue'),dict) else None
        for key,fact in values.items():
            reason=None
            if isinstance(fact,dict):
                if fact.get('currency') and fact['currency']!=company.get('currency'):
                    reason='Divisa inconsistente';currency_issues.append(prefix+key)
                elif fact.get('period_end') and end and fact['period_end']!=end:reason='Cierre de la partida incompatible'
                elif key not in balances and start and fact.get('period_start') and fact['period_start']!=start:reason='Duración de flujo incompatible'
                elif fact.get('filed') and (fact['filed']>asof.date().isoformat() or (fact.get('period_end') and fact['filed']<fact['period_end'])):
                    reason='Fecha de presentación incompatible';chronology_issues.append(prefix+key)
            if reason:excluded.append({'field':prefix+key,'reason':reason})
            else:result[key]=fact
        return result
    current=valid_values(original,latest['end'] if latest else None,'')
    prior=valid_values(previous['values'],previous['end'],'opening.') if previous else {}
    metrics={}
    consecutive=False
    if latest and previous:
        gap=(date.fromisoformat(latest['end'])-date.fromisoformat(previous['end'])).days
        consecutive=300<=gap<=380
    def add(key,label,formula,value=None,reason=None,inputs=None,limitations=None):
        metrics[key]={'label':label,'value':value,'status':'available' if value is not None else 'unavailable','formula':formula,'reason':reason if value is None else None,'inputs':inputs or {},'limitations':limitations or [],'unit':'ratio','period_end':latest['end'] if latest else None,'previous_period_end':previous['end'] if previous and consecutive else None}
    ni=number(current,'net_income');equity=owners_equity(current);prev_equity=owners_equity(prior)
    owner_income=number(current,'net_income_owners')
    if owner_income is None:
        f=current.get('net_income',{});tag=f.get('tag','') if isinstance(f,dict) else ''
        if not tag or tag=='us-gaap:NetIncomeLoss':owner_income=ni
    roe=None
    if consecutive and owner_income is not None and equity is not None and prev_equity is not None and equity>0 and prev_equity>0:roe=owner_income/((equity+prev_equity)/2)
    add('roe_average','ROE sobre patrimonio medio','Net income attributable to owners / ((opening owners equity + closing owners equity) / 2)',roe,'Se necesitan ejercicios consecutivos, beneficio atribuible a propietarios y patrimonio positivo en ambos cierres.',{'income':current.get('net_income_owners') or current.get('net_income'),'opening_equity':prior.get('equity'),'closing_equity':current.get('equity')},['Media de dos cierres; no patrimonio medio diario.'])
    assets=number(current,'assets');old_assets=number(prior,'assets');roa=None
    if consecutive and ni is not None and assets is not None and old_assets is not None and assets>0 and old_assets>0:roa=ni/((assets+old_assets)/2)
    add('roa_average','ROA sobre activos medios','Reported net income / ((opening assets + closing assets) / 2)',roa,'Se necesitan dos cierres consecutivos con activos positivos y beneficio disponible.',{'income':current.get('net_income'),'opening_assets':prior.get('assets'),'closing_assets':current.get('assets')},['Proxy contable: el resultado reportado puede incluir partidas no operativas y diferencias por participaciones no controladoras.'])
    roic=None;roic_inputs={};reason='Faltan EBIT, impuestos, resultado antes de impuestos o capital invertido de dos cierres consecutivos.'
    ebit=number(current,'ebit');tax=number(current,'tax_expense');pretax=number(current,'pretax_income')
    eq,eq_inputs,eq_method=total_equity(current);old_eq,old_eq_inputs,old_method=total_equity(prior)
    debt=number(current,'debt');old_debt=number(prior,'debt');cash=number(current,'cash');old_cash=number(prior,'cash')
    try:financial=6000<=int(company.get('sic') or 0)<=6999
    except ValueError:financial=False
    if financial:reason='El ROIC industrial genérico no se aplica a entidades financieras; se requiere metodología sectorial.'
    elif consecutive and all(v is not None for v in (ebit,tax,pretax,eq,old_eq,debt,old_debt,cash,old_cash)):
        if pretax<=0 or tax<0 or tax>pretax:reason='La tasa fiscal efectiva no es interpretable entre 0% y 100%; no se inventa una tasa normalizada.'
        else:
            capital=eq+debt-cash;opening=old_eq+old_debt-old_cash
            if capital<=0 or opening<=0:reason='Capital invertido no positivo en uno de los cierres; ratio no interpretable.'
            else:
                effective_tax=tax/pretax;nopat=ebit-max(ebit,0)*effective_tax
                roic=nopat/((capital+opening)/2)
                roic_inputs={'ebit':current['ebit'],'tax_expense':current['tax_expense'],'pretax_income':current['pretax_income'],'effective_tax':effective_tax,'nopat_proxy':nopat,'closing_invested_capital':capital,'opening_invested_capital':opening,'opening_sources':{**old_eq_inputs,'debt':prior['debt'],'cash':prior['cash']},'closing_sources':{**eq_inputs,'debt':current['debt'],'cash':current['cash']},'equity_methods':[old_method,eq_method]}
    add('roic_average','ROIC contable aproximado','NOPAT proxy / average(total equity + debt − cash); NOPAT proxy = EBIT − max(EBIT,0) × (tax expense / pretax income)',roic,reason,roic_inputs,['Usa todos los saldos de efectivo, no una estimación de efectivo excedentario.','Tasa fiscal corporativa observada como proxy operativa; puede distorsionarse por partidas extraordinarias.','Sin ajustes adicionales por goodwill, I+D capitalizado o arrendamientos fuera de la deuda reportada.'])
    revenue=number(current,'revenue');old_revenue=number(prior,'revenue');growth=None
    if consecutive and revenue is not None and old_revenue is not None and old_revenue>0:growth=revenue/old_revenue-1
    add('revenue_growth','Crecimiento anual de ingresos','Latest annual revenue / previous consecutive annual revenue − 1',growth,'Se requieren dos ejercicios anuales consecutivos con ingresos anteriores positivos.',{'current':current.get('revenue'),'previous':prior.get('revenue')})
    cagr=None;inputs={}
    if len(annual)>=6:
        window=annual[:6]
        aligned=all(300<=(date.fromisoformat(window[i]['end'])-date.fromisoformat(window[i+1]['end'])).days<=380 for i in range(5))
        first_values=valid_values(window[-1]['values'],window[-1]['end'],'five_years_ago.')
        first=number(first_values,'revenue')
        if aligned and first is not None and first>0 and revenue is not None and revenue>0:
            cagr=(revenue/first)**.2-1;inputs={'latest':current['revenue'],'five_fiscal_years_ago':first_values['revenue']}
    add('revenue_cagr_5y','CAGR de ingresos · 5 ejercicios','(Latest revenue / revenue five fiscal years earlier)^(1/5) − 1',cagr,'Se necesitan seis cierres anuales consecutivos con ingresos positivos.',inputs)
    present=[k for k in CORE if number(current,k) is not None];missing=[k for k in CORE if k not in present]
    chronology=[];currencies=[];missing_provenance=[]
    for key in present:
        fact=current[key]
        if not isinstance(fact,dict):missing_provenance.append(key);continue
        if not fact.get('source') or not fact.get('filed') or not fact.get('unit'):missing_provenance.append(key)
        if fact.get('currency') and fact['currency']!=company.get('currency'):currencies.append(key)
        if fact.get('filed') and (fact['filed']>asof.date().isoformat() or (fact.get('period_end') and fact['filed']<fact['period_end'])):chronology.append(key)
    balance={'status':'not_checked','reason':'Falta patrimonio total reportado para una comprobación independiente.'}
    reported_eq=number(current,'equity_total');liabilities=number(current,'liabilities')
    if all(v is not None for v in (assets,liabilities,reported_eq)):
        difference=assets-liabilities-reported_eq;tolerance=max(1,abs(assets)*.00001)
        balance={'status':'consistent' if abs(difference)<=tolerance else 'requires_review','difference':difference,'tolerance':tolerance,'formula':'Assets − liabilities − reported total equity','inputs':{k:current[k] for k in ['assets','liabilities','equity_total']}}
    age=None
    if quote and quote.get('timestamp'):
        age=(asof-datetime.fromisoformat(quote['timestamp'])).total_seconds()/86400
    period_age=(asof.date()-date.fromisoformat(latest['end'])).days if latest else None
    coverage={'latest_period_age_days':period_age,'annual_data_outdated':period_age is not None and period_age>550,'present_count':len(present),'expected_count':len(CORE),'present_fields':present,'missing_fields':missing,'currency_mismatches':sorted(set(currencies+currency_issues)),'chronology_issues':sorted(set(chronology+chronology_issues)),'excluded_fields':excluded,'fields_without_provenance':missing_provenance,'annual_periods':len(annual),'quarters':len(company.get('quarterly',[])),'ttm_available':bool(company.get('ttm')),'balance_check':balance,'quote_age_days':age,'quote_currency_compatible':bool(quote and quote.get('currency')==company.get('currency')),'multiple_share_classes':company.get('multiple_share_classes',False),'interpretation':'Cobertura de campos y controles de consistencia; no es una puntuación de calidad empresarial ni una validación de auditoría.'}
    return {'methodology_version':'fundamentals-1.0','computed_at':now(),'metrics':metrics,'coverage':coverage}
