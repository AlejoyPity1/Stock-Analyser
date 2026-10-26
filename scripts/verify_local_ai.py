"""Run on the Windows PC hosting LM Studio. No paid APIs or database fixtures."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.config import settings
from app.local_ai import synthesize_local
from app.providers import ProviderError
from app.research import ResearchRequest


async def verify():
    # Synthetic evidence, deliberately not presented as facts about any company.
    sources = [
        {'id': 'LOCAL-CHECK-S1', 'title': 'Synthetic revenue fixture', 'read_status': 'read',
         'text': 'Synthetic test only. Reported revenue was 110 million dollars, compared with 100 million dollars in the previous period.'},
        {'id': 'LOCAL-CHECK-S2', 'title': 'Synthetic uncertainty fixture', 'read_status': 'abstract_only',
         'summary': 'Synthetic test only. Management has not provided next-quarter guidance. A suggested earnings date is an estimate and has not been confirmed.'},
    ]
    try:
        result = await synthesize_local(sources, ResearchRequest(symbol='TEST', horizon='3-6m', use_ai=True))
        passed = result['status'] == 'generated_quote_verified' and bool(result['data']['claims'])
        diagnostic = {key: result[key] for key in ('status', 'code', 'reason', 'diagnostics', 'usage') if key in result}
        if not passed and result['status'] == 'generated_quote_verified':
            diagnostic.update(code='local_ai_empty_claims', reason='The answer passed validation but contained no claims.')
        return {'check': 'local-ai-protocol-and-quotation-check', 'synthetic_evidence': True,
                'passed': passed, 'paid_api_calls': 0, 'financial_quality_evaluated': False,
                'gpu_acceleration_verified': False, **diagnostic, 'result': result}
    except ProviderError as error:
        return {'passed': False, 'paid_api_calls': 0, 'model': settings.local_ai_model,
                'code': error.code, 'reason': error.message}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='local-ai-check.json')
    args = parser.parse_args()
    result = asyncio.run(verify())
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'result'}, ensure_ascii=False, indent=2))
    print('Full result saved to ' + args.output)
    raise SystemExit(0 if result['passed'] else 1)
