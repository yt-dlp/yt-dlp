from __future__ import annotations

import bisect
import threading
import time


class ProgressCalculator:
    # Time to calculate the speed over (seconds)
    SAMPLING_WINDOW = 3
    # Minimum timeframe before to sample next downloaded bytes (seconds)
    SAMPLING_RATE = 0.05
    # Time before showing eta (seconds)
    GRACE_PERIOD = 1

    def __init__(self, initial: int):
        self._initial = initial or 0
        self.downloaded = self._initial

        self.elapsed: float = 0
        self.speed = SmoothValue(0, smoothing=0.7)
        self.eta = SmoothValue(None, smoothing=0.9)

        self._total = 0
        self._start_time = time.monotonic()
        self._last_update = self._start_time

        self._lock = threading.Lock()
        self._thread_sizes: dict[int, int] = {}

        self._times = [self._start_time]
        self._downloaded = [self.downloaded]

    @property
    def total(self):
        return self._total

    @total.setter
    def total(self, value: int | None):
        with self._lock:
            if value is not None and value < self.downloaded:
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
        current_time = time.monotonic()

        self.downloaded += size
        self.elapsed = current_time - self._start_time
        if self.total is not None and self.downloaded > self.total:
            self._total = self.downloaded

        if self._last_update + self.SAMPLING_RATE > current_time:
            return
        self._last_update = current_time

        self._times.append(current_time)
        self._downloaded.append(self.downloaded)

        offset = bisect.bisect_left(self._times, current_time - self.SAMPLING_WINDOW)
        del self._times[:offset]
        del self._downloaded[:offset]
        if len(self._times) < 2:
            self.speed.reset()
            self.eta.reset()
            return

        download_time = current_time - self._times[0]
        if not download_time:
            return

        self.speed.set((self.downloaded - self._downloaded[0]) / download_time)
        if self.total and self.speed.value and self.elapsed > self.GRACE_PERIOD:
            self.eta.set((self.total - self.downloaded) / self.speed.value)
        else:
            self.eta.reset()


class SmoothValue:
    def __init__(self, initial: float | None, smoothing: float):
        self.value = self.smooth = self._initial = initial
        self._smoothing = smoothing

    def set(self, value: float):
        self.value = value
        if self.smooth is None:
            self.smooth = self.value
        else:
            self.smooth = (1 - self._smoothing) * value + self._smoothing * self.smooth

    def reset(self):
        self.value = self.smooth = self._initial
