"""Local readiness test with an explicitly synthetic, independently checkable DCF.
Does not persist fictitious financial data or call external APIs.
"""
import httpx
api='http://127.0.0.1:8000'
from app.config import settings
headers={'Authorization':f'Bearer {settings.app_token}'} if settings.app_token else {}
with httpx.Client(headers=headers,timeout=20) as c:
    assert c.get(api+'/health').json()['status']=='ok'
    r=c.post(api+'/valuation/preview',json={'revenue':1000,'growth':0,'operating_margin':.2,'tax_rate':0,'capex_ratio':0,'da_ratio':0,'nwc_ratio':0,'wacc':.1,'terminal_growth':0,'net_debt':0,'shares':100})
    r.raise_for_status()
    assert abs(r.json()['fair_value']-20)<1e-8
    assert c.get('http://127.0.0.1:3000/api/health').json()['status']=='ok'
    assert c.get('http://127.0.0.1:3000').status_code==200
print('PASS: backend, frontend, proxy y DCF controlado (perpetuidad 200/10%/100 = 20). Sin datos reales ni persistencia de prueba.')
