from __future__ import annotations

import bisect
# import operator
import statistics
import threading
import time
from dataclasses import dataclass


@dataclass
class ThreadInfo:
    speed: float
    last_update: float
    last_size: int
    times: list[float]
    speeds: list[float]


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

        self._start_time = time.monotonic()
        self._thread_infos: dict[int, ThreadInfo] = {}
        self._lock = threading.Lock()

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

    def update(self, size):
        with self._lock:
            return self._update(size)

    def _update(self, size):
        current_thread = threading.get_ident()
        thread_info = self._thread_infos.get(current_thread)
        if not thread_info:
            thread_info = ThreadInfo(self._start_time, 0, 0, [], [])
            self._thread_infos[current_thread] = thread_info

        last_size = thread_info.last_size
        if size < last_size:
            chunk = size
        elif size > last_size:
            chunk = size - last_size
        else:
            return
        self.downloaded += chunk
        if self.total and self.downloaded > self.total:
            self._total = self.downloaded
        thread_info.last_size = size

        current_time = time.monotonic()
        self.elapsed = current_time - self._start_time

        last_update = thread_info.last_update
        if current_time - self.UPDATE_TIME <= last_update:
            return
        thread_info.last_update = current_time

        offset = bisect.bisect_left(thread_info.times, current_time - self.WINDOW_SIZE)
        del thread_info.times[:offset]
        del thread_info.speeds[:offset]
        thread_info.times.append(current_time)
        thread_info.speeds.append(size / (current_time - last_update))

        # weights = tuple(1 + (point - current_time) / self.WINDOW_SIZE for point in thread_info.times)
        # Same as `statistics.fmean(self.data_points, weights)`, but weights is >=3.11
        # thread_info.speed = sum(map(operator.mul, thread_info.speeds, weights)) / sum(weights)
        thread_info.speed = statistics.fmean(thread_info.speeds)
        self.speed = sum(info.speed for info in self._thread_infos.values())

        if not self.total:
            self.eta = None
        else:
            self.eta = (self.total - self.downloaded) / self.speed
