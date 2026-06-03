import os

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from core.models import DownloadJob
from gui.queue_tab import QueueTab


def test_queue_tab_exposes_management_flow(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    tab = QueueTab()
    job = DownloadJob(url="https://example.com/video", output_dir=tmp_path, format_id="best", title="Example")

    started = []
    paused = []
    tab.start_requested.connect(lambda queue_id, queued_job: started.append((queue_id, queued_job)))
    tab.pause_requested.connect(paused.append)

    queue_id = tab.add_job(job)
    tab.table.selectRow(0)

    tab.start_selected()
    assert started == [(queue_id, job)]

    tab.update_job(queue_id, "RUN", 42)
    tab.pause_selected()
    assert paused == [queue_id]

    tab.update_job(queue_id, "PAUSED", 42)
    tab.resume_selected()
    assert started[-1] == (queue_id, job)

    tab.update_job(queue_id, "DONE", 100)
    tab.remove_selected()
    assert tab.table.rowCount() == 0
    assert tab.items == {}
