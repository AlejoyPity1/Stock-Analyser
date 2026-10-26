"""Provider boundary: no fabricated fallback data and no arbitrary URL fetching."""
import asyncio
import hashlib
import json
import math
import time
from datetime import date, datetime, timezone, timedelta
from typing import Protocol
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from .config import settings
from .store import Cache, Session, now

class ProviderError(Exception):
    def __init__(self,message,code='provider_unavailable'):
        self.message=message; self.code=code
        super().__init__(message)

class MarketProvider(Protocol):
    async def quote(self,symbol:str)->dict: ...
    async def news(self,symbol:str,days:int)->list[dict]: ...

# A single limiter per host enforces spacing across concurrent jobs.
_locks: dict[str,asyncio.Lock]={}
_last: dict[str,float]={}
_HOSTS={'www.sec.gov','data.sec.gov','finnhub.io','www.alphavantage.co','static2.finnhub.io'}

async def fetch(url,params=None,text=False,ttl=None):
    host=urlparse(url).hostname
    if urlparse(url).scheme!='https' or host not in _HOSTS:
        raise ProviderError('Destino no autorizado','unsafe_url')
    headers={}
    if host and host.endswith('sec.gov'):
        ua=settings.sec_user_agent
        if '@' not in ua or 'YOUR_EMAIL' in ua:
            raise ProviderError('Configura SEC_USER_AGENT con nombre de aplicación y correo de contacto válido.','missing_configuration')
        headers['User-Agent']=ua
    # Hash credentials in cache keys; never persist query strings containing keys.
    key=hashlib.sha256((url+json.dumps(params or {},sort_keys=True)).encode()).hexdigest()
    with Session() as s:
        row=s.get(Cache,key)
        if row and row.expires>time.time(): return json.loads(row.payload)
    lock=_locks.setdefault(host,asyncio.Lock())
    for attempt in range(3):
        async with lock:
            spacing=1.1 if host.endswith('sec.gov') else 1.05
            await asyncio.sleep(max(0,spacing-(time.monotonic()-_last.get(host,0))))
            _last[host]=time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=25,follow_redirects=False) as client:
                    request_url=url
                    request_params=params
                    # The symbol directory redirects to Finnhub's own signed CDN.
                    # Allow only that endpoint/host/path; never forward credentials to arbitrary redirects.
                    response=None
                    for hop in range(2):
                        request=client.build_request('GET',request_url,params=request_params,headers=headers)
                        response=await client.send(request,stream=True)
                        if response.status_code not in (301,302,307,308): break
                        target=urljoin(request_url,response.headers.get('location',''))
                        dest=urlparse(target)
                        await response.aclose()
                        if (hop or host!='finnhub.io' or urlparse(url).path!='/api/v1/stock/symbol'
                            or dest.scheme!='https' or dest.hostname!='static2.finnhub.io'
                            or not dest.path.startswith('/file/')):
                            raise ProviderError('Redirección del proveedor no autorizada','unsafe_redirect')
                        request_url=target;request_params=None
                    try:
                        if response.status_code in (429,500,502,503,504):
                            if attempt<2:
                                await asyncio.sleep(2**attempt); continue
                        if response.status_code>=300:
                            raise ProviderError(f'{host}: HTTP {response.status_code}. Revisa acceso, cuota y licencia.','http_error')
                        body=bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            limit=50_000_000 if host=='www.sec.gov' and urlparse(url).path.startswith('/Archives/') else 15_000_000
                            if len(body)>limit: raise ProviderError('Respuesta excede el límite de tamaño autorizado','response_too_large')
                        try: data=bytes(body).decode('utf-8',errors='replace') if text else json.loads(body)
                        except (ValueError,UnicodeError): raise ProviderError('Respuesta no válida del proveedor','invalid_response')
                    finally:
                        await response.aclose()
                with Session() as s:
                    row=s.get(Cache,key)
                    if row: row.payload=json.dumps(data); row.expires=time.time()+(settings.cache_seconds if ttl is None else ttl)
                    else: s.add(Cache(key=key,payload=json.dumps(data),expires=time.time()+(settings.cache_seconds if ttl is None else ttl)))
                    s.commit()
                return data
            except httpx.HTTPError:
                if attempt==2: raise ProviderError(f'No se pudo conectar a {host}; verifica la política de red y la configuración.','network_error') from None
                await asyncio.sleep(2**attempt)
    raise ProviderError('Cuota temporal agotada','rate_limit')

# Explicit aliases, all sourced from the selected issuer's XBRL taxonomy.
TAGS={
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','Revenues','SalesRevenueNet','Revenue'],
 'cost_revenue':['CostOfRevenue','CostOfGoodsAndServicesSold','CostOfGoodsSold','CostOfSales'],
 'gross_profit':['GrossProfit'], 'ebit':['OperatingIncomeLoss','ProfitLossFromOperatingActivities'],
 'net_income':['NetIncomeLoss','ProfitLoss'], 'eps':['EarningsPerShareDiluted','DilutedEarningsLossPerShare'],
 'shares':['WeightedAverageNumberOfDilutedSharesOutstanding','WeightedAverageNumberOfDilutedShares','AdjustedWeightedAverageShares'],
 'cash':['CashAndCashEquivalentsAtCarryingValue','CashAndCashEquivalents'],
 'assets':['Assets'], 'current_assets':['AssetsCurrent','CurrentAssets'],
 'liabilities':['Liabilities'], 'current_liabilities':['LiabilitiesCurrent','CurrentLiabilities'],
 'equity':['StockholdersEquity','EquityAttributableToOwnersOfParent','Equity'],
 'ocf':['NetCashProvidedByUsedInOperatingActivities','CashFlowsFromUsedInOperatingActivities'],
 'capex':['PaymentsToAcquirePropertyPlantAndEquipment','PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities'],
 'da':['DepreciationDepletionAndAmortization','DepreciationDepletionAndAmortizationPropertyPlantAndEquipment','DepreciationAmortizationAndAccretionNet'],
 'sbc':['ShareBasedCompensation','AdjustmentsForSharebasedPayments'], 'dividends':['PaymentsOfDividends','PaymentsOfDividendsCommonStock','DividendsPaidClassifiedAsFinancingActivities'],
 'buybacks':['PaymentsForRepurchaseOfCommonStock','PaymentsToAcquireOrRedeemEntitysShares'], 'interest':['InterestExpense','InterestAndDebtExpense'],
 'tax_expense':['IncomeTaxExpenseBenefit','IncomeTaxExpenseContinuingOperations'],
 'pretax_income':['IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest','IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments','ProfitLossBeforeTax'],
 'net_income_owners':['ProfitLossAttributableToOwnersOfParent'],
 'equity_total':['StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest','Equity'],
 'debt_total':['LongTermDebtAndFinanceLeaseObligationsIncludingCurrentPortion','LongTermDebtCurrentAndNoncurrent','Borrowings'],
 'debt_long':['LongTermDebtNoncurrent','LongTermDebt','LongtermBorrowings'],
 'debt_current':['LongTermDebtCurrent','ShorttermBorrowings'], 'commercial_paper':['CommercialPaper'],
}
INSTANT={'equity_total','cash','assets','current_assets','liabilities','current_liabilities','equity','debt_total','debt_long','debt_current','commercial_paper'}


def normalize_facts(raw,cik,asof=None):
    asof=asof or date.today().isoformat()
    # A foreign filer can contain a few US GAAP acquisition tags alongside IFRS.
    # Select the taxonomy with actual consolidated revenue coverage, not mere presence.
    available=raw.get('facts',{})
    taxonomy=max(('us-gaap','ifrs-full'),key=lambda tax: sum(len(entries) for tag in TAGS['revenue'] for entries in available.get(tax,{}).get(tag,{}).get('units',{}).values()))
    facts=raw.get('facts',{}).get(taxonomy,{})
    # Currency is inferred from revenue, never relabelled or silently converted.
    currency=None
    for tag in TAGS['revenue']:
        units=facts.get(tag,{}).get('units',{})
        found=[u for u in units if len(u)==3 and u.isalpha()]
        if len(found)==1: currency=found[0]; break
    if not currency: raise ProviderError('No se pudo determinar una divisa de ingresos única','insufficient_data')
    annual={}
    for metric,tags in TAGS.items():
        unit='shares' if metric=='shares' else f'{currency}/shares' if metric=='eps' else currency
        candidates=[]
        for priority,tag in enumerate(tags):
            for entry in facts.get(tag,{}).get('units',{}).get(unit,[]):
                if not isinstance(entry.get('val'),(int,float)) or not math.isfinite(entry['val']): continue
                if entry.get('filed','9999')>asof or entry.get('form') not in ('10-K','20-F','40-F','10-K/A','20-F/A'): continue
                if not entry.get('end') or entry['end']>asof: continue
                if metric not in INSTANT:
                    if not entry.get('start'): continue
                    days=(date.fromisoformat(entry['end'])-date.fromisoformat(entry['start'])).days
                    if not 300<=days<=380: continue
                candidates.append((entry,tag,priority))
        # Latest filing wins for restatements; first alias wins only on equal filing dates.
        for e,tag,priority in sorted(candidates,key=lambda v:(v[0].get('filed',''),-v[2])):
            end=e['end']; annual.setdefault(end,{})[metric]={
              'value':e['val'],'unit':unit,'currency':currency if unit!='shares' else None,
              'period_start':e.get('start'),'period_end':end,'filed':e.get('filed'),
              'retrieved_at':now(),'accession':e.get('accn'),'tag':f'{taxonomy}:{tag}',
              'source':f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{e.get("accn", "").replace("-", "")}/',
              'source_id':f'{e.get("accn")}:{tag}:{end}', 'quality':'reported'}
    # Keep annual income statement ends, not random interim balance snapshots.
    annual={end:v for end,v in annual.items() if 'revenue' in v}
    for end,v in annual.items():
        # Annual metrics must cover the same duration as consolidated revenue.
        # A 300-day flow and a 365-day flow are not comparable merely because they share an end date.
        start=v['revenue']['period_start']
        for key in list(v):
            if key not in INSTANT and v[key].get('period_start')!=start:del v[key]
        # Current maturities are part of long-term debt, never add total liabilities.
        components=['debt_long','debt_current','commercial_paper']
        if 'debt_total' in v:
            total=v['debt_total']['value']+v.get('commercial_paper',{}).get('value',0)
            v['debt']={**v['debt_total'],'value':total,'quality':'derived','formula':'Reported total debt + commercial paper (if separately reported)','components':[v[k] for k in ['debt_total','commercial_paper'] if k in v]}
        elif 'debt_long' in v and 'debt_current' in v:
            v['debt']={**v['debt_long'],'value':sum(v.get(k,{}).get('value',0) for k in components),'quality':'derived','formula':'Noncurrent long-term debt + current maturities + commercial paper (if separately reported)','components':[v[k] for k in components if k in v]}
        # Absence of a debt tag never means zero debt.
    from .periods import periods
    quarterly,trailing=periods(raw,taxonomy,currency,cik,TAGS,INSTANT,asof)
    # Apply the identical debt bridge to all balance dates, including TTM.
    for row in quarterly+([trailing] if trailing else []):
        values=row['values']
        if 'debt_total' in values:
            keys=['debt_total']+(['commercial_paper'] if 'commercial_paper' in values else [])
        elif 'debt_long' in values and 'debt_current' in values:
            keys=['debt_long','debt_current']+(['commercial_paper'] if 'commercial_paper' in values else [])
        else:continue
        values['debt']={**values[keys[0]],'value':sum(values[k]['value'] for k in keys),'quality':'derived','components':[values[k] for k in keys],'formula':' + '.join(keys)}
    return {'quarterly':quarterly,'ttm':trailing,'currency':currency,'taxonomy':taxonomy,'period_type':'annual','statements':[{'end':e,'values':v} for e,v in sorted(annual.items(),reverse=True)[:10]],'limitations':['Base anual por defecto; trimestres y TTM se muestran por separado cuando hay cobertura. Ratios de balance usan saldo de cierre, no saldo medio.','Cobertura XBRL consolidada: etiquetas sectoriales y emisores IFRS pueden quedar incompletos.','La deuda puede excluir arrendamientos u obligaciones no cubiertas por las etiquetas indicadas.']}

class SECProvider:
    async def search(self,query):
        data=await fetch('https://www.sec.gov/files/company_tickers_exchange.json',ttl=86400)
        fields=data['fields']; rows=[dict(zip(fields,row)) for row in data['data']]
        q=query.casefold().strip()
        rows=[r for r in rows if q==r['ticker'].casefold() or q in r['name'].casefold() or q in r['ticker'].casefold()]
        rows.sort(key=lambda r:(r['ticker'].casefold()!=q,r['name']))
        return [{'symbol':r['ticker'],'name':r['name'],'cik':str(r['cik']).zfill(10),'exchange':r['exchange']} for r in rows[:20]]

    async def company(self,symbol):
        matches=await self.search(symbol)
        exact=[r for r in matches if r['symbol']==symbol]
        if len(exact)!=1: raise ProviderError('Ticker no resuelto de forma única en SEC. Usa un ticker SEC exacto.','not_found')
        company=exact[0]; cik=company['cik']
        sub,raw=await asyncio.gather(fetch(f'https://data.sec.gov/submissions/CIK{cik}.json'),fetch(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'))
        company.update(sic=sub.get('sic'),industry=sub.get('sicDescription'),country=sub.get('addresses',{}).get('business',{}).get('countryDescription'),**normalize_facts(raw,cik))
        recent=sub.get('filings',{}).get('recent',{}); filings=[]
        for i,form in enumerate(recent.get('form',[])):
            if form not in ('10-K','10-Q','8-K','20-F','6-K','40-F'): continue
            acc=recent['accessionNumber'][i]
            filings.append({'id':acc,'title':f'{form} · {company["name"]}','form':form,'published_at':recent['filingDate'][i], 'event_date':recent.get('reportDate',[None]*len(recent['form']))[i], 'publisher':'SEC EDGAR','url':f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-", "")}/{recent["primaryDocument"][i]}','retrieved_at':now(),'read_status':'not_read','full_text':False})
            if len(filings)>=50: break
        company['filings']=filings; company['retrieved_at']=now()
        company['listed_classes']=sub.get('tickers',[])
        company['multiple_share_classes']=len(company['listed_classes'])>1
        if company['multiple_share_classes']:company['limitations'].append('Emisor con varias clases cotizadas: acciones y EPS XBRL no se atribuyen automáticamente a una clase. Múltiplos desactivados; el DCF requiere acciones de la clase verificadas manualmente.')
        return company

    async def read_document(self,url):
        p=urlparse(url)
        if p.hostname!='www.sec.gov' or not p.path.startswith('/Archives/edgar/data/') or p.query:
            raise ProviderError('Solo se pueden recuperar documentos oficiales SEC','unsafe_url')
        text=await fetch(url,text=True,ttl=86400)
        soup=BeautifulSoup(text,'html.parser')
        for tag in soup(['script','style','noscript','iframe','svg']): tag.decompose()
        content=' '.join(soup.stripped_strings)
        return {'text':content[:120000],'content_hash':hashlib.sha256(content.encode()).hexdigest(),'truncated':len(content)>120000,'read_status':'read','full_text':len(content)<=120000}

class FinnhubProvider:
    def key(self):
        if not settings.finnhub_api_key: raise ProviderError('Falta FINNHUB_API_KEY','missing_credentials')
        return settings.finnhub_api_key

    async def instrument(self,symbol):
        # Profile currency is the reporting currency, not necessarily the quote currency.
        # Resolve the exact US-listed instrument (SEC tickers), including trading currency.
        instruments=await fetch('https://finnhub.io/api/v1/stock/symbol',{'exchange':'US','token':self.key()},ttl=86400)
        exact=[r for r in instruments if r.get('symbol')==symbol] if isinstance(instruments,list) else []
        if not exact and '-' in symbol:
            exact=[r for r in instruments if r.get('symbol')==symbol.replace('-','.')]
        if len(exact)!=1 or not exact[0].get('currency'):
            raise ProviderError('No se pudo verificar la divisa del instrumento cotizado','ambiguous_currency')
        return exact[0]

    async def quote(self,symbol):
        instrument=await self.instrument(symbol)
        d=await fetch('https://finnhub.io/api/v1/quote',{'symbol':instrument['symbol'],'token':self.key()},ttl=60)
        if not isinstance(d.get('c'),(int,float)) or not math.isfinite(d['c']) or d['c']<=0 or not isinstance(d.get('t'),(int,float)) or not 0<d['t']<=time.time()+300 or not instrument.get('currency'):
            raise ProviderError('Cotización sin precio positivo, fecha válida o divisa','missing_data')
        return {'price':d['c'],'currency':instrument['currency'],'timestamp':datetime.fromtimestamp(d['t'],timezone.utc).isoformat(),'retrieved_at':now(),'type':'latest_available_not_guaranteed_realtime','source':'https://finnhub.io/docs/api/quote','provider':'Finnhub','stale':time.time()-d['t']>86400,'change_percent':d.get('dp'),'exchange':instrument.get('mic'),'instrument':{'symbol':instrument['symbol'],'figi':instrument.get('figi'),'type':instrument.get('type')},'currency_source':'https://finnhub.io/docs/api/stock-symbols'}

    async def news(self,symbol,days):
        today=date.today()
        instrument=await self.instrument(symbol)
        d=await fetch('https://finnhub.io/api/v1/company-news',{'symbol':instrument['symbol'],'from':(today-timedelta(days=days)).isoformat(),'to':today.isoformat(),'token':self.key()},ttl=600)
        if not isinstance(d,list): raise ProviderError('Noticias: respuesta no válida','invalid_response')
        out=[]
        for n in d:
            url=n.get('url',''); parsed=urlparse(url)
            if parsed.scheme not in ('http','https') or not n.get('headline') or not isinstance(n.get('datetime'),(int,float)) or not 0<n['datetime']<=time.time(): continue
            out.append({'id':f'finnhub:{n.get("id")}','title':n['headline'],'url':url,'publisher':n.get('source'),'published_at':datetime.fromtimestamp(n['datetime'],timezone.utc).isoformat(),'event_date':None,'retrieved_at':now(),'summary':n.get('summary',''),'read_status':'abstract_only','full_text':False,'relation':'Relacionado por el proveedor; verificar entidad y materialidad.','topic':n.get('category','company'),'quality':'unverified_abstract'})
        return out

    async def earnings_calendar(self,symbol,start,end):
        instrument=await self.instrument(symbol)
        data=await fetch('https://finnhub.io/api/v1/calendar/earnings',{'symbol':instrument['symbol'],'from':start,'to':end,'token':self.key()},ttl=3600)
        if not isinstance(data,dict) or not isinstance(data.get('earningsCalendar'),list):
            raise ProviderError('Calendario no disponible: verifica cobertura, cuota y derechos del proveedor.','calendar_unavailable')
        out=[];seen=set()
        for event in data['earningsCalendar']:
            if event.get('symbol')!=instrument['symbol']:continue
            day=event.get('date')
            try:date.fromisoformat(day)
            except (ValueError,TypeError):continue
            if not start<=day<=end:continue
            key=(day,event.get('year'),event.get('quarter'))
            if key in seen:continue
            seen.add(key)
            out.append({'symbol':symbol,'event_date':day,'title':f'Resultados estimados · {symbol}',
                        'date_status':'estimated','fiscal_year':event.get('year'),'fiscal_quarter':event.get('quarter'),
                        'session':event.get('hour'),'source_url':'https://finnhub.io/docs/api/earnings-calendar',
                        'retrieved_at':now(),'interpretation':'Calendario del proveedor, pendiente de confirmación oficial. Una fecha estimada puede cambiar.'})
        return {'symbol':symbol,'from':start,'to':end,'items':sorted(out,key=lambda e:e['event_date']),
                'coverage':'Solo fechas devueltas por Finnhub; una lista vacía no demuestra ausencia de resultados o catalizadores.'}

class AlphaVantageProvider:
    async def history(self,symbol,adjusted=True):
        if not settings.alphavantage_api_key:raise ProviderError('Falta ALPHAVANTAGE_API_KEY','missing_credentials')
        function='TIME_SERIES_DAILY_ADJUSTED' if adjusted else 'TIME_SERIES_DAILY'
        d=await fetch('https://www.alphavantage.co/query',{'function':function,'symbol':symbol,'outputsize':'compact','apikey':settings.alphavantage_api_key},ttl=86400)
        series=d.get('Time Series (Daily)')
        if not series:raise ProviderError('Serie ajustada no disponible en el plan actual; puedes elegir explícitamente precios sin ajustar.' if adjusted else 'Serie diaria no disponible: verifica cuota, símbolo y derechos del plan.','provider_entitlement')
        if d.get('Meta Data',{}).get('2. Symbol')!=symbol:raise ProviderError('Símbolo de la serie no coincide con el solicitado','identity_mismatch')
        points=[]
        for key,value in sorted(series.items()):
            close=float(value['4. close']);observed=float(value['5. adjusted close']) if adjusted else close
            if not math.isfinite(observed) or observed<=0:raise ProviderError('Precio histórico no válido','invalid_response')
            row={'date':key,'close':close,'volume':int(value['6. volume'] if adjusted else value['5. volume'])}
            if adjusted:row.update(adjusted_close=observed,dividend=float(value['7. dividend amount']),split=float(value['8. split coefficient']))
            points.append(row)
        currency=None
        try:currency=(await market.instrument(symbol))['currency']
        except ProviderError:pass
        return {'source':'https://www.alphavantage.co/documentation/#dailyadj' if adjusted else 'https://www.alphavantage.co/documentation/#daily','adjusted':adjusted,'currency':currency,'retrieved_at':now(),'adjustment':'Proveedor: splits y dividendos; retorno ajustado, no índice reinvertido certificado.' if adjusted else 'PRECIOS SIN AJUSTAR. Splits y dividendos pueden distorsionar retornos e indicadores. No es rentabilidad total.','points':points}

sec=SECProvider(); market=FinnhubProvider(); historical=AlphaVantageProvider()
