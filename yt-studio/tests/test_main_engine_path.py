from main import resolve_ytdlp_source


def test_resolves_repo_engine_when_app_lives_inside_yt_dlp_checkout(tmp_path):
    app_root = tmp_path / "yt-studio"
    engine_pkg = tmp_path / "yt_dlp"
    app_root.mkdir()
    engine_pkg.mkdir()

    assert resolve_ytdlp_source(app_root) == tmp_path


def test_resolves_sibling_publish_checkout_for_standalone_app(tmp_path):
    app_root = tmp_path / "yt-studio"
    engine_pkg = tmp_path / "yt-dlp-publish" / "yt_dlp"
    app_root.mkdir()
    engine_pkg.mkdir(parents=True)

    assert resolve_ytdlp_source(app_root) == tmp_path / "yt-dlp-publish"


def test_resolves_bundled_release_engine_for_original_workspace(tmp_path):
    app_root = tmp_path / "yt-studio"
    engine_root = tmp_path / "yt-dlp-2026.03.17" / "yt-dlp-2026.03.17"
    app_root.mkdir()
    (engine_root / "yt_dlp").mkdir(parents=True)

    assert resolve_ytdlp_source(app_root) == engine_root
