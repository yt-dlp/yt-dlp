from pathlib import Path

from core.history import HistoryStore


def test_history_store_saves_searches_and_updates_downloads(tmp_path):
    store = HistoryStore(tmp_path / "history.db")
    download_id = store.add_download(
        title="Example Video",
        url="https://example.com/video",
        output_path="C:/Downloads/example.mp4",
        format_id="best",
        status="running",
    )

    store.finish_download(download_id, "completed")
    results = store.search_downloads("example")

    assert len(results) == 1
    assert results[0]["id"] == download_id
    assert results[0]["title"] == "Example Video"
    assert results[0]["status"] == "completed"


def test_history_store_persists_settings(tmp_path):
    store = HistoryStore(tmp_path / "history.db")

    store.set_setting("output_dir", "C:/Downloads")
    store.set_setting("theme", "system")

    assert store.get_setting("output_dir") == "C:/Downloads"
    assert store.get_settings() == {"output_dir": "C:/Downloads", "theme": "system"}
