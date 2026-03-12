from pmoves_yt_service import yt as ytmod


def test_with_ytdlp_defaults_uses_modern_client_chain(monkeypatch) -> None:
    monkeypatch.setattr(ytmod, 'YT_PLAYER_CLIENTS', ['default', 'mweb'])
    monkeypatch.setattr(ytmod, 'YT_USER_AGENT', '')

    opts = ytmod._with_ytdlp_defaults({})

    assert opts['extractor_args']['youtube']['player_client'] == ['default', 'mweb']
    assert 'http_headers' not in opts


def test_with_ytdlp_defaults_normalizes_po_token(monkeypatch) -> None:
    monkeypatch.setattr(ytmod, 'YT_PLAYER_CLIENTS', ['web_safari'])
    monkeypatch.setattr(ytmod, 'YT_PO_TOKEN_CONTEXT', '')

    opts = ytmod._with_ytdlp_defaults({}, po_token='token-value')

    assert opts['extractor_args']['youtube']['po_token'] == ['web_safari.gvs+token-value']


def test_normalize_po_token_upgrades_legacy_prefix(monkeypatch) -> None:
    monkeypatch.setattr(ytmod, 'YT_PO_TOKEN_CONTEXT', '')

    normalized = ytmod._normalize_po_token('WEB+legacy-token', ['web_safari'])

    assert normalized == 'web_safari.gvs+legacy-token'
