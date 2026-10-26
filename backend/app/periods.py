"""Standalone quarters and TTM from reported durations, with explicit derivation provenance."""
from datetime import date, timedelta
from .finance import ttm
from .store import now


def periods(raw, taxonomy, currency, cik, tags, instants, asof):
    facts=raw.get('facts',{}).get(taxonomy,{})
    durations={}; balances={}
    for metric, aliases in tags.items():
        unit='shares' if metric=='shares' else f'{currency}/shares' if metric=='eps' else currency
        selected={}
        for priority,tag in enumerate(aliases):
            for e in facts.get(tag,{}).get('units',{}).get(unit,[]):
                if e.get('form') not in ('10-Q','10-K','10-K/A','10-Q/A','20-F','20-F/A','40-F','6-K'):continue
                if e.get('filed','9999')>asof or e.get('end','9999')>asof:continue
                if not isinstance(e.get('val'),(int,float)):continue
                import math
                if not math.isfinite(e['val']):continue
                if metric not in instants and not e.get('start'):continue
                key=(e.get('start'),e['end']) if metric not in instants else e['end']
                rank=(e.get('filed',''),-priority)
                if key in selected and selected[key][0]>rank:continue
                source=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{e.get("accn", "").replace("-", "")}/'
                val={'value':e['val'],'unit':unit,'currency':currency if unit!='shares' else None,'period_start':e.get('start'),'period_end':e['end'],'filed':e.get('filed'),'retrieved_at':now(),'accession':e.get('accn'),'source':source,'source_id':f'{e.get("accn")}:{tag}:{key}','tag':f'{taxonomy}:{tag}','quality':'reported'}
                selected[key]=(rank,val)
        if metric in instants: balances[metric]={k:v[1] for k,v in selected.items()}
        else:durations[metric]=[v[1] for v in selected.values()]
    quarters={}
    for metric, entries in durations.items():
        direct={}
        for v in entries:
            days=(date.fromisoformat(v['period_end'])-date.fromisoformat(v['period_start'])).days+1
            if 70<=days<=110:
                key=(v['period_start'],v['period_end'])
                direct[key]=v
        # YTD cash flows and annual Q4 are differenced, never added as if standalone.
        if metric!='eps':
            for current in entries:
                cd=(date.fromisoformat(current['period_end'])-date.fromisoformat(current['period_start'])).days+1
                if not 150<=cd<=380:continue
                preceding=[p for p in entries if p['period_start']==current['period_start'] and 70<=(date.fromisoformat(current['period_end'])-date.fromisoformat(p['period_end'])).days<=110]
                if not preceding:continue
                previous=max(preceding,key=lambda p:p['period_end'])
                start=(date.fromisoformat(previous['period_end'])+timedelta(days=1)).isoformat()
                key=(start,current['period_end'])
                if key in direct:continue
                pd=(date.fromisoformat(previous['period_end'])-date.fromisoformat(previous['period_start'])).days+1
                value=(current['value']*cd-previous['value']*pd)/(cd-pd) if metric=='shares' else current['value']-previous['value']
                direct[key]={**current,'value':value,'period_start':start,'quality':'derived','components':[current,previous],'formula':'(YTD weighted shares × YTD days − prior YTD weighted shares × prior days) / quarter days' if metric=='shares' else 'Current YTD (or FY) − preceding YTD with identical fiscal start'}
        for (start,end),value in direct.items():
            # One fiscal duration per end, not a mixture of calendar and fiscal quarters.
            row=quarters.setdefault(end,{'start':start,'end':end,'values':{}})
            if row['start']==start:row['values'][metric]=value
    quarters={end:q for end,q in quarters.items() if 'revenue' in q['values']}
    for end,q in quarters.items():
        for metric,values in balances.items():
            if end in values:q['values'][metric]=values[end]
    ordered=sorted(quarters.values(),key=lambda q:q['end'],reverse=True)
    trailing=None
    if len(ordered)>=4:
        last=ordered[:4];values={}
        for metric in set().union(*(set(q['values']) for q in last)):
            if metric in instants:
                if metric in last[0]['values']:values[metric]=last[0]['values'][metric]
                continue
            if metric=='eps' or not all(metric in q['values'] for q in last):continue
            components=[q['values'][metric] for q in reversed(last)]
            try:value=ttm([{'start':q['start'],'end':q['end'],'value':q['values'][metric]['value'],'currency':currency} for q in last],weighted_average=metric=='shares')
            except ValueError:continue
            values[metric]={**components[-1],'value':value,'period_start':last[-1]['start'],'period_end':last[0]['end'],'filed':max(c['filed'] for c in components),'quality':'derived','components':components,'formula':'Days-weighted average of four contiguous standalone quarters' if metric=='shares' else 'Sum of four contiguous standalone quarters'}
        if 'revenue' in values:trailing={'start':last[-1]['start'],'end':last[0]['end'],'values':values,'period_type':'ttm'}
    return ordered[:40],trailing
