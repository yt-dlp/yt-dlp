from fastapi.testclient import TestClient

from pmoves_yt_service import yt as app_module


def test_playlist_add_returns_preview_by_default(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/add',
        json={
            'playlist_id': 'PL123',
            'video_id': 'vid-123',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'preview'
    assert data['action'] == 'playlist_add'
    assert data['details']['playlist_id'] == 'PL123'
    assert events[0][0] == 'creator.youtube.control.preview.v1'
    assert audits[0]['status'] == 'preview'
    assert audits[0]['action'] == 'playlist_add'


def test_playlist_create_returns_preview_by_default(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/create',
        json={
            'title': 'PMOVES Creator Queue',
            'description': 'Owned channel review queue',
            'privacy_status': 'unlisted',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'preview'
    assert data['action'] == 'playlist_create'
    assert data['details']['title'] == 'PMOVES Creator Queue'
    assert data['details']['privacy_status'] == 'unlisted'
    assert events[0][0] == 'creator.youtube.control.preview.v1'
    assert audits[0]['status'] == 'preview'
    assert audits[0]['action'] == 'playlist_create'


def test_playlist_update_returns_preview_by_default(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/update',
        json={
            'playlist_id': 'PL123',
            'title': 'PMOVES Creator Queue',
            'privacy_status': 'unlisted',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'preview'
    assert data['action'] == 'playlist_update'
    assert data['details']['playlist_id'] == 'PL123'
    assert data['details']['title'] == 'PMOVES Creator Queue'
    assert events[0][0] == 'creator.youtube.control.preview.v1'
    assert audits[0]['status'] == 'preview'
    assert audits[0]['action'] == 'playlist_update'


def test_playlist_update_requires_mutable_fields():
    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/update',
        json={
            'playlist_id': 'PL123',
        },
    )

    assert resp.status_code == 400
    assert resp.json()['detail'] == 'playlist_update requires at least one mutable field'


def test_playlist_delete_returns_preview_by_default(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/delete',
        json={
            'playlist_id': 'PL123',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'preview'
    assert data['action'] == 'playlist_delete'
    assert data['details']['playlist_id'] == 'PL123'
    assert events[0][0] == 'creator.youtube.control.preview.v1'
    assert audits[0]['status'] == 'preview'
    assert audits[0]['action'] == 'playlist_delete'


def test_playlist_add_execute_requires_approval(monkeypatch):
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/add',
        json={
            'playlist_id': 'PL123',
            'video_id': 'vid-123',
            'execute': True,
        },
    )

    assert resp.status_code == 400
    assert resp.json()['detail'] == 'approved_by is required when execute=true'


def test_playlist_create_execute_uses_youtube_control_runtime(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'create_playlist',
        lambda **kwargs: {'id': 'PLNEW123', 'snippet': {'title': kwargs['title']}, 'status': {'privacyStatus': kwargs['privacy_status']}},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/create',
        json={
            'title': 'PMOVES Creator Queue',
            'description': 'Owned channel review queue',
            'privacy_status': 'private',
            'execute': True,
            'approved_by': 'discord-agent',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'playlist_create'
    assert data['result']['id'] == 'PLNEW123'
    assert events[0][0] == 'creator.youtube.control.executed.v1'
    assert audits[0]['status'] == 'executed'
    assert audits[0]['action'] == 'playlist_create'


def test_playlist_update_execute_uses_youtube_control_runtime(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'update_playlist',
        lambda **kwargs: {'id': kwargs['playlist_id'], 'status': {'privacyStatus': kwargs['privacy_status']}},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/update',
        json={
            'playlist_id': 'PL123',
            'title': 'Updated Queue',
            'privacy_status': 'private',
            'execute': True,
            'approved_by': 'discord-agent',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'playlist_update'
    assert data['result']['id'] == 'PL123'
    assert events[0][0] == 'creator.youtube.control.executed.v1'
    assert audits[0]['status'] == 'executed'
    assert audits[0]['action'] == 'playlist_update'


def test_playlist_delete_execute_uses_youtube_control_runtime(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'delete_playlist',
        lambda **kwargs: {'id': kwargs['playlist_id'], 'deleted': True},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/delete',
        json={
            'playlist_id': 'PL123',
            'execute': True,
            'approved_by': 'discord-agent',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'playlist_delete'
    assert data['result']['id'] == 'PL123'
    assert data['result']['deleted'] is True
    assert events[0][0] == 'creator.youtube.control.executed.v1'
    assert audits[0]['status'] == 'executed'
    assert audits[0]['action'] == 'playlist_delete'


def test_playlist_remove_returns_preview_by_default(monkeypatch):
    audits = []
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/remove',
        json={
            'playlist_item_id': 'PLI123',
            'playlist_id': 'PL123',
            'video_id': 'vid-123',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'preview'
    assert data['action'] == 'playlist_remove'
    assert data['details']['playlist_item_id'] == 'PLI123'
    assert audits[0]['action'] == 'playlist_remove'


def test_playlist_reorder_execute_uses_youtube_control_runtime(monkeypatch):
    audits = []
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'update_playlist_item_position',
        lambda **kwargs: {'id': kwargs['playlist_item_id'], 'snippet': {'position': kwargs['position']}},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/playlist/reorder',
        json={
            'playlist_item_id': 'PLI123',
            'playlist_id': 'PL123',
            'video_id': 'vid-123',
            'position': 4,
            'execute': True,
            'approved_by': 'discord-agent',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'playlist_reorder'
    assert data['result']['id'] == 'PLI123'
    assert data['result']['snippet']['position'] == 4
    assert audits[0]['action'] == 'playlist_reorder'
    assert audits[0]['status'] == 'executed'


def test_comment_execute_uses_youtube_control_runtime(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'insert_comment',
        lambda **kwargs: {'id': 'comment-1', 'snippet': {'videoId': kwargs['video_id']}},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/comment',
        json={
            'video_id': 'vid-123',
            'text': 'Thanks for the video',
            'execute': True,
            'approved_by': 'discord-agent',
            'approval_note': 'networking follow-up',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'comment_create'
    assert data['result']['id'] == 'comment-1'
    assert events[0][0] == 'creator.youtube.control.executed.v1'
    assert audits[0]['status'] == 'executed'
    assert audits[0]['action'] == 'comment_create'


def test_reply_execute_uses_youtube_control_runtime(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'insert_comment',
        lambda **kwargs: {'id': 'reply-1', 'snippet': {'parentId': kwargs['parent_comment_id']}},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/comment',
        json={
            'video_id': 'vid-123',
            'parent_comment_id': 'comment-parent-1',
            'text': 'Replying with a PMOVES follow-up',
            'execute': True,
            'approved_by': 'discord-agent',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'comment_create'
    assert data['details']['parent_comment_id'] == 'comment-parent-1'
    assert data['result']['id'] == 'reply-1'
    assert events[0][0] == 'creator.youtube.control.executed.v1'
    assert audits[0]['status'] == 'executed'
    assert audits[0]['action'] == 'comment_create'


def test_comment_delete_returns_preview_by_default(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/comment/delete',
        json={
            'comment_id': 'comment-1',
            'video_id': 'vid-123',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'preview'
    assert data['action'] == 'comment_delete'
    assert data['details']['comment_id'] == 'comment-1'
    assert events[0][0] == 'creator.youtube.control.preview.v1'
    assert audits[0]['status'] == 'preview'
    assert audits[0]['action'] == 'comment_delete'


def test_comment_delete_execute_uses_youtube_control_runtime(monkeypatch):
    events = []
    audits = []
    monkeypatch.setattr(app_module, '_publish_event', lambda topic, payload: events.append((topic, payload)))
    monkeypatch.setattr(app_module, '_record_control_action', lambda **kwargs: audits.append(kwargs))
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_ID', 'client-id')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_CLIENT_SECRET', 'client-secret')
    monkeypatch.setattr(app_module, 'YT_GOOGLE_REFRESH_TOKEN', 'refresh-token')
    monkeypatch.setattr(app_module, 'YT_CONTROL_REQUIRE_APPROVAL', True)
    monkeypatch.setattr(app_module, 'refresh_access_token', lambda **kwargs: 'access-token')
    monkeypatch.setattr(
        app_module,
        'delete_comment',
        lambda **kwargs: {'id': kwargs['comment_id'], 'deleted': True},
    )

    client = TestClient(app_module.app)
    resp = client.post(
        '/yt/control/comment/delete',
        json={
            'comment_id': 'comment-1',
            'video_id': 'vid-123',
            'execute': True,
            'approved_by': 'discord-agent',
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'executed'
    assert data['action'] == 'comment_delete'
    assert data['result']['id'] == 'comment-1'
    assert data['result']['deleted'] is True
    assert events[0][0] == 'creator.youtube.control.executed.v1'
    assert audits[0]['status'] == 'executed'
    assert audits[0]['action'] == 'comment_delete'
