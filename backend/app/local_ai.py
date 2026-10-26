"""Bounded LM Studio inference on this machine. Never falls back to a paid API."""
import asyncio
import hashlib
import json
import re
import time
from weakref import WeakKeyDictionary

import httpx

from .config import settings, loopback_ai_url
from .horizon import investment_horizon
from .providers import ProviderError
from .synthesis import SYSTEM, Synthesis, format_synthesis, quotes_match

_gates = WeakKeyDictionary()
_FINANCIAL = re.compile(
    r'revenue|net income|operating income|guidance|outlook|cash flow|liquidity|'
    r'capital expenditure|risk factors|results of operations|earnings|margin|'
    r'dividend|repurchase|regulat|litigation', re.I
)
LIMITATIONS = [
    'Literal quotations were checked only against the excerpts sent to the model; interpretation requires review.',
    'Excerpt selection uses bounded keyword windows, not semantic retrieval or exhaustive document analysis.',
    'Contradictions are assessed within batches; absence of a detected conflict is not proof of consistency.',
    'The model does not update valuations or produce validated price predictions.',
]


def local_base_url(value=None):
    value = settings.local_ai_base_url if value is None else value
    try:
        return loopback_ai_url(value)
    except (ValueError, AttributeError):
        raise ProviderError(
            'LOCAL_AI_BASE_URL must be a loopback URL such as http://127.0.0.1:1234/v1. '
            'Run Stock Analyser on the same Windows PC as LM Studio.', 'local_ai_configuration'
        ) from None


def _config():
    base = local_base_url()
    if (not settings.local_ai_model.strip() or len(settings.local_ai_model) > 200
            or settings.local_ai_model.lower().startswith(('text-embedding', 'nomic-embed'))):
        raise ProviderError('Set LOCAL_AI_MODEL to a chat model, for example qwen/qwen3.5-9b.', 'local_ai_configuration')
    if (not 4096 <= settings.local_ai_context_tokens <= 32768
            or not 256 <= settings.local_ai_max_output_tokens <= 4096
            or not 10 <= settings.local_ai_timeout_seconds <= 600
            or not 1 <= settings.local_ai_quick_batches <= 12
            or not 1 <= settings.local_ai_deep_batches <= 24):
        raise ProviderError('Local AI context, output, timeout or batch limits are invalid.', 'local_ai_configuration')
    return base


async def _request(method, path, payload=None):
    base = _config()
    headers = {'Authorization': f'Bearer {settings.local_ai_api_key}'} if settings.local_ai_api_key else {}
    try:
        # Only the validated literal loopback destination bypasses ambient proxies.
        # Public provider clients keep their inherited proxy/TLS configuration.
        async with httpx.AsyncClient(timeout=settings.local_ai_timeout_seconds,
                                     follow_redirects=False, trust_env=False) as client:
            async with client.stream(method, base + path, json=payload, headers=headers) as response:
                if response.status_code >= 300:
                    raise ProviderError(
                        f'LM Studio returned HTTP {response.status_code}. Check its server, authentication, '
                        'loaded model and structured-output support. No alternative provider was called.',
                        'local_ai_http_error'
                    )
                body = bytearray()
                async for part in response.aiter_bytes():
                    body.extend(part)
                    if len(body) > 2_000_000:
                        raise ProviderError('LM Studio response exceeded the size limit.', 'local_ai_response_too_large')
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise ValueError
                return result
    except httpx.TimeoutException:
        raise ProviderError('LM Studio timed out. Check GPU offload and context settings; reduce thinking/output if needed.', 'local_ai_timeout') from None
    except httpx.HTTPError:
        raise ProviderError('Cannot reach LM Studio on this machine. Start its server on port 1234 on the same PC.', 'local_ai_unreachable') from None
    except (ValueError, TypeError):
        raise ProviderError('LM Studio returned invalid JSON.', 'local_ai_invalid_response') from None


async def check_local_model():
    if settings.ai_provider != 'local':
        raise ProviderError('Set AI_PROVIDER=local and restart the application first.', 'local_ai_disabled')
    result = await _request('GET', '/models')
    rows = result.get('data')
    if not isinstance(rows, list):
        raise ProviderError('LM Studio returned an invalid model directory.', 'local_ai_invalid_response')
    if not any(isinstance(row, dict) and row.get('id') == settings.local_ai_model for row in rows):
        raise ProviderError('The exact configured LOCAL_AI_MODEL is not listed by LM Studio. Load it or correct the ID.', 'local_ai_model_missing')
    return {'status': 'reachable', 'provider': 'local', 'model': settings.local_ai_model,
            'inference_verified': False,
            'message': 'Model ID is listed. This check does not test generation, GPU use or financial accuracy.'}


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _prefix(text, byte_limit):
    return text.encode('utf-8')[:byte_limit].decode('utf-8', errors='ignore')


def _windows(text, byte_limit):
    if len(text.encode('utf-8')) <= byte_limit:
        return [(0, len(text), text)]
    # Exact contiguous windows. Their offsets and hashes are kept for audit.
    width = max(80, byte_limit // 3)
    candidates = []
    for match in list(_FINANCIAL.finditer(text))[:200]:
        start = max(0, match.start() - width // 4)
        excerpt = _prefix(text[start:], byte_limit)
        score = len({m.group().lower() for m in _FINANCIAL.finditer(excerpt)})
        candidates.append((score, start, start + len(excerpt), excerpt))
    if not candidates:
        excerpt = _prefix(text, byte_limit)
        return [(0, len(excerpt), excerpt)]
    result = []
    for _, start, end, excerpt in sorted(candidates, key=lambda row: (-row[0], row[1])):
        if not any(start < old_end and end > old_start for old_start, old_end, _ in result):
            result.append((start, end, excerpt))
        if len(result) == 2:
            break
    return sorted(result)


def make_batches(sources, request, horizon):
    _config()
    schema = Synthesis.model_json_schema()
    compact_horizon = {k: horizon[k] for k in (
        'code', 'as_of', 'min_months', 'max_months', 'window_start_date', 'window_end_date'
    ) if k in horizon}
    base = {'symbol': request.symbol, 'investment_horizon': compact_horizon, 'sources': []}
    # UTF-8 bytes conservatively bound ordinary byte-fallback tokenization. Reserve
    # schema, chat-template overhead, output, and room for non-text special tokens.
    overhead = len(SYSTEM.encode()) + len(_json(schema).encode()) + 512
    available = settings.local_ai_context_tokens - settings.local_ai_max_output_tokens - overhead
    if available < len(_json(base).encode()) + 500:
        raise ProviderError('The configured local context is too small for the evidence schema and output reserve.', 'local_ai_context_limit')
    excerpt_limit = min(1200, max(200, (available - len(_json(base).encode()) - 600) // 2))
    readable = []
    seen = set()
    for source in sources:
        if source.get('read_status') not in ('read', 'abstract_only'):
            continue
        text = source.get('text') or source.get('summary') or ''
        if not isinstance(text, str) or not text.strip():
            continue
        sid = source['id']
        if sid in seen:
            raise ProviderError('Duplicate evidence source IDs cannot be analyzed safely.', 'local_ai_duplicate_source')
        seen.add(sid)
        units = []
        for start, end, excerpt in _windows(text, excerpt_limit):
            units.append({'id': sid, 'title': str(source.get('title', ''))[:100],
                          'read_status': source['read_status'], 'start': start, 'end': end,
                          'excerpt': excerpt})
        readable.append((source, text, units))
    # Give each readable source one window before adding any second window.
    units = [row[2][i] for i in range(2) for row in readable if len(row[2]) > i]
    limit = settings.local_ai_quick_batches if request.mode == 'quick' else settings.local_ai_deep_batches
    batches = []
    batch = []
    for unit in units:
        if len(_json({**base, 'sources': batch + [unit]}).encode()) > available:
            if batch:
                batches.append({**base, 'sources': batch})
                batch = []
            if len(batches) >= limit:
                break
            if len(_json({**base, 'sources': [unit]}).encode()) > available:
                continue
        batch.append(unit)
    if batch and len(batches) < limit:
        batches.append({**base, 'sources': batch})
    sent = [unit for batch in batches for unit in batch['sources']]
    included = {unit['id'] for unit in sent}
    ranges = {sid: [(u['start'], u['end']) for u in sent if u['id'] == sid] for sid in included}
    truncated = [s['id'] for s, text, _ in readable
                 if s['id'] in included and sum(end - start for start, end in ranges[s['id']]) < len(text)]
    coverage = {
        'selection_method': 'bounded_keyword_windows', 'context_tokens_configured': settings.local_ai_context_tokens,
        'input_budget_utf8_bytes_per_batch': available, 'output_tokens_per_batch': settings.local_ai_max_output_tokens,
        'selected_source_count': len(sources), 'readable_source_count': len(readable),
        'included_source_ids': sorted(included), 'omitted_readable_source_ids': sorted(seen - included),
        'truncated_source_ids': truncated, 'batch_count': len(batches),
        'excerpts': [{k: u[k] for k in ('id', 'start', 'end', 'read_status')} | {
            'sha256': hashlib.sha256(u['excerpt'].encode()).hexdigest()} for u in sent],
        'financial_quality_evaluated': False,
    }
    return batches, coverage


async def synthesize_local(sources, request, horizon_context=None, on_progress=None):
    if settings.ai_provider != 'local':
        raise ProviderError('Local AI is not selected.', 'local_ai_disabled')
    horizon = horizon_context or investment_horizon(request.horizon)
    batches, coverage = make_batches(sources, request, horizon)
    metadata = {'provider': 'local', 'model': settings.local_ai_model, 'coverage': coverage,
                'billing': {'provider': 'local', 'model': settings.local_ai_model,
                            'estimated_cost_usd': 0, 'price_source': 'Local inference; electricity/hardware costs excluded.'},
                'limitations': LIMITATIONS}
    if not batches:
        return {**metadata, 'status': 'unavailable', 'reason': 'No readable source excerpts are available for local analysis.'}
    loop = asyncio.get_running_loop()
    gate = _gates.setdefault(loop, asyncio.Semaphore(1))
    claims = []; conflicts = []; unresolved = []; usage = []; audits = []; response_models = []
    started = time.monotonic()
    async with gate:
        await check_local_model()
        for index, batch in enumerate(batches):
            if on_progress:
                on_progress(f'Local AI: evidence batch {index + 1}/{len(batches)}')
            payload = {
                'model': settings.local_ai_model,
                'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': _json(batch)}],
                'response_format': {'type': 'json_schema', 'json_schema': {
                    'name': 'research', 'strict': True, 'schema': Synthesis.model_json_schema()}},
                'temperature': 0.2, 'max_tokens': settings.local_ai_max_output_tokens, 'stream': False,
            }
            response = await _request('POST', '/chat/completions', payload)
            if isinstance(response.get('model'), str):
                response_models.append(response['model'])
            usage.append(response.get('usage', {}))
            evidence = {}
            for unit in batch['sources']:
                evidence.setdefault(unit['id'], []).append(unit['excerpt'])
            audits.append({'request_sha256': hashlib.sha256(_json(payload).encode()).hexdigest(),
                           'sent_source_ids': sorted(evidence)})
            try:
                choice = response['choices'][0]
                if choice.get('finish_reason') != 'stop' or choice['message'].get('tool_calls'):
                    raise ValueError('Incomplete or tool-bearing response')
                parsed = Synthesis.model_validate_json(choice['message']['content'])
                if not quotes_match(parsed, evidence):
                    raise ValueError('Unmatched quotation')
            except (ValueError, TypeError, KeyError, IndexError):
                return {**metadata, 'status': 'rejected', 'usage': usage, 'request_audit': audits,
                        'reason': 'Local output was incomplete, invalid JSON, or quoted text outside the supplied excerpts. '
                                  'No synthesis was published. Check thinking/output settings if generation was truncated.'}
            claims.extend(parsed.claims); conflicts.extend(parsed.contradictions); unresolved.extend(parsed.unresolved)
    # Merge independent checked batches without inventing an uncited narrative.
    def unique(items, key):
        seen = set(); result = []
        for item in items:
            value = key(item)
            if value not in seen:
                seen.add(value); result.append(item)
        return result
    all_claims = unique(claims, lambda c: (c.source_id, c.evidence_quote, c.side, c.text))
    all_conflicts = unique(conflicts, lambda c: (c.first_source_id, c.first_quote, c.second_source_id, c.second_quote))
    merged = Synthesis(claims=all_claims[:30], contradictions=all_conflicts[:10],
                       unresolved=list(dict.fromkeys(unresolved))[:12])
    coverage['claims_omitted_by_output_limit'] = max(0, len(all_claims) - 30)
    coverage['contradictions_omitted_by_output_limit'] = max(0, len(all_conflicts) - 10)
    return {**metadata, 'status': 'generated_quote_verified', 'data': format_synthesis(merged),
            'usage': usage, 'request_audit': audits, 'response_model_ids': sorted(set(response_models)),
            'duration_seconds': round(time.monotonic() - started, 3)}
