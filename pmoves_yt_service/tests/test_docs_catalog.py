from fastapi.testclient import TestClient

from pmoves_yt_service import yt as app_module
from pmoves_yt_service.docs_sync import collect_yt_dlp_docs


def test_docs_catalog_endpoint_smoke():
    client = TestClient(app_module.app)
    resp = client.get('/yt/docs/catalog')
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('ok') is True
    assert data['meta']['yt_dlp_version'] != 'unknown'
    assert data['meta']['extractor_count'] > 0
    assert data['counts']['options'] > 0


def test_docs_sync_collects_real_version():
    data = collect_yt_dlp_docs()
    assert data['version'] != 'unknown'


def test_docs_sync_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setenv('YT_DOCS_SYNC_ON_START', 'false')
    monkeypatch.setenv('VALID_API_KEYS', 'test-key')
    monkeypatch.setenv('YT_DOCS_SYNC_MIN_INTERVAL_SECONDS', '0')
    monkeypatch.setattr(app_module, 'collect_yt_dlp_docs', lambda: {'version': '2026.02.04', 'help_cli': 'help'})
    monkeypatch.setattr(app_module, 'sync_to_supabase', lambda docs: {'status': 'ok', 'count': 1, 'version': docs['version']})

    client = TestClient(app_module.app)
    monkeypatch.setattr(app_module, '_docs_sync_last_request_ts', 0.0)
    assert client.post('/yt/docs/sync').status_code == 401
    authed = client.post('/yt/docs/sync', headers={'X-API-Key': 'test-key'})
    assert authed.status_code == 200
    assert authed.json()['ok'] is True


def test_docs_sync_rate_limits_repeated_requests(monkeypatch):
    monkeypatch.setenv('YT_DOCS_SYNC_ON_START', 'false')
    monkeypatch.setenv('VALID_API_KEYS', 'test-key')
    monkeypatch.setenv('YT_DOCS_SYNC_MIN_INTERVAL_SECONDS', '60')
    monkeypatch.setattr(app_module, 'collect_yt_dlp_docs', lambda: {'version': '2026.02.04', 'help_cli': 'help'})
    monkeypatch.setattr(app_module, 'sync_to_supabase', lambda docs: {'status': 'ok', 'count': 1, 'version': docs['version']})
    monkeypatch.setattr(app_module.time, 'monotonic', lambda: 1000.0)

    client = TestClient(app_module.app)
    monkeypatch.setattr(app_module, '_docs_sync_last_request_ts', 0.0)
    assert client.post('/yt/docs/sync', headers={'X-API-Key': 'test-key'}).status_code == 200
    assert client.post('/yt/docs/sync', headers={'X-API-Key': 'test-key'}).status_code == 429
