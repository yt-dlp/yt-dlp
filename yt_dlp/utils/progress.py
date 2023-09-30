from __future__ import annotations

import bisect
import threading
import time

# FIXME: monotonic has terrible resolution on Windows
TIME_PROVIDER = time.perf_counter


# XXX: Fragment resume is not accounted for here
class ProgressCalculator:
    # Time to calculate the average over (in seconds)
    WINDOW_SIZE = 2.0
    # Minimum time before we add another datapoint (in seconds)
    # This is *NOT* the same as the time between a progress change
    UPDATE_TIME = 0.1

    def __init__(self, initial):
        self.downloaded = initial if initial else 0

        self.elapsed = 0
        self.speed = None
        self.eta = None
        self._total = None

        self._lock = threading.Lock()
        self._start_time = TIME_PROVIDER()
        self._last_update = self._start_time

        self._times: list[float] = []
        self._speeds: list[int] = []

        self._thread_updates: dict[int, float] = {}
        self._thread_sizes: dict[int, int] = {}

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value):
        with self._lock:
            if not value or value <= 0.01:
                value = None
            elif value < self.downloaded:
                value = self.downloaded

            self._total = value

    def thread_reset(self):
        current_thread = threading.get_ident()
        with self._lock:
            self._thread_sizes[current_thread] = 0
            self._thread_updates[current_thread] = TIME_PROVIDER()

    def update(self, size: int | None):
        if not size:
            return

        current_thread = threading.get_ident()

        with self._lock:
            current_time = TIME_PROVIDER()
            last_size = self._thread_sizes.get(current_thread) or 0
            last_update = self._thread_updates.get(current_thread) or self._start_time
            chunk = size - last_size
            print(f'    [{threading.get_ident()}] {last_update} -> {current_time} ({chunk}B)')

            update_time = self._update(chunk, current_time, last_update)
            if update_time:
                self._thread_updates[current_thread] = current_time
            self._thread_sizes[current_thread] = size

    def _update(self, size, current_time, last_update):
        self.downloaded += size
        self.elapsed = current_time - self._start_time
        if self.total is not None and self.downloaded > self.total:
            self._total = self.downloaded

        self._times.append(current_time)
        self._speeds.append(size / (current_time - last_update))

        if current_time - self.UPDATE_TIME <= last_update:
            return
        self._last_update = current_time

        offset = bisect.bisect_left(self._times, current_time - self.WINDOW_SIZE)
        del self._times[:offset]
        del self._speeds[:offset]

        weights = tuple(1 + (point - current_time) / self.WINDOW_SIZE for point in self._times)
        # Same as `statistics.fmean(self.data_points, weights)`, but weights is >=3.11
        self.speed = sum(map(float.__mul__, self._speeds, weights)) / sum(weights)

        if not self.total:
            self.eta = None
        else:
            self.eta = (self.total - self.downloaded) / self.speed
