from pathlib import Path

from core.downloader import DownloadWorker
from core.models import DownloadJob


def test_download_worker_progress_hook_emits_percent_speed_and_eta():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="best",
    )
    worker = DownloadWorker(job, youtube_dl_factory=lambda _opts: None)
    events = []
    worker.progress.connect(events.append)

    worker._progress_hook(
        {
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes": 200,
            "speed": 1024,
            "eta": 30,
            "filename": "example.mp4",
        }
    )

    assert events == [{"percent": 25.0, "speed": 1024, "eta": 30, "filename": "example.mp4"}]


def test_download_worker_finished_hook_emits_status_message():
    job = DownloadJob(
        url="https://example.com/video",
        output_dir=Path("C:/Downloads"),
        format_id="best",
    )
    worker = DownloadWorker(job, youtube_dl_factory=lambda _opts: None)
    statuses = []
    worker.status.connect(statuses.append)

    worker._progress_hook({"status": "finished", "filename": "example.mp4"})

    assert statuses == ["Finished downloading example.mp4; post-processing if needed."]
