"""Verify real profitability inputs and conditional peer valuation; no AI or saved models.

Run: PYTHONPATH=backend .venv/bin/python scripts/verify_analytics.py
HTTP responses may populate the provider cache. Does not recover/interrupt research jobs.
"""
import asyncio
import json
from datetime import datetime, timezone

from app.analytics import advanced_analytics
from app.comparables import ComparableRequest, relative_analysis
from app.providers import sec, market, ProviderError
from app.store import initialize


async def main():
    initialize()
    snapshots = {}
    for symbol in ('AAPL', 'GPRK', 'ASML', 'MSFT', 'ADP', 'INTU', 'ORCL'):
        try:
            company = await sec.company(symbol)
            quote = await market.quote(symbol)
            snapshots[symbol] = {
                'company': company, 'quote': quote,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        except ProviderError as error:
            snapshots[symbol] = {'symbol': symbol, 'error': error.message}
    fundamentals = []
    for symbol in ('AAPL', 'GPRK', 'ASML'):
        snapshot = snapshots[symbol]
        if snapshot.get('error'):
            fundamentals.append(snapshot)
            continue
        fundamentals.append({
            'symbol': symbol,
            'reporting_currency': snapshot['company']['currency'],
            'quote_currency': snapshot['quote']['currency'],
            **advanced_analytics(snapshot['company'], snapshot['quote']),
        })
    rationale = (
        'VALIDACIÓN TÉCNICA: software y servicios empresariales USD con cierres próximos; '
        'las diferencias de negocio, márgenes y riesgo requieren revisión y no certifican '
        'comparabilidad económica. No es una recomendación ni un precio objetivo.'
    )
    request = ComparableRequest(target='MSFT', peers=['ADP', 'INTU'], rationale=rationale)
    relative = relative_analysis(request, snapshots)
    comparison = relative_analysis(request.model_copy(update={'peers': ['ORCL', 'INTU']}), snapshots)
    evidence = {
        'verified_at': datetime.now(timezone.utc).isoformat(), 'ai_calls': 0,
        'fundamentals': fundamentals, 'relative_valuation': relative,
        'additional_peer_checks': [{k: row.get(k) for k in (
            'symbol', 'period_end', 'eligible', 'reasons', 'currency',
        )} for row in comparison['peers']],
    }
    print(json.dumps(evidence, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if relative['status'] == 'available' and not any(row.get('error') for row in fundamentals) else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
