from __future__ import annotations

from pmoves_yt_service import docs_sync


class _Response:
    def __init__(self, status_code: int = 200, body: list[dict] | None = None):
        self.status_code = status_code
        self._body = body if body is not None else []
        self.ok = 200 <= status_code < 300
        self.text = ''

    def json(self):
        return self._body


def test_sync_to_supabase_url_encodes_on_conflict(monkeypatch):
    calls: list[str] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        return _Response()

    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'service-role')
    monkeypatch.setattr('pmoves_yt_service.docs_sync.requests.post', fake_post)

    out = docs_sync.sync_to_supabase(
        {
            'version': '2026.02.04',
            'help_cli': 'help',
            'extractors': 'extractors',
            'user_agent': 'ua',
        },
    )

    assert out['status'] == 'ok'
    assert calls
    assert any('on_conflict=tool%2Cversion%2Cdoc_type' in call for call in calls)
