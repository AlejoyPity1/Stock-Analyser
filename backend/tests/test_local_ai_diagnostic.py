"""The replay diagnoses saved evidence; it never changes a report or relaxes quote checks."""
import importlib.util
import json
from pathlib import Path

import pytest

from app.horizon import investment_horizon
from app.local_ai import synthesize_local
from app.research import ResearchRequest
from app.store import get, put
from test_local_ai import SOURCES, TEXT, answer, completion, directory, local, mock_transport

spec = importlib.util.spec_from_file_location('diagnose_local_ai', Path(__file__).resolve().parents[2] / 'scripts/diagnose_local_ai.py')
diagnostic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostic)


def test_whitespace_only_quote_difference_stays_rejected():
    evidence = {'fixture-source': [TEXT.replace('100 million', '100\u00a0million')]}
    result = diagnostic.inspect_response(completion().json(), evidence)
    assert result['passed'] is False and result['code'] == 'local_ai_unmatched_quote'
    mismatch = result['unverified_quote_mismatches'][0]
    assert mismatch['whitespace_normalized_match'] is True
    assert mismatch['source_was_supplied'] is True


def test_schema_errors_do_not_echo_raw_response_or_private_reasoning():
    raw = completion({'claims': 'RAW MODEL CONTENT MUST NOT BE ECHOED'}).json()
    raw['choices'][0]['message']['reasoning_content'] = 'PRIVATE INTERNAL REASONING'
    result = diagnostic.inspect_response(raw, {'fixture-source': [TEXT]})
    assert result['code'] == 'local_ai_invalid_synthesis'
    assert result['schema_errors'][0]['path'] == ['claims']
    assert 'RAW MODEL CONTENT' not in json.dumps(result)
    assert 'PRIVATE INTERNAL REASONING' not in json.dumps(result)


@pytest.mark.asyncio
async def test_replay_uses_identical_saved_batch_without_mutating_record_or_fetching_sources(local, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.host == '127.0.0.1'
        return directory() if request.method == 'GET' else completion()
    mock_transport(monkeypatch, handler)
    request = ResearchRequest(symbol='TEST', use_ai=True)
    horizon = investment_horizon('3-6m', '2026-10-26T12:00:00Z')
    result = await synthesize_local(SOURCES, request, horizon)
    saved = {'id': 'controlled-diagnostic', 'symbol': 'TEST', 'status': 'completed',
             'request': request.model_dump(), 'investment_horizon': horizon, 'sources': SOURCES, 'ai': result}
    put(saved['id'], 'research', 'TEST', saved)
    before = get(saved['id'])
    replay = await diagnostic.diagnose_saved('TEST')
    assert replay['passed'] is True
    assert replay['same_payload_as_original_first_batch'] is True
    assert replay['research_record_modified'] is False and get(saved['id']) == before
    assert replay['source_retrieval_calls'] == 0 and replay['paid_api_calls'] == 0
    assert len(calls) == 4  # Model listing + inference, once for each execution.
