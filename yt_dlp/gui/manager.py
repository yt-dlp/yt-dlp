"""Background download workers for the graphical interface"""

from __future__ import annotations

import dataclasses
import functools
import itertools
import queue
import threading

from ..utils import DownloadCancelled, DownloadError, format_bytes
from ..YoutubeDL import YoutubeDL


class Status:
    """The states a queued download goes through"""

    PENDING = 'Pending'
    DOWNLOADING = 'Downloading'
    PROCESSING = 'Processing'
    FINISHED = 'Finished'
    CANCELLED = 'Cancelled'
    ERROR = 'Error'

    ACTIVE = (DOWNLOADING, PROCESSING)
    DONE = (FINISHED, CANCELLED, ERROR)


@dataclasses.dataclass
class Task:
    """A single queued download, owned by the manager and mirrored by the interface"""

    task_id: int
    url: str
    title: str = ''
    status: str = Status.PENDING
    progress: float = 0.0
    speed: str = ''
    eta: str = ''
    size: str = ''
    message: str = ''
    filepath: str = ''
    params: dict = dataclasses.field(default_factory=dict, repr=False)
    cancelled: threading.Event = dataclasses.field(default_factory=threading.Event)

    def snapshot(self):
        """@returns the displayable state of the task"""
        return {
            'task_id': self.task_id,
            'url': self.url,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'eta': self.eta,
            'size': self.size,
            'message': self.message,
            'filepath': self.filepath,
        }


def format_eta(seconds):
    """@returns `seconds` as [H:]MM:SS, or an empty string when unknown"""
    if seconds is None:
        return ''
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f'{hours}:{minutes:02d}:{seconds:02d}'
    return f'{minutes}:{seconds:02d}'


def format_speed(speed):
    """@returns `speed` in bytes per second as a human readable rate"""
    if not speed:
        return ''
    return f'{format_bytes(speed)}/s'


class TaskLogger:
    """Forwards the messages of a single download to the interface"""

    def __init__(self, report, task):
        self._report = report
        self._task = task

    def debug(self, message):
        if message.startswith('[debug] '):
            self._report(self._task, 'debug', message)
        else:
            self.info(message)

    def info(self, message):
        self._report(self._task, 'info', message)

    def warning(self, message):
        self._report(self._task, 'warning', message)

    def error(self, message):
        self._report(self._task, 'error', message)


class DownloadManager:
    """Runs the queued downloads on a pool of threads

    Progress is never pushed to the widgets directly; every change is published
    on `events` so that the interface can consume it from the main thread.
    """

    def __init__(self, events, workers=2):
        self.events = events
        self._workers = max(1, int(workers))
        self._pending = queue.Queue()
        self._tasks = {}
        self._threads = []
        self._ids = itertools.count(1)
        self._lock = threading.Lock()
        self._shutdown = threading.Event()

    @property
    def tasks(self):
        with self._lock:
            return list(self._tasks.values())

    def set_concurrency(self, workers):
        """Set how many downloads may run at once; a lower limit frees idle workers"""
        with self._lock:
            self._workers = max(1, int(workers))

    def submit(self, url, params):
        """Queue `url` with the `YoutubeDL` `params` it must run with"""
        with self._lock:
            task = Task(task_id=next(self._ids), url=url, params=dict(params))
            self._tasks[task.task_id] = task
        self._publish(task)
        self._pending.put(task)
        self._ensure_workers()
        return task

    def cancel(self, task_id):
        """Request the cancellation of a queued or running download"""
        with self._lock:
            task = self._tasks.get(task_id)
        if task and task.status not in Status.DONE:
            task.cancelled.set()

    def cancel_all(self):
        for task in self.tasks:
            self.cancel(task.task_id)

    def forget(self, task_id):
        """Drop a finished task; running ones are kept until they stop"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status in Status.DONE:
                del self._tasks[task_id]
                return True
        return False

    def counts(self):
        """@returns the amount of (queued, running, finished) downloads"""
        queued = running = done = 0
        for task in self.tasks:
            if task.status == Status.PENDING:
                queued += 1
            elif task.status in Status.ACTIVE:
                running += 1
            else:
                done += 1
        return queued, running, done

    def shutdown(self):
        """Cancel everything and let the worker threads exit"""
        self._shutdown.set()
        self.cancel_all()

    def _ensure_workers(self):
        with self._lock:
            missing = self._workers - len(self._threads)
            for _ in range(max(0, missing)):
                index = len(self._threads)
                thread = threading.Thread(
                    target=self._work, args=(index,), name=f'yt-dlp-gui-{index}', daemon=True)
                self._threads.append(thread)
                thread.start()

    def _work(self, index):
        while not self._shutdown.is_set():
            if index >= self._workers:
                break
            try:
                task = self._pending.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                self._download(task)
            finally:
                self._pending.task_done()
        with self._lock:
            if index < len(self._threads):
                self._threads.pop()

    def _download(self, task):
        if task.cancelled.is_set() or self._shutdown.is_set():
            self._update(task, status=Status.CANCELLED, message='Cancelled before starting')
            return

        params = dict(task.params)
        params.update({
            'progress_hooks': [functools.partial(self._progress_hook, task)],
            'postprocessor_hooks': [functools.partial(self._postprocessor_hook, task)],
            'logger': TaskLogger(self._log, task),
        })

        self._update(task, status=Status.DOWNLOADING, message='')
        try:
            with YoutubeDL(params) as ydl:
                ydl.download([task.url])
        except DownloadCancelled:
            self._update(task, status=Status.CANCELLED, message='Cancelled', speed='', eta='')
        except DownloadError as error:
            self._update(task, status=Status.ERROR, message=str(error), speed='', eta='')
        except Exception as error:
            self._log(task, 'error', str(error))
            self._update(task, status=Status.ERROR, message=str(error), speed='', eta='')
        else:
            self._update(task, status=Status.FINISHED, progress=100.0, speed='', eta='', message='')

    def _abort_if_cancelled(self, task):
        if task.cancelled.is_set() or self._shutdown.is_set():
            raise DownloadCancelled

    def _progress_hook(self, task, status):
        self._abort_if_cancelled(task)
        state = status.get('status')
        if state == 'downloading':
            total = status.get('total_bytes') or status.get('total_bytes_estimate')
            downloaded = status.get('downloaded_bytes') or 0
            self._update(
                task,
                status=Status.DOWNLOADING,
                progress=downloaded / total * 100 if total else 0.0,
                speed=format_speed(status.get('speed')),
                eta=format_eta(status.get('eta')),
                size=format_bytes(total) if total else '',
                title=self._title_of(status) or task.title)
        elif state == 'finished':
            self._update(
                task, status=Status.PROCESSING, progress=100.0, speed='', eta='',
                filepath=status.get('filename') or task.filepath)
        elif state == 'error':
            self._update(task, status=Status.ERROR, message='The download failed')

    def _postprocessor_hook(self, task, status):
        self._abort_if_cancelled(task)
        if status.get('status') == 'started':
            self._update(
                task, status=Status.PROCESSING,
                message=status.get('postprocessor') or '',
                title=self._title_of(status) or task.title)

    @staticmethod
    def _title_of(status):
        info = status.get('info_dict') or {}
        return info.get('title') or ''

    def _log(self, task, level, message):
        self.events.put({
            'type': 'log',
            'task_id': task.task_id,
            'level': level,
            'message': message,
        })

    def _update(self, task, **fields):
        for name, value in fields.items():
            setattr(task, name, value)
        self._publish(task)

    def _publish(self, task):
        self.events.put({'type': 'state', **task.snapshot()})
