from fastapi.testclient import TestClient

from pmoves_yt_service import yt as app_module


def test_summary_endpoint_returns_model_provenance(monkeypatch):
    monkeypatch.setattr(app_module, '_get_transcript', lambda video_id: {'text': 'transcript text', 'segments': []})
    merged = {}
    events = []

    def _record_merge(video_id, patch):
        merged['video_id'] = video_id
        merged['patch'] = patch

    monkeypatch.setattr(app_module, '_merge_video_meta', _record_merge)
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(
        app_module,
        '_resolve_summary_runtime',
        lambda provider: {
            'provider': 'ollama',
            'role': 'creator_summary',
            'model_alias': 'creator_summary_local',
            'model_id': 'qwen3:8b',
        },
    )
    monkeypatch.setattr(app_module, '_summarize_ollama', lambda text, style, model_id: f'{style}:{model_id}:{text}')

    client = TestClient(app_module.app)
    resp = client.post('/yt/summarize', json={'video_id': 'vid-123', 'style': 'short'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['model']['role'] == 'creator_summary'
    assert data['model']['model_alias'] == 'creator_summary_local'
    assert data['model']['model_id'] == 'qwen3:8b'
    assert merged['patch']['model']['model_id'] == 'qwen3:8b'
    assert events[0][0] == 'ingest.summary.ready.v1'
    assert events[0][1]['model_alias'] == 'creator_summary_local'


def test_chapters_endpoint_returns_model_provenance(monkeypatch):
    monkeypatch.setattr(app_module, '_get_transcript', lambda video_id: {'text': 'transcript text', 'segments': []})
    merged = {}
    events = []

    def _record_merge(video_id, patch):
        merged['video_id'] = video_id
        merged['patch'] = patch

    monkeypatch.setattr(app_module, '_merge_video_meta', _record_merge)
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(
        app_module,
        '_resolve_summary_runtime',
        lambda provider: {
            'provider': 'hf',
            'role': 'creator_summary',
            'model_alias': 'creator_summary_hf',
            'model_id': 'google/gemma-2-9b-it',
        },
    )
    monkeypatch.setattr(
        app_module,
        '_summarize_hf',
        lambda text, style, model_id: '[{"title":"Intro","blurb":"Start here"}]',
    )

    client = TestClient(app_module.app)
    resp = client.post('/yt/chapters', json={'video_id': 'vid-456'})
    assert resp.status_code == 200
    data = resp.json()
    assert data['provider'] == 'hf'
    assert data['model']['model_alias'] == 'creator_summary_hf'
    assert data['model']['model_id'] == 'google/gemma-2-9b-it'
    assert merged['patch']['chapters_model']['model_alias'] == 'creator_summary_hf'
    assert events[0][0] == 'ingest.chapters.ready.v1'
    assert events[0][1]['model_id'] == 'google/gemma-2-9b-it'
