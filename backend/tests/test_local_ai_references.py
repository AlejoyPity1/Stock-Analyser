import importlib.util
import json
from pathlib import Path

import pytest

from app.config import settings
from app.horizon import investment_horizon
from app.local_ai import _parse_completion, synthesize_local
from app.research import ResearchRequest
from app.store import get, now, put, records
from test_local_ai import TEXT, SOURCES, completion, directory, evidence_answer, local, mock_transport

spec = importlib.util.spec_from_file_location('reanalyze_local_ai', Path(__file__).resolve().parents[2] / 'scripts/reanalyze_local_ai.py')
reanalysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reanalysis)


@pytest.mark.asyncio
async def test_references_preserve_original_spaces_punctuation_and_table_text(local, monkeypatch):
    original = 'On July\u00a030, 2026, Apple\u00a0Inc. (\u201cApple\u201d) issued a press release regarding Apple\u2019s financial results. Net income 29,789 23,434.'
    def handler(request):
        if request.method == 'GET': return directory()
        payload = json.loads(request.content)
        batch = json.loads(payload['messages'][1]['content'])
        assert batch['sources'][0]['excerpt'] == original
        schema = payload['response_format']['json_schema']['schema']
        claim = schema['$defs']['EvidenceClaim']
        assert claim['properties']['evidence_id']['enum'] == ['E1']
        assert 'evidence_quote' not in claim['properties']
        return completion(evidence_answer('E1'))
    mock_transport(monkeypatch, handler)
    result = await synthesize_local([{**SOURCES[0], 'text': original}], ResearchRequest(symbol='TEST', use_ai=True))
    assert result['status'] == 'generated_quote_verified'
    assert result['data']['claims'][0]['evidence_quote'] == original
    assert result['data']['claims'][0]['source_id'] == 'fixture-source'
    assert result['request_audit'][0]['selected_evidence_ids'] == ['E1']
    assert result['coverage']['citation_method'] == 'server_copied_evidence_ids'


@pytest.mark.parametrize('same_source', [True, False])
def test_two_window_ids_cannot_turn_one_source_into_a_cross_source_contradiction(same_source):
    references = {'E1': {'id': 'first', 'excerpt': TEXT},
                  'E2': {'id': 'first' if same_source else 'second', 'excerpt': 'Management provided a different guidance statement.'}}
    data = {'claims': [], 'unresolved': [], 'contradictions': [
        {'description': 'Potential difference requiring review.', 'first_evidence_id': 'E1', 'second_evidence_id': 'E2'}]}
    parsed, rejection = _parse_completion(completion(data).json(), references)
    if same_source:
        assert parsed is None and rejection['code'] == 'local_ai_invalid_contradiction'
    else:
        assert rejection is None
        assert parsed.synthesis.contradictions[0].first_quote == TEXT
        assert parsed.synthesis.contradictions[0].second_source_id == 'second'


@pytest.mark.asyncio
@pytest.mark.parametrize('valid', [True, False])
async def test_reanalysis_adds_a_new_version_only_after_full_validation(local, monkeypatch, valid):
    mock_transport(monkeypatch, lambda request: directory() if request.method == 'GET'
                   else completion(evidence_answer('E1' if valid else 'E999')))
    timestamp = now()
    request = ResearchRequest(symbol='TEST', use_ai=True)
    original = {'id': 'original-real-source-fixture', 'symbol': 'TEST', 'status': 'completed',
                'created_at': timestamp, 'updated_at': timestamp, 'request': request.model_dump(),
                'investment_horizon': investment_horizon('3-6m', timestamp), 'sources': SOURCES,
                'stats': {'selected': 1, 'used_for_synthesis': 0}, 'ai': {'status': 'rejected'}}
    put(original['id'], 'research', 'TEST', original)
    result = await reanalysis.reanalyze(record_id=original['id'])
    assert get(original['id']) == original
    assert result['passed'] is valid and result['paid_api_calls'] == 0
    assert result['source_retrieval_calls'] == 0
    if valid:
        fresh = get(result['new_record_id'])
        assert fresh['id'] != original['id'] and fresh['sources'] == original['sources']
        assert fresh['investment_horizon'] == original['investment_horizon']
        assert fresh['reanalysis']['of_record_id'] == original['id']
        assert fresh['ai']['data']['claims'][0]['evidence_quote'] == TEXT
        assert fresh['stats']['used_for_synthesis'] == 1
    else:
        assert len(records('research', 'TEST')) == 1


@pytest.mark.asyncio
async def test_reanalysis_rejects_disabled_provider_without_any_inference(client, monkeypatch):
    monkeypatch.setattr(settings, 'ai_provider', 'disabled')
    from app.providers import ProviderError
    with pytest.raises(ProviderError) as error:
        await reanalysis.reanalyze()
    assert error.value.code == 'local_ai_disabled'
