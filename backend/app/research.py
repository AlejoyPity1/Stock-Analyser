import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from uuid import uuid4
import httpx
from pydantic import BaseModel, ConfigDict, Field
from .config import settings
from .analytics import advanced_analytics
from .horizon import HorizonCode, investment_horizon
from .catalysts import latest_catalysts
from .providers import sec, market, ProviderError
from .store import get, put, now, records
from .synthesis import SYSTEM, Claim, Conflict, Synthesis, format_synthesis, quotes_match
from .local_ai import synthesize_local

class ResearchRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    symbol: str = Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    mode: Literal['quick','deep']='quick'
    horizon: HorizonCode='3-6m'
    use_ai: bool=False
    budget_usd: float = Field(default=.1,gt=0,le=5)

_tasks={}; _slots=asyncio.Semaphore(2)

def canonical(url):
    p=urlparse(url)
    return urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/'),'',urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith(('utm_','fbclid'))]),''))

def deduplicate(items):
    seen=set(); out=[]
    for item in items:
        key=canonical(item['url'])
        if key not in seen: seen.add(key); out.append(item)
    return out


def progress(id,**fields):
    job=get(id)
    if not job or job['status']=='cancelled': raise asyncio.CancelledError
    job.update(fields,updated_at=now()); put(id,'research',job['symbol'],job)
    return job

async def synthesize(sources,request,horizon_context=None,on_progress=None):
    if settings.ai_provider == 'local':
        return await synthesize_local(sources,request,horizon_context,on_progress)
    if settings.ai_provider != 'openai':
        raise ProviderError('AI is disabled. Select AI_PROVIDER=local to use LM Studio. Paid AI remains blocked.','paid_ai_disabled')
    if not settings.paid_ai_enabled: raise ProviderError('Paid AI is disabled. No request was made.','paid_ai_disabled')
    if not settings.research_api_key: raise ProviderError('Falta RESEARCH_API_KEY','missing_credentials')
    ip=settings.ai_input_usd_per_million; op=settings.ai_output_usd_per_million
    if ip is None or op is None or ip<0 or op<0:
        raise ProviderError('Configura precios verificados de entrada/salida del modelo para aplicar el presupuesto.','missing_pricing')
    remaining=40000; prepared=[]
    for source in sources:
        text=source.get('text') or source.get('summary','')
        if source.get('read_status') not in ('read','abstract_only') or not text or remaining<=0:continue
        excerpt=text[:remaining];remaining-=len(excerpt)
        prepared.append({'id':source['id'],'title':source['title'],'content':excerpt,'read_status':source['read_status']})
    content=json.dumps({'symbol':request.symbol,'investment_horizon':horizon_context or investment_horizon(request.horizon),'sources':prepared},ensure_ascii=False)
    system=SYSTEM
    # Conservative UTF-8 byte upper bound plus schema overhead. One API call, no agent loop or paid tools.
    upper_input=len(content.encode())+len(system.encode())+16000
    upper_cost=(upper_input*ip+settings.research_max_output_tokens*op)/1e6
    budget=min(request.budget_usd,settings.research_max_usd)
    if upper_cost>budget: raise ProviderError(f'Coste máximo conservador {upper_cost:.4f} USD supera presupuesto {budget:.4f} USD.','budget_exceeded')
    payload={'model':settings.research_model,'input':[{'role':'system','content':system},{'role':'user','content':content}],'max_output_tokens':settings.research_max_output_tokens,'store':False,'text':{'format':{'type':'json_schema','name':'research','strict':True,'schema':Synthesis.model_json_schema()}}}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response=await client.post('https://api.openai.com/v1/responses',json=payload,headers={'Authorization':f'Bearer {settings.research_api_key}'})
            if response.status_code>=300: raise ProviderError(f'OpenAI HTTP {response.status_code}: comprueba disponibilidad del modelo, cuota y acceso. No se sustituye el modelo silenciosamente.','ai_error')
            d=response.json()
    except httpx.HTTPError: raise ProviderError('No se pudo completar la solicitud OpenAI','ai_error') from None
    usage=d.get('usage',{}); cost=(usage.get('input_tokens',0)*ip+usage.get('output_tokens',0)*op)/1e6
    billing={'model':settings.research_model,'usage':usage,'estimated_cost_usd':cost,'authorized_budget_usd':budget,'preflight_upper_bound_usd':upper_cost,'price_source':'Tarifas configuradas por el usuario; validar con la cuenta.'}
    try:
        text=''.join(c.get('text','') for o in d.get('output',[]) for c in o.get('content',[]) if c.get('type')=='output_text')
        if d.get('status')!='completed': return {'status':'rejected','reason':'Respuesta incompleta; no se publica síntesis','billing':billing}
        parsed=Synthesis.model_validate_json(text)
        evidence={source['id']:[source['content']] for source in prepared}
        if not quotes_match(parsed,evidence):
            return {'status':'rejected','reason':'Quotation or contradiction evidence was not found in the supplied excerpts.','billing':billing}
        return {'status':'generated_quote_verified','provider':'openai','model':settings.research_model,'data':format_synthesis(parsed),'billing':billing,'limitations':['Literal quotes were matched; interpretation requires review.','The synthesis does not modify valuations and does not verify the full original article when only an abstract is available.']}
    except (ValueError,KeyError,TypeError):
        return {'status':'rejected','reason':'Salida estructurada no válida; síntesis descartada.','billing':billing}

async def run(id,request):
    try:
        async with _slots:
            job=progress(id,status='running',stage='Resolviendo empresa y recuperando SEC')
            if not job.get('investment_horizon'):
                job=progress(id,investment_horizon=investment_horizon(request.horizon,job.get('created_at')))
            company=await sec.company(request.symbol)
            market_snapshot=None
            try: market_snapshot=await market.quote(request.symbol)
            except ProviderError: pass
            progress(id,financial_snapshot=company,market_snapshot=market_snapshot,analytics=advanced_analytics(company,market_snapshot),relative_ids=[r['id'] for r in records('relative',request.symbol)],valuation_ids=[r['id'] for r in records('valuation',request.symbol)],scenario_ids=[r['id'] for r in records('scenario',request.symbol)],price_scenario_ids=[r['id'] for r in records('price_scenario',request.symbol)],catalyst_ids=[event['id'] for event in latest_catalysts(request.symbol)])
            progress(id,company={'symbol':company['symbol'],'name':company['name'],'currency':company['currency']},stage='Buscando publicaciones y documentos oficiales')
            errors=[]; news=[]
            windows=[30] if request.mode=='quick' else [30,90,365]
            for days in windows:
                try: news.extend(await market.news(request.symbol,days))
                except ProviderError as e: errors.append({'provider':'Finnhub','code':e.code,'message':e.message}); break
            candidates=company['filings']+news
            unique=deduplicate(candidates)
            limit=min(settings.research_max_articles,10 if request.mode=='quick' else 50)
            # Preserve source diversity; do not let news displace official filings or vice versa.
            official=[s for s in unique if s['publisher']=='SEC EDGAR']; media=[s for s in unique if s['publisher']!='SEC EDGAR']
            sources=official[:min(5,limit)]
            sources+=media[:max(0,limit-len(sources))]
            sources+=official[5:5+max(0,limit-len(sources))]
            sources=deduplicate(sources)[:limit]
            progress(id,stage='Leyendo documentos accesibles',sources=sources,errors=errors)
            read_limit=2 if request.mode=='quick' else 6
            for s in [s for s in sources if s['publisher']=='SEC EDGAR'][:read_limit]:
                try: s.update(await sec.read_document(s['url']))
                except ProviderError as e: s.update(read_status='inaccessible',error=e.message)
                progress(id,sources=sources,stage=f'Lectura: {sum(x["read_status"]=="read" for x in sources)} documentos')
            for s in sources:
                s['financial_impact']={'status':'requires_review','model_changed':False,'reason':'No se cuantifica impacto sin evidencia de importe, calendario, márgenes y doble contabilización.'}
            stats={'found':len(candidates),'unique':len(unique),'selected':len(sources),'relevance_confirmed':None,'read_documents':sum(s['read_status']=='read' for s in sources),'full_text':sum(s.get('full_text',False) for s in sources),'abstract_only':sum(s['read_status']=='abstract_only' for s in sources),'inaccessible':sum(s['read_status']=='inaccessible' for s in sources),'used_for_synthesis':0}
            ai={'status':'not_requested'}
            if request.use_ai:
                progress(id,stage='Síntesis de evidencias con IA',sources=sources,stats=stats)
                try:
                    ai=await synthesize(sources,request,job['investment_horizon'],lambda message:progress(id,stage=message))
                    if ai['status']=='generated_quote_verified':
                        stats['used_for_synthesis']=len(ai['data']['used_source_ids'])
                except ProviderError as e: ai={'status':'unavailable','provider':settings.ai_provider,'model':settings.local_ai_model if settings.ai_provider=='local' else settings.research_model,'code':e.code,'reason':e.message}
            readable=stats['read_documents']+stats['abstract_only']
            progress(id,status='completed' if readable else 'partial',stage='Recopilación terminada',sources=sources,stats=stats,ai=ai,errors=errors,report={'summary':f'{len(sources)} fuentes seleccionadas; {stats["read_documents"]} documentos consultados y {stats["abstract_only"]} extractos. No se atribuye lectura al texto inaccesible.','limitations':['Investigación limitada a SEC reciente y cobertura de Finnhub; no búsqueda web exhaustiva ni cobertura garantizada de competidores/filiales.','Documentos extensos se truncan a 120.000 caracteres. La relevancia económica y contradicciones requieren revisión.','Sin IA configurada se entrega un expediente de evidencias, no un informe de analista generado.','No hay cambios automáticos de valoración ni probabilidades inventadas.']})
    except asyncio.CancelledError:
        job=get(id)
        if job and job['status']!='cancelled':
            job.update(status='interrupted',stage='Proceso interrumpido'); put(id,'research',job['symbol'],job)
        raise
    except ProviderError as e:
        progress(id,status='failed',stage='No se pudo completar',error=e.message,error_code=e.code)
    except Exception:
        progress(id,status='failed',stage='Error de procesamiento',error='Fallo interno. Consulta los registros del servidor; no se publicaron resultados inventados.')
    finally: _tasks.pop(id,None)


def enqueue(request):
    if len(_tasks)>=8: raise ProviderError('Cola completa; espera o cancela un trabajo.','queue_full')
    for id in list(_tasks):
        job=get(id)
        if job and job['symbol']==request.symbol and job['request']==request.model_dump(): return job
    id=str(uuid4()); created=now()
    job={'id':id,'symbol':request.symbol,'status':'queued','stage':'En cola','created_at':created,'updated_at':created,'request':request.model_dump(),'investment_horizon':investment_horizon(request.horizon,created),'sources':[]}
    put(id,'research',request.symbol,job); _tasks[id]=asyncio.create_task(run(id,request))
    return job

def cancel(id):
    job=get(id)
    if not job: return None
    if job['status'] not in ('queued','running'): return job
    job.update(status='cancelled',stage='Cancelado por el usuario',updated_at=now()); put(id,'research',job['symbol'],job)
    if task:=_tasks.get(id): task.cancel()
    return job
