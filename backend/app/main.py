import asyncio
import hmac
import json
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from statistics import median
from typing import Literal
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from .config import settings
from .store import initialize, now, put, get, records, delete
from .providers import sec, market, historical, ProviderError
from .finance import DCFInput, dcf, ratios, sensitivity, reverse_dcf, quant, benchmark_metrics
from .analytics import advanced_analytics
from .comparables import ComparableRequest, relative_analysis
from .near_term import PriceScenarioRequest, calculate_price_scenarios
from .catalysts import CatalystRequest, save_catalyst, latest_catalysts, event_position
from .horizon import investment_horizon
from .reporting import build_report, render_pdf
from .research import ResearchRequest, enqueue, cancel, _tasks
from .local_ai import check_local_model

@asynccontextmanager
async def lifespan(app):
    if settings.app_environment=='production' and not settings.app_token:
        raise RuntimeError('APP_TOKEN es obligatorio en producción')
    initialize(recover_jobs=True)
    yield
    tasks=list(_tasks.values())
    for task in tasks: task.cancel()
    await asyncio.gather(*tasks,return_exceptions=True)

app=FastAPI(title='Stock Intelligence AI',version='0.2.0',lifespan=lifespan)
_hits=defaultdict(deque)

@app.middleware('http')
async def protection(request:Request,call_next):
    if request.url.path!='/health':
        if settings.app_token and not hmac.compare_digest(request.headers.get('authorization',''),f'Bearer {settings.app_token}'):
            return JSONResponse({'detail':'No autorizado'},status_code=401)
        length=request.headers.get('content-length','0')
        if not length.isdigit(): return JSONResponse({'detail':'Longitud no válida'},status_code=400)
        if int(length)>100000:
            return JSONResponse({'detail':'Solicitud demasiado grande'},status_code=413)
        key=request.client.host if request.client else 'local'; t=time.monotonic(); hits=_hits[key]
        while hits and hits[0]<t-60: hits.popleft()
        if len(hits)>=120: return JSONResponse({'detail':'Límite de 120 solicitudes/minuto'},status_code=429,headers={'Retry-After':'60'})
        hits.append(t)
        if len(_hits)>10000: _hits.clear()
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(ProviderError)
async def provider_error(request,exc):
    return JSONResponse(status_code=503,content={'detail':exc.message,'code':exc.code})

@app.get('/health')
def health(): return {'status':'ok','version':'0.2.0'}

@app.get('/settings')
def config():
    return {'ai_provider':settings.ai_provider,'providers':{'sec':{'configured':'@' in settings.sec_user_agent and 'YOUR_EMAIL' not in settings.sec_user_agent,'coverage':'Emisores SEC; anuales, trimestres y TTM cuando existen cuatro períodos compatibles. No todo el mercado.'},'finnhub':{'configured':bool(settings.finnhub_api_key),'coverage':'Cotización y noticias según licencia/cuota. No se garantiza tiempo real.'},'alphavantage':{'configured':bool(settings.alphavantage_api_key),'coverage':'Histórico diario ajustado; puede requerir un plan de pago.'},'local':{'enabled':settings.ai_provider=='local','configured':settings.ai_provider=='local','model':settings.local_ai_model,'base_url':settings.local_ai_base_url,'context_tokens':settings.local_ai_context_tokens,'availability_verified':False,'coverage':'English synthesis of bounded source excerpts with literal quote checks. Financial interpretation still requires review.'},'openai':{'enabled':settings.ai_provider=='openai' and settings.paid_ai_enabled,'deferred':not settings.paid_ai_enabled,'configured':bool(settings.research_api_key),'model':settings.research_model,'pricing_configured':settings.ai_input_usd_per_million is not None and settings.ai_output_usd_per_million is not None,'availability_verified':False}},'limits':{'cache_seconds':settings.cache_seconds,'max_articles':settings.research_max_articles,'max_budget_usd':settings.research_max_usd,'concurrent_jobs':2},'storage':'PostgreSQL' if settings.database_url.startswith('postgres') else 'SQLite','security':{'access_token_required':bool(settings.app_token),'environment':settings.app_environment},'limitations':['Proveedor conectado solo después de una solicitud exitosa; configured no significa verificado.','No hay alertas push, cobertura global ni modelos sectoriales certificados.','Uso personal local. Antes de exponer públicamente, añade TLS, autenticación de usuarios y control de acceso.']}

@app.post('/settings/local-ai/check')
async def local_ai_check():
    return await check_local_model()

@app.get('/search')
async def search(q:str=Query(min_length=1,max_length=100)):
    return await sec.search(q)

def valid_symbol(symbol):
    import re
    symbol=symbol.upper()
    if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',symbol): raise HTTPException(422,'Ticker no válido')
    return symbol

async def snapshot(symbol):
    symbol=valid_symbol(symbol); company=await sec.company(symbol)
    quote=None; warnings=[]
    try: quote=await market.quote(symbol)
    except ProviderError as e: warnings.append({'code':e.code,'message':e.message})
    if company.get('multiple_share_classes'):warnings.append({'code':'share_class_mapping','message':'Varias clases cotizadas: no se atribuyen automáticamente las acciones medias a este ticker. Múltiplos desactivados.'})
    latest=company['statements'][0] if company['statements'] else None
    currency_compatible=quote and quote['currency']==company['currency']
    compatible=currency_compatible and not company.get('multiple_share_classes',False)
    if quote and not currency_compatible: warnings.append({'code':'currency_mismatch','message':'Cotización y estados en distinta divisa; múltiplos no calculados.'})
    from datetime import datetime,timezone,date
    clock=datetime.now(timezone.utc)
    quote_recent=bool(quote and -300<=(clock-datetime.fromisoformat(quote['timestamp'])).total_seconds()<=7*86400)
    annual_recent=bool(latest and 0<=(clock.date()-date.fromisoformat(latest['end'])).days<=550)
    if quote and not quote_recent:warnings.append({'code':'quote_too_old','message':'Cotización de más de siete días: múltiplos y yields no calculados.'})
    if latest and not annual_recent:warnings.append({'code':'annual_too_old','message':'El último ejercicio tiene más de 550 días: múltiplos anuales no calculados.'})
    metrics=ratios(latest['values'],quote['price'] if compatible and quote_recent and annual_recent else None) if latest else {}
    if quote: warnings.append({'code':'period_basis','message':'Múltiplos: precio más reciente / último ejercicio anual disponible; no TTM. Capitalización usa acciones diluidas medias del ejercicio, no acciones actuales.'})
    trailing=company.get('ttm')
    ttm_recent=bool(trailing and 0<=(clock.date()-date.fromisoformat(trailing['end'])).days<=200)
    ttm_metrics=ratios(trailing['values'],quote['price'] if compatible and quote_recent and ttm_recent else None) if trailing else None
    result={'company':company,'quote':quote,'metrics':metrics,'ttm_metrics':ttm_metrics,'warnings':warnings,'created_at':now()}
    result['analytics']=advanced_analytics(company,quote)
    put(f'snapshot:{symbol}','snapshot',symbol,result)
    return result

@app.get('/companies/{symbol}')
async def company(symbol:str): return await snapshot(symbol)

@app.get('/companies/{symbol}/history')
async def history(symbol:str,adjusted:bool=True,benchmark:str|None=Query(default=None,max_length=15)):
    data=await historical.history(valid_symbol(symbol),adjusted=adjusted)
    key='adjusted_close' if adjusted else 'close'
    data['metrics']=quant([p[key] for p in data['points']],adjusted=adjusted)
    if benchmark:
        name=valid_symbol(benchmark);other=await historical.history(name,adjusted=adjusted)
        if not data['currency'] or data['currency']!=other['currency']:raise HTTPException(422,'Benchmark y acción requieren una divisa de negociación verificada común')
        try:data['benchmark']={'symbol':name,'source':other['source'],**benchmark_metrics([{'date':p['date'],'value':p[key]} for p in data['points']],[{'date':p['date'],'value':p[key]} for p in other['points']])}
        except ValueError as e:raise HTTPException(422,str(e))
    return data

class ValuationRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    symbol:str=Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    inputs:DCFInput
    parent_id:str|None=Field(default=None,max_length=100)
    source_id:str|None=Field(default=None,max_length=100)
    research_id:str|None=Field(default=None,max_length=100)
    justification:str=Field(min_length=10,max_length=4000)

@app.post('/valuations')
def valuation(request:ValuationRequest):
    if request.research_id and not request.source_id: raise HTTPException(422,'Asocia una fuente para vincular una investigación')
    parent=get(request.parent_id) if request.parent_id else None
    if request.parent_id and (not parent or parent.get('symbol')!=request.symbol or 'inputs' not in parent): raise HTTPException(422,'Modelo anterior no encontrado para esta empresa')
    source=None
    if request.source_id:
        research=get(request.research_id) if request.research_id else None
        source=next((s for s in research.get('sources',[]) if s['id']==request.source_id),None) if research and research.get('symbol')==request.symbol else None
        if not source or source.get('read_status') not in ('read','abstract_only'): raise HTTPException(422,'Fuente no leída o ajena a esta empresa')
    if parent and (parent['inputs']['currency']!=request.inputs.currency or parent['inputs']['basis']!=request.inputs.basis): raise HTTPException(422,'Las versiones deben conservar divisa y base nominal')
    result=dcf(request.inputs); id=str(uuid4())
    changes=[{'field':k,'old':parent['inputs'].get(k),'new':v} for k,v in request.inputs.model_dump().items() if parent and parent['inputs'].get(k)!=v]
    result.update(id=id,symbol=request.symbol,created_at=now(),parent_id=request.parent_id,justification=request.justification,source=source,research_id=request.research_id,baseline_snapshot=get('snapshot:'+request.symbol),changes=changes,value_effect=result['fair_value']-parent['fair_value'] if parent else None,sensitivity=sensitivity(request.inputs),reverse_dcf=reverse_dcf(request.inputs))
    put(id,'valuation',request.symbol,result); return result

@app.post('/valuation/preview')
def preview(inputs:DCFInput): return {**dcf(inputs),'sensitivity':sensitivity(inputs),'reverse_dcf':reverse_dcf(inputs)}

class ScenarioRequest(BaseModel):
    bear:DCFInput
    base:DCFInput
    bull:DCFInput

@app.post('/scenarios')
def scenarios(request:ScenarioRequest):
    inputs=[request.bear,request.base,request.bull]
    if len({x.currency for x in inputs})!=1 or len({x.years for x in inputs})!=1: raise HTTPException(422,'Escenarios deben compartir divisa y horizonte')
    return {k:dcf(getattr(request,k)) for k in ['bear','base','bull']}

class SavedScenarios(ScenarioRequest):
    symbol:str=Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    research_id:str|None=Field(default=None,max_length=100)
    justification:str=Field(min_length=10,max_length=4000)

@app.post('/scenario-sets')
def save_scenarios(request:SavedScenarios):
    if request.research_id:
        research=get(request.research_id)
        if not research or research.get('symbol')!=request.symbol:raise HTTPException(422,'Investigación no encontrada para esta empresa')
    for field in ('revenue','net_debt','shares','price','price_currency','basis'):
        if len({getattr(m,field) for m in (request.bear,request.base,request.bull)})!=1:raise HTTPException(422,'Los escenarios guardados deben compartir los datos de partida: '+field)
    result=scenarios(request);id=str(uuid4())
    record={'id':id,'symbol':request.symbol,'created_at':now(),'research_id':request.research_id,'justification':request.justification,'results':result,'inputs':{k:getattr(request,k).model_dump() for k in ['bear','base','bull']}}
    put(id,'scenario',request.symbol,record);return record

@app.get('/companies/{symbol}/earnings-calendar')
async def earnings_calendar(symbol:str):
    window=investment_horizon('6m')
    return await market.earnings_calendar(valid_symbol(symbol),window['as_of'],window['window_end_date'])

@app.get('/catalysts')
def catalysts(symbol:str,horizon:Literal['3-6m','3m','6m']='3-6m'):
    symbol=valid_symbol(symbol);window=investment_horizon(horizon)
    return {'symbol':symbol,'investment_horizon':window,'items':[{**value,'position':event_position(value,window)} for value in latest_catalysts(symbol)],'coverage':'Últimas versiones dentro de los 1.000 registros de catalizadores más recientes de esta empresa.'}

@app.post('/catalysts')
def create_catalyst(request:CatalystRequest):
    try:return save_catalyst(request)
    except ValueError as error:raise HTTPException(422,str(error))

async def price_model(request):
    if request.research_id:
        job=get(request.research_id)
        if not job or job.get('symbol')!=request.symbol:raise HTTPException(422,'Investigación no encontrada para esta empresa')
        if job.get('investment_horizon',{}).get('code',request.horizon)!=request.horizon:raise HTTPException(422,'El horizonte debe coincidir con la investigación vinculada')
    events=[]
    for id in request.catalyst_ids:
        event=get(id)
        if not event or event.get('record_type')!='catalyst' or event['symbol']!=request.symbol:raise HTTPException(422,'Catalizador no encontrado para esta empresa')
        events.append(event)
    quote=await market.quote(request.symbol)
    try:return calculate_price_scenarios(request,quote,events)
    except ValueError as error:raise HTTPException(422,str(error))

@app.post('/price-scenarios/preview')
async def preview_price_scenarios(request:PriceScenarioRequest):return await price_model(request)

@app.post('/price-scenarios')
async def save_price_scenarios(request:PriceScenarioRequest):
    value=await price_model(request);value['id']=str(uuid4())
    value['research_id']=request.research_id
    put(value['id'],'price_scenario',request.symbol,value);return value

@app.get('/records')
def saved(kind:Literal['valuation','research','snapshot','scenario','relative','price_scenario','catalyst']='research',symbol:str|None=None): return records(kind,valid_symbol(symbol) if symbol else None)

@app.get('/records/{id}')
def record(id:str):
    row=get(id)
    if not row: raise HTTPException(404,'Registro no encontrado')
    return row

@app.post('/research',status_code=202)
async def research(request:ResearchRequest): return enqueue(request)

@app.post('/research/{id}/cancel')
async def cancel_job(id:str):
    result=cancel(id)
    if not result: raise HTTPException(404,'Investigación no encontrada')
    return result

class WatchRequest(BaseModel):
    symbol:str=Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    note:str=Field(default='',max_length=2000)

@app.get('/watchlist')
def watchlist(): return records('watchlist')

@app.post('/watchlist')
def add_watch(request:WatchRequest):
    put('watch:'+request.symbol,'watchlist',request.symbol,request.model_dump()); return request

@app.delete('/watchlist/{symbol}')
def remove_watch(symbol:str): delete('watch:'+valid_symbol(symbol)); return {'removed':True}

@app.get('/screen')
def screen(min_margin:float|None=None,max_pe:float|None=None,min_fcf_yield:float|None=None,
           min_growth:float|None=None,max_debt_ebitda:float|None=None,
           min_cap:float|None=None,max_cap:float|None=None,currency:str|None=Query(default=None,pattern=r'^[A-Z]{3}$'),
           industry:str|None=Query(default=None,max_length=100),country:str|None=Query(default=None,max_length=100),
           sort:Literal['symbol','pe','operating_margin','fcf_yield','debt_ebitda','revenue_growth','market_cap']='symbol',order:Literal['asc','desc']='asc'):
    if (min_cap is not None or max_cap is not None) and not currency:raise HTTPException(422,'Especifica divisa para filtrar capitalizaciones sin mezclar monedas')
    rows=[];all_rows=records('snapshot')
    for row in all_rows:
        d=row['data'];company=d['company'];m=dict(d['metrics']);annual=company.get('statements',[])
        growth=None
        if len(annual)>=2:
            from datetime import date
            gap=(date.fromisoformat(annual[0]['end'])-date.fromisoformat(annual[1]['end'])).days
            a=annual[0]['values'].get('revenue',{}).get('value');b=annual[1]['values'].get('revenue',{}).get('value')
            if a is not None and b is not None and b>0 and 300<=gap<=380:growth=a/b-1
        m['revenue_growth']=growth
        if currency and company.get('currency')!=currency:continue
        if industry and industry.casefold() not in (company.get('industry') or '').casefold():continue
        if country and country.casefold()!=(company.get('country') or '').casefold():continue
        conditions=[('operating_margin',min_margin,True),('pe',max_pe,False),('fcf_yield',min_fcf_yield,True),('revenue_growth',min_growth,True),('debt_ebitda',max_debt_ebitda,False),('market_cap',min_cap,True),('market_cap',max_cap,False)]
        if any(limit is not None and (m.get(k) is None or (m[k]<limit if minimum else m[k]>limit)) for k,limit,minimum in conditions):continue
        rows.append({'symbol':row['symbol'],'name':company['name'],'currency':company.get('currency'),'industry':company.get('industry'),'country':company.get('country'),'metrics':m,'period_end':annual[0]['end'] if annual else None,'retrieved_at':d['created_at']})
    if sort=='symbol':rows.sort(key=lambda r:r['symbol'],reverse=order=='desc')
    else:
        known=[r for r in rows if r['metrics'].get(sort) is not None];missing=[r for r in rows if r['metrics'].get(sort) is None]
        rows=sorted(known,key=lambda r:r['metrics'][sort],reverse=order=='desc')+missing
    return {'universe':'Empresas previamente consultadas en esta instancia (hasta 100 snapshots recientes); no todo el mercado.','universe_count':len(all_rows),'sort':sort,'order':order,'rows':rows}

@app.get('/compare')
async def compare(symbols:str=Query(max_length=100)):
    names=list(dict.fromkeys(valid_symbol(s.strip()) for s in symbols.split(',')))
    if not 2<=len(names)<=5: raise HTTPException(422,'Selecciona de 2 a 5 empresas')
    data=await asyncio.gather(*(snapshot(s) for s in names),return_exceptions=True)
    rows=[]
    for symbol,row in zip(names,data):
        if isinstance(row,Exception): rows.append({'symbol':symbol,'error':row.message if isinstance(row,ProviderError) else 'Error de proveedor'})
        else: rows.append({'symbol':symbol,'name':row['company']['name'],'currency':row['company']['currency'],'industry':row['company'].get('industry'),'metrics':row['metrics'],'period':row['company']['statements'][0]['end'] if row['company']['statements'] else None,'quote_currency':row['quote']['currency'] if row['quote'] else None,'warnings':row['warnings']})
    return {'rows':rows,'limitations':['Comparabilidad económica requiere revisión de industria, divisa, ejercicio y crecimiento. No se infiere por ticker.','No se calcula mediana ni valor implícito sin un grupo comparable aprobado y bases compatibles.']}

class RelativeRequest(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    metric:Literal['pe','ev_ebitda','ev_revenue','p_fcf']
    peer_multiples:list[float]=Field(min_length=2,max_length=30)
    target_fundamental:float=Field(gt=0)
    shares:float=Field(gt=0)
    net_debt:float=0
    comparability_rationale:str=Field(min_length=20,max_length=3000)

@app.post('/relative')
def relative(request:RelativeRequest):
    import math
    if any(not math.isfinite(x) or x<=0 for x in request.peer_multiples): raise HTTPException(422,'Múltiplos positivos y finitos requeridos')
    multiple=median(request.peer_multiples); value=multiple*request.target_fundamental
    equity=value-request.net_debt if request.metric.startswith('ev_') else value
    return {'median':multiple,'range':[min(request.peer_multiples),max(request.peer_multiples)],'implied_equity':equity,'implied_per_share':equity/request.shares,'inputs':request.model_dump(),'methodology':'Inputs manuales en una misma divisa y período; EV se convierte a equity restando deuda neta.'}


async def prepare_relative(request):
    symbols=[request.target]+request.peers
    responses=await asyncio.gather(*(snapshot(s) for s in symbols),return_exceptions=True)
    bundle={symbol:({'symbol':symbol,'error':r.message if isinstance(r,ProviderError) else 'Error de proveedor'} if isinstance(r,Exception) else r) for symbol,r in zip(symbols,responses)}
    if request.research_id:
        research=get(request.research_id)
        if not research or research.get('symbol')!=request.target:raise HTTPException(422,'Investigación no encontrada para esta empresa')
    return relative_analysis(request,bundle)

@app.post('/relative-analysis')
async def relative_preview(request:ComparableRequest):return await prepare_relative(request)

@app.post('/relative-valuations')
async def relative_save(request:ComparableRequest):
    result=await prepare_relative(request)
    if result['status']!='available':raise HTTPException(422,{'message':'No hay comparables suficientes o el objetivo no es valorable con esta base','target':result['target']['reasons'],'peers':[{k:r[k] for k in ['symbol','reasons']} for r in result['peers']]})
    result['id']=str(uuid4());result['research_id']=request.research_id
    put(result['id'],'relative',request.target,result)
    return result

@app.get('/reports/{id}')
def report(id:str):
    result=build_report(id)
    if not result:raise HTTPException(404,'Informe no encontrado')
    return result

@app.get('/reports/{id}/pdf')
def report_pdf(id:str):
    result=build_report(id)
    if not result:raise HTTPException(404,'Informe no encontrado')
    payload=render_pdf(result)
    symbol=valid_symbol(result['record']['symbol'])
    return Response(payload,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="informe-{symbol}.pdf"'})
