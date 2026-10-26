"""Analyze saved sources with local AI; create a new record only after full validation."""
import argparse
import asyncio
from copy import deepcopy
import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app.local_ai import synthesize_local
from app.providers import ProviderError
from app.research import ResearchRequest
from app.store import get, now, put, records


async def reanalyze(symbol=None, record_id=None, on_progress=None):
    if settings.ai_provider != 'local':
        raise ProviderError('Select AI_PROVIDER=local for saved-source reanalysis.', 'local_ai_disabled')
    saved = records('research')
    if any(row['data'].get('status') in ('queued', 'running') for row in saved):
        return {'passed': False, 'code': 'research_still_running',
                'reason': 'Wait for running research to finish before local reanalysis.'}
    candidates = [row for row in saved if symbol is None or row['symbol'] == symbol]
    job = get(record_id) if record_id else candidates[0]['data'] if candidates else None
    if not job or not job.get('sources'):
        return {'passed': False, 'code': 'saved_research_missing'}
    if not job.get('investment_horizon'):
        return {'passed': False, 'code': 'saved_horizon_missing'}
    request = ResearchRequest.model_validate(job['request']).model_copy(update={'use_ai': True})
    result = await synthesize_local(job['sources'], request, job['investment_horizon'], on_progress,
                                    company_context=job.get('financial_snapshot'))
    passed = result['status'] == 'generated_quote_verified' and bool(result['data']['claims'])
    summary = {'check': 'saved-source-local-reanalysis', 'passed': passed,
               'original_record_id': job['id'], 'symbol': request.symbol,
               'source_retrieval_calls': 0, 'paid_api_calls': 0,
               'original_record_modified': False, 'financial_quality_evaluated': False,
               'status': result['status'], 'citation_method': result['coverage']['citation_method'],
               'completed_batches': len(result.get('usage', [])),
               'planned_batches': result['coverage']['batch_count'],
               'structured_financial_periods': len(result.get('data', {}).get('financial_facts', [])),
               'withheld_financial_statements': result.get('data', {}).get('quality_control', {}).get('withheld_count', 0),
               'excluded_sources': result['coverage']['source_screening'].get('excluded_count', 0), 'ai': result}
    if not passed:
        summary.update({key: result[key] for key in ('code', 'reason', 'diagnostics') if key in result})
        if result['status'] == 'generated_quote_verified':
            summary.update(code='local_ai_empty_claims', reason='No evidence claims were returned.')
        return summary
    fresh = deepcopy(job)
    fresh.update(id=str(uuid4()), created_at=now(), updated_at=now(), status='completed',
                 stage='Local AI analysis completed using saved sources', ai=result, request=request.model_dump())
    fresh['stats'] = {**job.get('stats', {}), 'used_for_synthesis': len(result['data']['used_source_ids'])}
    previous = job.get('reanalysis') or {}
    fresh['reanalysis'] = {'of_record_id': job['id'],
                           'source_snapshot_created_at': previous.get('source_snapshot_created_at', job['created_at']),
                           'source_retrieval_calls': 0, 'horizon_preserved': True}
    put(fresh['id'], 'research', request.symbol, fresh)
    return {**summary, 'new_record_id': fresh['id'], 'claim_count': len(result['data']['claims']),
            'used_source_count': len(result['data']['used_source_ids'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol')
    parser.add_argument('--record')
    parser.add_argument('--output', default='local-ai-reanalysis.json')
    args = parser.parse_args()
    symbol = ResearchRequest(symbol=args.symbol.upper()).symbol if args.symbol else None
    try:
        result = asyncio.run(reanalyze(symbol, args.record, on_progress=print))
    except ProviderError as error:
        result = {'passed': False, 'code': error.code, 'reason': error.message, 'paid_api_calls': 0}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'ai'}, indent=2))
    print('Full result saved to ' + args.output)
    raise SystemExit(0 if result['passed'] else 1)
