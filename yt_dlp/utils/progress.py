from __future__ import annotations

import bisect
import operator
import threading
import time


class ProgressCalculator:
    # Time to calculate the speed over (in nanoseconds)
    WINDOW_SIZE = 1_000_000_000
    # Time to smooth the speed over (in nanoseconds)
    SPEED_WINDOW = 1_000_000_000

    def __init__(self, initial):
        self.downloaded = initial or 0

        self.elapsed = 0
        self.speed = None
        self.eta = None

        self._total = None
        self._start_time = time.monotonic_ns()
        self._last_update = self._start_time

        self._lock = threading.Lock()
        self._thread_sizes: dict[int, int] = {}

        self._downloaded = _DataPoints()
        self._speeds = _DataPoints()

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

    def update(self, size: int | None):
        if not size:
            return

        current_thread = threading.get_ident()

        with self._lock:
            last_size = self._thread_sizes.get(current_thread, 0)
            self._thread_sizes[current_thread] = size
            self._update(size - last_size)

    def _update(self, size):
        current_time = time.monotonic_ns()

        self.downloaded += size
        self.elapsed = current_time - self._start_time
        if self.total is not None and self.downloaded > self.total:
            self._total = self.downloaded

        self._downloaded.add_point(current_time, self.downloaded)

        if current_time <= self._last_update:
            return
        self._last_update = current_time

        self._downloaded.trim(current_time - self.WINDOW_SIZE)
        download_time, download_bytes = self._downloaded.ranges()
        if not download_time:
            return
        speed = round(download_bytes * 1_000_000_000 / download_time)

        self._speeds.add_point(current_time, speed)
        self._speeds.trim(current_time - self.SPEED_WINDOW)
        speed_time = self._speeds.ranges()[0] or 1

        weights = tuple(1 + (point - current_time) / speed_time for point in self._speeds.times)
        # Same as `statistics.fmean(self.data_points, weights)`, but weights is >=3.11
        self.speed = int(sum(map(operator.mul, self._speeds.values, weights)) / sum(weights))

        if not self.total:
            self.eta = None
        elif self.speed:
            self.eta = (self.total - self.downloaded) / self.speed


class _DataPoints:
    def __init__(self):
        self.times: list[int] = []
        self.values: list[int] = []

    def add_point(self, time: int, value: int):
        """Add a point to the dataset"""
        self.times.append(time)
        self.values.append(value)

    def trim(self, start_time: int):
        """Remove expired data points"""
        offset = bisect.bisect_left(self.times, start_time)
        del self.times[:offset]
        del self.values[:offset]

        return offset

    def ranges(self):
        """Return the range of both the time and data"""
        if not self.times:
            return 0, 0

        return self.times[-1] - self.times[0], self.values[-1] - self.values[0]

    def __len__(self):
        return len(self.times)
