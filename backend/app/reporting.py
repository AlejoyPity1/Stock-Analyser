"""Evidence dossier: deterministic sections, explicit gaps, standalone PDF. No AI calls."""
from io import BytesIO
from xml.sax.saxutils import escape
from .finance import ratios
from .analytics import advanced_analytics
from .catalysts import event_position
from .store import get,records,now


def build_report(id):
    data=get(id)
    if not data or 'symbol' not in data:return None
    company=data.get('financial_snapshot') or {}
    quote=data.get('market_snapshot')
    horizon=data.get('investment_horizon')
    annual=company.get('statements',[])
    latest=annual[0] if annual else None
    valuations=[r['data'] for r in records('valuation',data['symbol']) if r['id'] in data.get('valuation_ids',[]) or r['data'].get('research_id')==id]
    relative=[r['data'] for r in records('relative',data['symbol']) if r['id'] in data.get('relative_ids',[]) or r['data'].get('research_id')==id]
    analysis=data.get('analytics') or advanced_analytics(company,quote)
    scenarios=[r['data'] for r in records('scenario',data['symbol']) if r['id'] in data.get('scenario_ids',[]) or r['data'].get('research_id')==id]
    price_scenarios=[r['data'] for r in records('price_scenario',data['symbol']) if r['id'] in data.get('price_scenario_ids',[]) or r['data'].get('research_id')==id]
    selected_catalysts=[r['data'] for r in records('catalyst',data['symbol'],limit=1000) if r['id'] in data.get('catalyst_ids',[]) or r['data'].get('research_id')==id]
    catalysts=[];seen_events=set()
    for event in selected_catalysts:
        if event['event_id'] not in seen_events:
            catalysts.append(event);seen_events.add(event['event_id'])
    ai=data.get('ai',{});synthesis=ai.get('data',{}) if ai.get('status')=='generated_quote_verified' else {}
    sections=[]
    def add(title,status='not_available',text='',rows=None):
        sections.append({'number':len(sections)+1,'title':title,'status':status,'text':text or 'Información no disponible o evaluación pendiente. No se sustituye por una conclusión inventada.','rows':rows or []})
    summary=data.get('report',{}).get('summary') or data.get('error') or 'Expediente en preparación. Sin conclusión automática de inversión.'
    if horizon:
        summary+=f" Horizonte elegido: {horizon['label']}, entre {horizon['window_start_date']} y {horizon['window_end_date']}, desde {horizon['as_of']}. "+horizon['interpretation']
    else:
        summary+=' El expediente original no tiene horizonte registrado; no se le asigna uno retroactivamente.'
    add('Executive Summary','partial',summary)
    add('Company Overview','available' if company else 'not_available',f"{company.get('name',data['symbol'])}; ticker {data['symbol']}; CIK {company.get('cik','no disponible')}; sector {company.get('industry','no disponible')}; moneda de reporte {company.get('currency','no disponible')}.")
    add('Business Model',text='A complete business-model analysis requires review of official documents; a bounded AI summary does not establish full coverage.')
    add('Industry Analysis','partial' if company.get('industry') else 'not_available',company.get('industry'))
    add('Competitive Positioning',text='No se infiere posición competitiva ni comparabilidad por pertenecer al mismo sector.')
    rows=[]
    for a in annual:
        rows.append({'period_end':a['end'],'currency':company.get('currency'),'revenue':a['values'].get('revenue',{}).get('value'),'net_income':a['values'].get('net_income',{}).get('value'),'operating_cash_flow':a['values'].get('ocf',{}).get('value'),'capex':a['values'].get('capex',{}).get('value')})
    add('Historical Financial Performance','available' if rows else 'not_available','Estados anuales; no se mezclan con TTM. Cada cifra conserva su procedencia en el snapshot JSON.',rows)
    metrics=ratios(latest['values']) if latest else {}
    add('Financial Strength','partial' if metrics else 'not_available','Indicadores deterministas sobre el último ejercicio. No constituyen una recomendación.',[{'metric':k,'value':v} for k,v in metrics.items() if v is not None]+[{'metric':v['label'],'value':v['value'],'status':v['status'],'reason':v['reason'],'formula':v['formula']} for v in analysis['metrics'].values()])
    sources=data.get('sources',[])
    add('Recent Developments','partial' if sources else 'not_available','Publicaciones recuperadas; un extracto no es una lectura del artículo original.',[{'title':s['title'],'published_at':s.get('published_at'),'read_status':s.get('read_status'),'url':s['url']} for s in sources])
    add('News and Catalyst Analysis','partial' if sources or catalysts else 'not_available','Fechas e hipótesis de catalizadores revisadas por el usuario. Una cita coincidente no verifica su interpretación. Las fechas de publicación no prueban fechas de eventos futuros. No se modifica el modelo automáticamente.',[{'source_id':s['id'],'assessment':s.get('financial_impact',{}).get('reason')} for s in sources]+[{'event_id':c['event_id'],'title':c['title'],'event_date':c['event_date'],'date_status':c['date_status'],'status':c['status'],'verification':c['verification'],'position':event_position(c,horizon) if horizon else 'horizon_not_registered','hypothesis':c['hypothesis'],'invalidation':c['invalidation'],'source_url':c['source_url']} for c in catalysts])
    add('Valuation','available' if valuations or relative else 'not_available','DCF y valor relativo condicional: hipótesis manuales, no predicción de cotización.',[{'id':v['id'],'method':'DCF','created_at':v['created_at'],'fair_value':v['fair_value'],'currency':v['currency'],'rationale':v['justification']} for v in valuations]+[{'id':v['id'],'method':'relative','created_at':v['created_at'],'value_per_share':v['implied_per_share'],'currency':v['currency'],'metric':v['inputs']['metric'],'rationale':v['inputs']['rationale']} for v in relative])
    add('Reverse DCF','available' if valuations else 'not_available','Crecimiento implícito manteniendo constantes las demás hipótesis.',[{'valuation_id':v['id'],**v.get('reverse_dcf',{})} for v in valuations])
    add('Bear / Base / Bull Scenarios','available' if scenarios or price_scenarios else 'not_available','DCF: valores presentes. Escenarios de cotización a 3/6 meses: EPS forward × P/E supuesto, hipótesis manuales y dividendos sin reinversión. No se asignan probabilidades ni se afirma un pronóstico validado.',[{'scenario_set':s['id'],'method':'DCF present value','created_at':s['created_at'],'cases':{k:{'fair_value':v['fair_value'],'currency':v['currency'],'rationale':v['inputs']['rationale']} for k,v in s['results'].items()}} for s in scenarios]+[{'scenario_set':s['id'],'method':s['model_version'],'created_at':s['created_at'],'currency':s['currency'],'reference_quote':s['reference_quote'],'horizons':s['horizons']} for s in price_scenarios])
    risks=[]
    for v in valuations:
        risks.extend(f"Modelo {v['id']}: {w}" for w in v.get('warnings',[]))
    if quote and company and quote['currency']!=company.get('currency'):
        risks.append('Divisa de cotización distinta de la moneda de reporte: no hay múltiplos o upside sin conversión explícita verificada.')
    add('Risk Assessment','partial', '\n'.join(risks) if risks else 'Evaluación cualitativa pendiente. No se fabrican riesgos específicos de la empresa.')
    add('Investment Thesis','partial' if synthesis else 'not_available','\n'.join(synthesis.get('bull_case',[])) or 'No quoted bullish thesis is available. Review source coverage and missing evidence.')
    add('Counterarguments','partial' if synthesis else 'not_available','\n'.join(synthesis.get('bear_case',[])))
    add('Unresolved Questions','partial','\n'.join(synthesis.get('unresolved',[])+data.get('report',{}).get('limitations',[])) or 'Revisar datos ausentes, sostenibilidad de supuestos y disponibilidad de fuentes.')
    add('Final Assessment','partial','Evidence, calculations and any quoted AI claims require review before an investment conclusion. Local AI does not establish forecast accuracy or exhaustive research coverage.')
    add('Sources and Methodology','available','SEC XBRL y documentos oficiales; Finnhub para cotización/extractos. Cálculos deterministas FCFF v1.0. Precios sin garantía de tiempo real. Datos financieros y fuentes con fechas independientes.',[{'source_id':s['id'],'url':s['url'],'retrieved_at':s.get('retrieved_at'),'read_status':s.get('read_status'),'content_hash':s.get('content_hash')} for s in sources])
    return {'report_version':'evidence-2.3','exported_at':now(),'record':data,'investment_horizon':horizon,'snapshot':company,'related_valuations':valuations,'related_scenarios':scenarios,'price_scenarios':price_scenarios,'catalysts':catalysts,'relative_valuations':relative,'analytics':analysis,'quote':quote,'sections':sections,'methodology':'Los snapshots y modelos preservan las entradas usadas. Secciones no evaluadas se señalan explícitamente; esta estructura no certifica un informe profesional completo.'}


def render_pdf(report):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
    from reportlab.graphics.shapes import Drawing,String
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    stream=BytesIO();styles=getSampleStyleSheet()
    for style in styles.byName.values():style.wordWrap='CJK'
    styles['BodyText'].fontSize=9;styles['BodyText'].leading=13
    def paragraph(text,style='BodyText'):
        return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
    story=[paragraph('STOCK INTELLIGENCE AI','Title'),paragraph(report['record']['symbol']+' · Expediente de evidencia','Heading1'),paragraph('Generado: '+report['exported_at']),paragraph(report['methodology']),Spacer(1,12)]
    horizon=report.get('investment_horizon')
    if horizon:
        story.append(paragraph(f"Horizonte: {horizon['label']} · Fecha base: {horizon['as_of']} · Ventana: {horizon['window_start_date']} a {horizon['window_end_date']}",'Heading2'))
        story.append(paragraph(horizon['interpretation']))
        for focus in horizon['focus']:story.append(paragraph(focus))
    else:
        story.append(paragraph('Horizonte no registrado en el expediente original.'))
    quote=report.get('quote')
    if quote:story.append(paragraph(f"Precio disponible: {quote['price']} {quote['currency']} · {quote['timestamp']} · sin garantía de tiempo real."))
    for section in report['sections']:
        story.extend([paragraph(f"{section['number']}. {section['title']}",'Heading2'),paragraph('Estado: '+section['status']),paragraph(section['text'])])
        for row in section['rows']:
            # Key/value layout wraps long source URLs without clipping wide tables.
            for key,value in row.items():
                if value is not None:story.append(paragraph(f'{key}: {value}'))
            story.append(Spacer(1,7))
    ai = report['record'].get('ai', {})
    if ai:
        story.append(paragraph('AI evidence analysis and audit', 'Heading2'))
        story.append(paragraph(f"Status: {ai.get('status')} · Provider: {ai.get('provider', 'not recorded')} · Model: {ai.get('model', ai.get('billing', {}).get('model', 'not recorded'))}"))
        if ai.get('reason'): story.append(paragraph(ai['reason']))
        if ai.get('status') == 'generated_quote_verified':
            story.append(paragraph(ai['data']['summary']))
            if ai['data'].get('financial_facts'):
                story.append(paragraph('Reported financial context (structured SEC facts)', 'Heading2'))
                for period in ai['data']['financial_facts']:
                    story.append(paragraph(f"{period['period_type']} · {period['period_start']} to {period['period_end']}", 'Heading3'))
                    for metric, fact in period['values'].items():
                        story.append(paragraph(f"{metric}: {fact['value']:,} {fact['unit']} · {fact.get('quality', 'reported')} · source: {fact['source']}"))
                story.append(paragraph('Values are unscaled. Share counts are weighted-average diluted shares for the stated period, not current shares outstanding.'))
            withheld = ai['data'].get('quality_control', {}).get('withheld_count', 0)
            if withheld:
                story.append(paragraph(f'{withheld} numerical financial statement(s) from the model were withheld; use structured financial facts and review the remaining interpretations.'))
            for claim in ai['data']['claims']:
                story.append(paragraph(f"{claim['kind']} · {claim['side']} · {claim['source_id']}", 'Heading3'))
                story.append(paragraph(claim['text']))
                story.append(paragraph('Verbatim evidence: '+claim['evidence_quote']))
                story.append(paragraph(claim['financial_mechanism']))
            for conflict in ai['data'].get('contradictions', []): story.append(paragraph(conflict))
            for question in ai['data'].get('unresolved', []): story.append(paragraph(question))
        if ai.get('coverage'): story.append(paragraph('Coverage and omissions: '+str(ai['coverage'])))
        for limitation in ai.get('limitations', []): story.append(paragraph(limitation))
    for valuation in report['related_valuations']:
        story.append(paragraph('Anexo: modelo '+valuation['id'],'Heading2'))
        story.append(paragraph(valuation['formula']))
        for k,v in valuation['inputs'].items():story.append(paragraph(f'{k}: {v}'))
        projection=valuation.get('projections',[])
        if projection:
            drawing=Drawing(450,190);chart=VerticalBarChart();chart.x=45;chart.y=35;chart.width=360;chart.height=130
            chart.data=[[p['fcff']/1e6 for p in projection]];chart.categoryAxis.categoryNames=[str(p['year']) for p in projection];chart.bars[0].fillColor=colors.HexColor('#55794b');drawing.add(chart);drawing.add(String(45,175,'FCFF proyectado (millones, moneda del modelo)',fontSize=9));story.append(drawing)
    for valuation in report.get('relative_valuations',[]):
        story.append(paragraph('Anexo: valoración relative '+valuation['id'],'Heading2'))
        story.append(paragraph(valuation['inputs']['rationale']))
        story.append(paragraph(valuation['formula']))
        story.append(paragraph('Distribución: '+str(valuation['distribution'])))
        story.append(paragraph('Valor por acción: '+str(valuation['implied_per_share'])+' '+valuation['currency']))
        for row in [valuation['target']]+valuation['peers']:
            story.append(paragraph(str({k:row.get(k) for k in ['symbol','period_end','currency','multiple','eligible','reasons']})))
        for limitation in valuation['limitations']:story.append(paragraph(limitation))
    for model in report.get('price_scenarios',[]):
        story.append(paragraph('Anexo: escenarios de cotización '+model['id'],'Heading2'))
        story.append(paragraph(model['formula']))
        story.append(paragraph('Cotización de referencia: '+str(model['reference_quote'])))
        for months,projection in model['horizons'].items():
            story.append(paragraph(f"{months} meses · {projection['target_date']}",'Heading3'))
            for case,value in projection['cases'].items():story.append(paragraph(case+': '+str(value)))
            story.append(paragraph('Relación condicional beneficio/riesgo: '+str(projection['conditional_reward_risk'])))
        for event in model['catalysts']:
            story.append(paragraph('Catalizador conservado: '+str(event)))
        for limitation in model['limitations']:story.append(paragraph(limitation))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.drawString(40,24,'Stock Intelligence AI · Datos y supuestos con fechas propias');canvas.drawRightString(555,24,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(stream,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=40,title='Stock Intelligence AI - '+report['record']['symbol'])
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()
