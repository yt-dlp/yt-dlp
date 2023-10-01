from __future__ import annotations

import bisect
import operator
import threading
import time


class ProgressCalculator:
    # Time to calculate the speed over (in nanoseconds)
    SAMPLING_WINDOW = 1_000_000_000
    # Time to smooth the speed over (in nanoseconds)
    SMOOTHING_WINDOW = 100_000_000

    def __init__(self, initial: int):
        self.downloaded = initial or 0

        self.elapsed: float = 0
        self.speed: int | None = None
        self.eta: float | None = None

        self._total = None
        self._start_time = time.monotonic_ns()
        self._last_update = self._start_time

        self._lock = threading.Lock()
        self._thread_sizes: dict[int, int] = {}

        self._downloaded = _DataPoints()
        self._downloaded.add_point(self._start_time, self.downloaded)
        self._speeds = _DataPoints()

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value: int | None):
        with self._lock:
            if not value:
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

    def _update(self, size: int):
        current_time = time.monotonic_ns()

        self.downloaded += size
        self.elapsed = (current_time - self._start_time) / 1_000_000_000
        if self.total is not None and self.downloaded > self.total:
            self._total = self.downloaded

        self._downloaded.add_point(current_time, self.downloaded)

        if current_time <= self._last_update:
            return
        self._last_update = current_time

        self._downloaded.trim(current_time - self.SAMPLING_WINDOW)
        download_time, download_bytes = self._downloaded.ranges()
        if not download_time:
            return
        speed = round(download_bytes * 1_000_000_000 / download_time)

        self._speeds.add_point(current_time, speed)
        self._speeds.trim(current_time - self.SMOOTHING_WINDOW)
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
