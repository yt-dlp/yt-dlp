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


def test_download_worker_keeps_completed_file_when_postprocess_raises(tmp_path):
    completed_file = tmp_path / "movie.mp4"
    completed_file.write_bytes(b"ok")

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def download(self, _urls):
            self.opts["progress_hooks"][0]({
                "status": "finished",
                "filename": str(completed_file),
            })
            raise RuntimeError("ERROR: Postprocessing: Error opening output files: Invalid argument")

    job = DownloadJob(
        url="https://streamimdb.ru/embed/movie/tt15940132",
        output_dir=tmp_path,
        format_id="best",
    )
    worker = DownloadWorker(job, youtube_dl_factory=FakeYDL)
    finished_events = []
    errors = []
    worker.finished.connect(finished_events.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert finished_events == [{
        "url": "https://streamimdb.ru/embed/movie/tt15940132",
        "title": "",
        "filename": str(completed_file),
        "warning": "ERROR: Postprocessing: Error opening output files: Invalid argument",
    }]


def test_download_worker_keeps_finished_download_when_postprocess_file_is_renamed(tmp_path):
    missing_file = tmp_path / "missing.mp4"

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def download(self, _urls):
            self.opts["progress_hooks"][0]({
                "status": "finished",
                "filename": str(missing_file),
            })
            raise RuntimeError("ERROR: Postprocessing: Error opening output files: Invalid argument")

    job = DownloadJob(
        url="https://streamimdb.ru/embed/movie/tt15940132",
        output_dir=tmp_path,
        format_id="best",
    )
    worker = DownloadWorker(job, youtube_dl_factory=FakeYDL)
    finished_events = []
    errors = []
    worker.finished.connect(finished_events.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert finished_events == [{
        "url": "https://streamimdb.ru/embed/movie/tt15940132",
        "title": "",
        "filename": str(missing_file),
        "warning": "ERROR: Postprocessing: Error opening output files: Invalid argument",
    }]


def test_download_worker_errors_when_non_postprocess_failure_happens_after_finished(tmp_path):
    missing_file = tmp_path / "missing.mp4"

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def download(self, _urls):
            self.opts["progress_hooks"][0]({
                "status": "finished",
                "filename": str(missing_file),
            })
            raise RuntimeError("network cleanup failed")

    job = DownloadJob(
        url="https://streamimdb.ru/embed/movie/tt15940132",
        output_dir=tmp_path,
        format_id="best",
    )
    worker = DownloadWorker(job, youtube_dl_factory=FakeYDL)
    finished_events = []
    errors = []
    worker.finished.connect(finished_events.append)
    worker.error.connect(errors.append)

    worker.run()

    assert finished_events == []
    assert errors == ["network cleanup failed"]
