import os

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.history import HistoryStore
from core.models import DownloadJob
from gui import download_tab as download_tab_module
from gui.download_tab import DownloadTab


class FakeSignal:
    def connect(self, _callback):
        pass


class FakeWorker:
    progress = FakeSignal()
    status = FakeSignal()
    error = FakeSignal()
    finished = FakeSignal()
    canceled = FakeSignal()

    def __init__(self, job, settings):
        self.job = job
        self.settings = settings
        self.started = False

    def start(self):
        self.started = True


def test_download_tab_start_job_starts_worker_without_ui_url_state(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    store = HistoryStore(tmp_path / "data.db")
    monkeypatch.setattr(download_tab_module, "DownloadWorker", FakeWorker)
    tab = DownloadTab(store, lambda: None, lambda job: 1, lambda *_args: None)
    job = DownloadJob(url="https://example.com/video", output_dir=tmp_path, format_id="best", title="Example")

    tab.start_job(job, 1)

    assert isinstance(tab.download_worker, FakeWorker)
    assert tab.download_worker.started is True
    assert store.search_downloads("Example")[0]["status"] == "running"
