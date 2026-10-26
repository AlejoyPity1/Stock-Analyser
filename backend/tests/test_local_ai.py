"""Controlled transport tests. These never call the user's PC or a paid provider."""
import asyncio
import json
import time

import httpx
import pytest

from app.config import Settings, settings
from app.horizon import investment_horizon
from app.local_ai import local_base_url, make_batches, synthesize_local
from app.providers import ProviderError
from app.research import ResearchRequest, synthesize

TEXT = 'Revenue increased from 100 million to 110 million. Management has not provided guidance.'
SOURCES = [{'id': 'fixture-source', 'title': 'CONTROLLED TEST ONLY', 'text': TEXT, 'read_status': 'read'}]


def answer(quote=TEXT, source_id='fixture-source'):
    return {'claims': [{'side': 'neutral', 'kind': 'reported_fact',
                        'text': 'The source reports higher revenue.', 'source_id': source_id,
                        'evidence_quote': quote, 'financial_mechanism': 'Review revenue persistence; no valuation change.'}],
            'unresolved': ['What guidance will management provide?'], 'contradictions': []}


@pytest.fixture
def local(client, monkeypatch):
    monkeypatch.setattr(settings, 'ai_provider', 'local')
    monkeypatch.setattr(settings, 'local_ai_base_url', 'http://127.0.0.1:1234/v1')
    monkeypatch.setattr(settings, 'local_ai_model', 'qwen/qwen3.5-9b')
    return client


def mock_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    def factory(**kwargs):
        assert kwargs['trust_env'] is False
        assert kwargs['follow_redirects'] is False
        return original(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(httpx, 'AsyncClient', factory)


def directory():
    return httpx.Response(200, json={'data': [{'id': 'text-embedding-nomic-embed-text-v1.5'},
                                            {'id': 'qwen/qwen3.5-9b'}]})


def completion(data=None, **overrides):
    return httpx.Response(200, json={'model': 'qwen3.5-9b', 'usage': {'prompt_tokens': 100, 'completion_tokens': 80},
                                    'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(data or answer())}}],
                                    **overrides})


@pytest.mark.parametrize('url', [
    'https://api.openai.com/v1', 'http://169.254.169.254:1234/v1',
    'http://127.0.0.1.evil.example:1234/v1', 'http://user:secret@127.0.0.1:1234/v1',
    'http://127.0.0.1:1234/v1?secret=abc', 'http://127.0.0.1:1234/v1#x',
    'http://127.0.0.1:80/v1', 'http://localhost:1234/elsewhere', 'http://localhost:1234/\nv1',
])
def test_only_literal_loopback_model_endpoint_is_accepted(url):
    with pytest.raises(ProviderError):
        local_base_url(url)
    with pytest.raises(ValueError):
        Settings(_env_file=None, local_ai_base_url=url)


def test_localhost_is_normalized_without_dns():
    assert local_base_url('http://localhost:1234/v1/') == 'http://127.0.0.1:1234/v1'
    assert local_base_url('http://[::1]:1234/v1') == 'http://[::1]:1234/v1'


@pytest.mark.asyncio
async def test_local_ai_works_with_paid_ai_blocked_and_uses_exact_model(local, monkeypatch):
    monkeypatch.setattr(settings, 'research_api_key', 'paid-key-must-not-leak')
    seen = []; horizon = investment_horizon('3m', '2026-01-31T12:00:00Z')
    def handler(request):
        assert request.url.host == '127.0.0.1'
        assert 'authorization' not in request.headers
        seen.append(request)
        if request.method == 'GET': return directory()
        payload = json.loads(request.content)
        assert payload['model'] == 'qwen/qwen3.5-9b'
        assert payload['response_format']['json_schema']['strict'] is True
        assert 'tools' not in payload and 'mcps' not in payload
        assert 'Write in English' in payload['messages'][0]['content']
        context = json.loads(payload['messages'][1]['content'])['investment_horizon']
        assert context['as_of'] == horizon['as_of']
        assert context['window_end_date'] == horizon['window_end_date']
        return completion()
    mock_transport(monkeypatch, handler)
    result = await synthesize(SOURCES, ResearchRequest(symbol='TEST', horizon='3m', use_ai=True), horizon)
    assert result['status'] == 'generated_quote_verified'
    assert result['data']['used_source_ids'] == ['fixture-source']
    assert result['billing']['estimated_cost_usd'] == 0
    assert result['provider'] == 'local' and len(seen) == 2
    assert 'paid-key-must-not-leak' not in json.dumps(result)


@pytest.mark.asyncio
@pytest.mark.parametrize('failure', ['quote', 'source', 'length', 'json', 'tool_calls', 'empty_choices', 'cross_batch_quote'])
async def test_invalid_or_unseen_citations_are_not_published(local, monkeypatch, failure):
    def handler(request):
        if request.method == 'GET': return directory()
        data = answer()
        if failure == 'quote': data = answer('This sentence was never supplied to the model.')
        if failure == 'source': data = answer(source_id='invented-source')
        if failure == 'cross_batch_quote': data = answer('Unique end-of-document statement about revenue.')
        choice = {'finish_reason': 'stop', 'message': {'content': json.dumps(data)}}
        if failure == 'length': choice['finish_reason'] = 'length'
        if failure == 'json': choice['message']['content'] = '```json\nnot JSON\n```'
        if failure == 'tool_calls': choice['message']['tool_calls'] = [{'function': {'name': 'buy'}}]
        return completion(choices=[] if failure == 'empty_choices' else [choice])
    mock_transport(monkeypatch, handler)
    sources = SOURCES if failure != 'cross_batch_quote' else [
        {**SOURCES[0], 'text': TEXT * 200 + 'Unique end-of-document statement about revenue.'}]
    result = await synthesize_local(sources, ResearchRequest(symbol='TEST', use_ai=True))
    assert result['status'] == 'rejected'
    assert 'data' not in result


@pytest.mark.asyncio
@pytest.mark.parametrize('status,code', [(401, 'local_ai_http_error'), (302, 'local_ai_http_error'), (500, 'local_ai_http_error')])
async def test_local_errors_and_redirects_never_fall_back_to_paid_api(local, monkeypatch, status, code):
    monkeypatch.setattr(settings, 'paid_ai_enabled', True)
    calls = []
    def handler(request):
        calls.append(str(request.url))
        assert request.url.host == '127.0.0.1'
        return httpx.Response(status, headers={'location': 'https://api.openai.com/v1/responses'})
    mock_transport(monkeypatch, handler)
    with pytest.raises(ProviderError) as error:
        await synthesize(SOURCES, ResearchRequest(symbol='TEST', use_ai=True))
    assert error.value.code == code and len(calls) == 1


@pytest.mark.asyncio
async def test_timeout_has_actionable_error_and_no_retry(local, monkeypatch):
    def handler(request): raise httpx.ReadTimeout('controlled timeout')
    mock_transport(monkeypatch, handler)
    with pytest.raises(ProviderError) as error:
        await synthesize_local(SOURCES, ResearchRequest(symbol='TEST'))
    assert error.value.code == 'local_ai_timeout'


def test_connection_check_uses_the_chat_model_and_does_not_claim_inference(local, monkeypatch):
    mock_transport(monkeypatch, lambda request: directory())
    response = local.post('/settings/local-ai/check', json={})
    assert response.status_code == 200
    assert response.json()['model'] == 'qwen/qwen3.5-9b'
    assert response.json()['inference_verified'] is False


def test_embedding_model_does_not_satisfy_chat_model_check(local, monkeypatch):
    mock_transport(monkeypatch, lambda request: httpx.Response(200, json={'data': [{'id': 'text-embedding-nomic-embed-text-v1.5'}]}))
    response = local.post('/settings/local-ai/check', json={})
    assert response.status_code == 503 and response.json()['code'] == 'local_ai_model_missing'


def test_local_secret_never_returned_by_settings(local, monkeypatch):
    monkeypatch.setattr(settings, 'local_ai_api_key', 'secret-local-token')
    response = local.get('/settings')
    assert 'secret-local-token' not in response.text
    assert response.json()['providers']['local']['enabled'] is True
    assert response.json()['providers']['openai']['enabled'] is False


def test_unreachable_configuration_is_not_probed_when_disabled(client, monkeypatch):
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: pytest.fail('Disabled provider must not make a request'))
    response = client.post('/settings/local-ai/check', json={})
    assert response.status_code == 503 and response.json()['code'] == 'local_ai_disabled'


def test_batching_bounds_utf8_context_and_discloses_omissions(local, monkeypatch):
    monkeypatch.setattr(settings, 'local_ai_quick_batches', 1)
    sources = [{**SOURCES[0], 'id': str(i), 'text': 'Revenue and cash flow. 中文é 💶 ' * 1000} for i in range(20)]
    sources.append({'id': 'inaccessible', 'title': 'Unread', 'text': TEXT, 'read_status': 'inaccessible'})
    request = ResearchRequest(symbol='TEST')
    batches, coverage = make_batches(sources, request, investment_horizon())
    assert len(batches) == 1 and coverage['omitted_readable_source_ids']
    assert coverage['truncated_source_ids'] and 'inaccessible' not in coverage['included_source_ids']
    for batch in batches:
        encoded = json.dumps(batch, ensure_ascii=False, separators=(',', ':')).encode()
        assert len(encoded) <= coverage['input_budget_utf8_bytes_per_batch']
        for unit in batch['sources']:
            original = next(s['text'] for s in sources if s['id'] == unit['id'])
            assert unit['excerpt'] == original[unit['start']:unit['end']]


@pytest.mark.asyncio
async def test_local_inference_is_serialized_for_single_gpu(local, monkeypatch):
    active = 0; peak = 0
    async def handler(request):
        nonlocal active, peak
        if request.method == 'GET': return directory()
        active += 1; peak = max(peak, active)
        try:
            await asyncio.sleep(.01)
            return completion()
        finally: active -= 1
    mock_transport(monkeypatch, handler)
    results = await asyncio.gather(*(synthesize_local(SOURCES, ResearchRequest(symbol='TEST')) for _ in range(2)))
    assert peak == 1 and all(r['status'] == 'generated_quote_verified' for r in results)


def test_research_endpoint_saves_local_analysis_and_exports_quotes(local, monkeypatch):
    from app.providers import sec, market
    async def company(symbol): return {'symbol': symbol, 'name': 'Controlled local AI fixture', 'currency': 'USD', 'filings': [], 'statements': []}
    async def quote(symbol): raise ProviderError('Controlled fixture has no market quote')
    async def news(*args): return [{**SOURCES[0], 'read_status': 'abstract_only', 'publisher': 'Controlled fixture', 'url': 'https://example.org/test', 'full_text': False}]
    monkeypatch.setattr(sec, 'company', company); monkeypatch.setattr(market, 'quote', quote); monkeypatch.setattr(market, 'news', news)
    mock_transport(monkeypatch, lambda request: directory() if request.method == 'GET' else completion())
    response = local.post('/research', json={'symbol': 'TEST', 'use_ai': True, 'horizon': '3m'})
    assert response.status_code == 202
    identifier = response.json()['id']
    for _ in range(100):
        job = local.get('/records/' + identifier).json()
        if job['status'] not in ('queued', 'running'): break
        time.sleep(.01)
    assert job['ai']['status'] == 'generated_quote_verified'
    assert job['ai']['provider'] == 'local' and job['stats']['used_for_synthesis'] == 1
    report = local.get('/reports/' + identifier).json()
    assert report['record']['ai']['coverage']['included_source_ids'] == ['fixture-source']
    pdf = local.get('/reports/' + identifier + '/pdf')
    from io import BytesIO
    from pypdf import PdfReader
    text = '\n'.join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    assert 'fixture-source' in text and TEXT in ' '.join(text.split())
