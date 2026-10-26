"""Read-only provider validation, no AI calls. Controlled tests are separate.
Run: PYTHONPATH=backend .venv/bin/python scripts/verify_live.py
Exit 1 if required SEC fundamentals or document retrieval remain blocked.
"""
import asyncio
import json
from datetime import datetime,timezone
from bs4 import BeautifulSoup
from app.providers import sec,market,fetch,ProviderError
from app.store import initialize

async def crosscheck(company):
    fact=company['statements'][0]['values']['revenue']
    filing=next((s for s in company['filings'] if s['id']==fact['accession']),None)
    if not filing:return {'status':'not_checked','reason':'Annual filing outside recent list'}
    html=await fetch(filing['url'],text=True,ttl=86400)
    soup=BeautifulSoup(html,'html.parser')
    nodes=soup.find_all(lambda t:t.name.lower().endswith('nonfraction') and t.get('name')==fact['tag'])
    contexts={t.get('id'):t for t in soup.find_all(lambda t:t.name.lower().endswith(':context'))}
    matched=[]
    for node in nodes:
        try:
            number=float(node.get_text('',strip=True).replace(',','').replace('−','-'))*10**int(node.get('scale','0'))
            if node.get('sign')=='-':number=-number
        except (ValueError,TypeError):continue
        context=contexts.get(node.get('contextref'))
        if context is None:continue
        end=context.find(lambda t:t.name.lower().endswith('enddate'))
        start=context.find(lambda t:t.name.lower().endswith('startdate'))
        # Do not match an unrelated segment or comparative period by value alone.
        dimension=context.find(lambda t:t.name.lower().endswith(('explicitmember','typedmember')))
        if end and start and not dimension and end.get_text(strip=True)==fact['period_end'] and start.get_text(strip=True)==fact['period_start'] and abs(number-fact['value'])<.5:
            matched.append(node.get('contextref'))
    return {'status':'matched_inline_fact' if matched else 'not_matched','metric':'revenue','value':fact['value'],'currency':fact['currency'],'period_end':fact['period_end'],'tag':fact['tag'],'accession':fact['accession'],'source':filing['url'],'contexts':sorted(set(matched))}

async def main():
    initialize();blocked=False;results=[]
    for symbol in ['AAPL','GPRK','ASML']:
        result={'symbol':symbol};company=None
        try:
            company=await sec.company(symbol)
            result['sec']={'status':'retrieved','name':company['name'],'taxonomy':company['taxonomy'],'currency':company['currency'],'annual_periods':len(company['statements']),'latest_period':company['statements'][0]['end'] if company['statements'] else None,'quarters':len(company.get('quarterly',[])),'ttm_end':company['ttm']['end'] if company.get('ttm') else None,'filings':len(company['filings']),'retrieved_at':company['retrieved_at']}
            if not company['statements']:result['sec']['status']='insufficient_data';blocked=True
            else:
                try:result['annual_revenue_crosscheck']=await crosscheck(company)
                except ProviderError as e:result['annual_revenue_crosscheck']={'status':'blocked','code':e.code,'reason':e.message}
            if company['filings']:
                try:
                    doc=await sec.read_document(company['filings'][0]['url'])
                    result['document']={'status':doc['read_status'],'full_text':doc['full_text'],'source':company['filings'][0]['url']}
                except ProviderError as e:result['document']={'status':'blocked','reason':e.message};blocked=True
        except ProviderError as e:result['sec']={'status':'blocked','code':e.code,'reason':e.message};blocked=True
        try:
            quote=await market.quote(symbol)
            result['quote']={'status':'retrieved','timestamp':quote['timestamp'],'currency':quote['currency'],'exchange':quote['exchange'],'source':quote['source'],'compatible_with_reporting_currency':quote['currency']==company['currency'] if company else None}
        except ProviderError as e:result['quote']={'status':'blocked','code':e.code,'reason':e.message}
        try:
            news=await market.news(symbol,30)
            result['news']={'status':'retrieved','count':len(news),'full_articles_claimed':False}
        except ProviderError as e:result['news']={'status':'blocked','code':e.code,'reason':e.message}
        results.append(result)
    print(json.dumps({'verified_at':datetime.now(timezone.utc).isoformat(),'ai_calls':0,'results':results},indent=2,ensure_ascii=False))
    return 1 if blocked else 0

if __name__=='__main__':raise SystemExit(asyncio.run(main()))
