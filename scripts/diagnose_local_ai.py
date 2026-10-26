"""Replay one saved evidence batch locally. Never modifies a research record."""
import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.config import settings
from app import local_ai
from app.local_ai import _json, _request, check_local_model, make_batches
from app.providers import ProviderError
from app.research import ResearchRequest
from app.store import get, records
from app.synthesis import SYSTEM, Synthesis, quotes_match


def inspect_response(response, evidence, references=None):
    """Explain a rejection without printing internal reasoning or accepting fuzzy quotes."""
    if references is not None:
        parsed, rejection = local_ai._parse_completion(response, references)
        if rejection:
            return {'passed': False, **rejection}
        return {'passed': bool(parsed.synthesis.claims), 'claim_count': len(parsed.synthesis.claims),
                'withheld_financial_statements': len(parsed.withheld),
                'selected_evidence_ids': parsed.evidence_ids,
                'code': 'generated_quote_verified' if parsed.synthesis.claims else 'local_ai_empty_claims'}
    choices = response.get('choices')
    choice = choices[0] if isinstance(choices, list) and choices else None
    message = choice.get('message') if isinstance(choice, dict) else None
    if not isinstance(message, dict):
        return {'passed': False, 'code': 'local_ai_invalid_response'}
    content = message.get('content')
    usage = response.get('usage')
    detail = usage.get('completion_tokens_details') if isinstance(usage, dict) else None
    diagnostic = {
        'finish_reason': choice.get('finish_reason'),
        'content_characters': len(content) if isinstance(content, str) else 0,
        'completion_tokens': usage.get('completion_tokens') if isinstance(usage, dict) else None,
        'reasoning_tokens': detail.get('reasoning_tokens') if isinstance(detail, dict) else None,
    }
    result = {'passed': False, 'diagnostics': diagnostic}
    if choice.get('finish_reason') != 'stop':
        return {**result, 'code': 'local_ai_output_truncated' if choice.get('finish_reason') == 'length'
                else 'local_ai_incomplete_output'}
    if message.get('tool_calls'):
        return {**result, 'code': 'local_ai_tool_call'}
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as error:
        return {**result, 'code': 'local_ai_invalid_json',
                'json_error': {'message': error.msg, 'character': error.pos}}
    except (TypeError, ValueError):
        return {**result, 'code': 'local_ai_invalid_json'}
    try:
        parsed = Synthesis.model_validate(decoded)
    except ValidationError as error:
        # Never include Pydantic's input/context, which can repeat the raw response.
        failures = [{'path': [str(part)[:100] for part in item['loc']], 'type': item['type']}
                    for item in error.errors(include_input=False, include_context=False, include_url=False)[:8]]
        return {**result, 'code': 'local_ai_invalid_synthesis', 'schema_errors': failures}
    if not quotes_match(parsed, evidence):
        mismatches = []

        def inspect_quote(path, source_id, quote):
            excerpts = evidence.get(source_id, [])
            if any(quote in excerpt for excerpt in excerpts):
                return
            # Formatting comparisons are diagnostic only. They NEVER validate a quote.
            normalized = re.sub(r'\s+', ' ', quote).strip()
            mismatches.append({'path': path, 'source_id': source_id[:200],
                               'source_was_supplied': bool(excerpts),
                               'quote_preview': quote[:300],
                               'quote_preview_ascii': json.dumps(quote[:300], ensure_ascii=True),
                               'whitespace_normalized_match': any(
                                   normalized in re.sub(r'\s+', ' ', excerpt).strip() for excerpt in excerpts),
                               'supplied_excerpt_previews': [excerpt[:400] for excerpt in excerpts[:2]]})

        for index, claim in enumerate(parsed.claims):
            inspect_quote(f'claims.{index}.evidence_quote', claim.source_id, claim.evidence_quote)
        same_source_conflicts = []
        for index, conflict in enumerate(parsed.contradictions):
            inspect_quote(f'contradictions.{index}.first_quote', conflict.first_source_id, conflict.first_quote)
            inspect_quote(f'contradictions.{index}.second_quote', conflict.second_source_id, conflict.second_quote)
            if conflict.first_source_id == conflict.second_source_id:
                same_source_conflicts.append(index)
        return {**result, 'code': 'local_ai_unmatched_quote',
                'unverified_quote_mismatches': mismatches[:4],
                'same_source_contradictions': same_source_conflicts}
    return {**result, 'passed': bool(parsed.claims), 'claim_count': len(parsed.claims),
            'code': 'generated_quote_verified' if parsed.claims else 'local_ai_empty_claims'}


async def diagnose_saved(symbol=None, record_id=None):
    if record_id:
        job = get(record_id)
    else:
        saved = records('research', symbol)
        job = saved[0]['data'] if saved else None
    if not job or not job.get('sources'):
        return {'passed': False, 'code': 'saved_research_missing',
                'reason': 'No saved research with source text was found.'}
    if job.get('status') in ('queued', 'running'):
        return {'passed': False, 'code': 'research_still_running',
                'reason': 'Wait for the current research to finish before replaying a batch.'}
    request = ResearchRequest.model_validate(job['request'])
    horizon = job.get('investment_horizon')
    if not horizon:
        return {'passed': False, 'code': 'saved_horizon_missing'}
    # The original batch builder and request contract also exist in the initial ZIP.
    # This script can therefore diagnose it without replacing backend files/restarting.
    if hasattr(local_ai, 'financial_facts'):
        batches, _ = make_batches(job['sources'], request, horizon, company_context=job.get('financial_snapshot'))
    else:
        batches, _ = make_batches(job['sources'], request, horizon)
    if not batches:
        return {'passed': False, 'code': 'no_readable_evidence'}
    batch = batches[0]
    payload = {'model': settings.local_ai_model,
               'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': _json(batch)}],
               'response_format': {'type': 'json_schema', 'json_schema': {
                   'name': 'research', 'strict': True, 'schema': Synthesis.model_json_schema()}},
               'temperature': 0.2, 'max_tokens': settings.local_ai_max_output_tokens, 'stream': False}
    references = None
    if hasattr(local_ai, 'completion_payload'):
        payload = local_ai.completion_payload(batch)
        references = {unit['evidence_id']: unit for unit in batch['sources']}
    fingerprint = hashlib.sha256(_json(payload).encode()).hexdigest()
    prior = job.get('ai', {}).get('request_audit') or []
    expected = prior[0].get('request_sha256') if prior else None
    await check_local_model()
    response = await _request('POST', '/chat/completions', payload)
    evidence = {}
    for unit in batch['sources']:
        evidence.setdefault(unit['id'], []).append(unit['excerpt'])
    return {'check': 'saved-local-evidence-batch-diagnostic', 'record_id': job['id'],
            'symbol': request.symbol, 'model': settings.local_ai_model,
            'batch_index': 1, 'total_batch_count': len(batches),
            'request_sha256': fingerprint,
            'same_payload_as_original_first_batch': fingerprint == expected if expected else None,
            'paid_api_calls': 0, 'source_retrieval_calls': 0, 'research_record_modified': False,
            'scope': 'One fresh local inference on saved sources; does not certify the original response or publish a synthesis.',
            **inspect_response(response, evidence, references)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', help='Optional ticker; otherwise use the latest saved research.')
    parser.add_argument('--record', help='Optional exact research record ID.')
    parser.add_argument('--output', default='local-ai-diagnostic.json')
    args = parser.parse_args()
    symbol = ResearchRequest(symbol=args.symbol.upper()).symbol if args.symbol else None
    try:
        result = asyncio.run(diagnose_saved(symbol, args.record))
    except ProviderError as error:
        result = {'passed': False, 'code': error.code, 'reason': error.message, 'paid_api_calls': 0}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True, indent=2))
    print('Diagnostic saved to ' + args.output)
    raise SystemExit(0 if result['passed'] else 1)
