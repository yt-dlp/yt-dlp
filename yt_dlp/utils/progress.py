from __future__ import annotations

import bisect
import threading
import time


class ProgressCalculator:
    # Time to calculate the speed over (seconds)
    SAMPLING_WINDOW = 3
    # Minimum timeframe before to sample next downloaded bytes (seconds)
    SAMPLING_RATE = 0.05
    # Time until we show smoothed speed and eta (seconds)
    GRACE_PERIOD = 1
    # Smoothing factor for the speed EMA (from 0 = prev to 1 = current)
    SPEED_SMOOTHING = 0.3
    # Smoothing factor for the ETA EMA (from 0 = prev to 1 = current)
    ETA_SMOOTHING = 0.1

    def __init__(self, initial: int):
        self._initial = initial or 0
        self.downloaded = self._initial

        self.elapsed: float = 0
        self.speed: float = 0
        self.smooth_speed: float = 0
        self.eta: float | None = None
        self.smooth_eta: float | None = None

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
            self.speed = self.smooth_speed = 0
            self.eta = self.smooth_eta = None
            return

        download_time = current_time - self._times[0]
        if not download_time:
            return

        self.speed = (self.downloaded - self._downloaded[0]) / download_time
        if self.elapsed < self.GRACE_PERIOD:
            self.smooth_speed = self.speed
            return

        self.smooth_speed = self.SPEED_SMOOTHING * self.speed + (1 - self.SPEED_SMOOTHING) * self.smooth_speed

        if self.total and self.speed:
            self.eta = (self.total - self.downloaded) / self.speed
            if not self.smooth_eta:
                self.smooth_eta = self.eta
            else:
                self.smooth_eta = self.ETA_SMOOTHING * self.eta + (1 - self.ETA_SMOOTHING) * self.smooth_eta
        else:
            self.eta = None
            self.smooth_eta = None
