from __future__ import annotations

import time
from datetime import timedelta


def time_ms() -> int:
    """Returns the current :py:func:`time.time` as milliseconds."""
    return round(time.time() * 1000)


class Countdown:
    """Utility class for counting down time. Exposes a simple API to initiate
    it with an initial timeout and to check whether is has expired."""

    def __init__(self, init_timeout: timedelta | None):
        if init_timeout is not None:
            self._timeout_ms = int(init_timeout / timedelta(milliseconds=1))
            self._start_time_ms = time_ms()
        else:
            self._timeout_ms = 0
            self._start_time_ms = 0

    @classmethod
    def from_seconds(cls, timeout_seconds: float) -> Countdown:
        return cls(timedelta(seconds=timeout_seconds))

    @classmethod
    def from_millis(cls, timeout_ms: int) -> Countdown:
        return cls(timedelta(milliseconds=timeout_ms))

    @property
    def timeout_ms(self) -> int:
        """Returns timeout as integer milliseconds."""
        return self._timeout_ms

    @property
    def timeout(self) -> timedelta:
        return timedelta(milliseconds=self._timeout_ms)

    @timeout.setter
    def timeout(self, timeout: timedelta) -> None:
        """Set a new timeout for the countdown instance."""
        self._timeout_ms = round(timeout / timedelta(milliseconds=1))

    def timed_out(self) -> bool:
        return round(time_ms() - self._start_time_ms) >= self._timeout_ms

    def busy(self) -> bool:
        return not self.timed_out()

    def reset(self, new_timeout: timedelta | None = None) -> None:
        if new_timeout is not None:
            self.timeout = new_timeout
        self.start()

    def start(self) -> None:
        self._start_time_ms = time_ms()

    def time_out(self) -> None:
        self._start_time_ms = 0

    def remaining_time(self) -> timedelta:
        """Remaining time left."""
        end_time = self._start_time_ms + self._timeout_ms
        current = time_ms()
        if end_time < current:
            return timedelta()
        return timedelta(milliseconds=end_time - current)

    def __repr__(self):
        return f"{self.__class__.__name__}(init_timeout={timedelta(milliseconds=self._timeout_ms)})"

    def __str__(self):
        return (
            f"{self.__class__.__class__} with"
            f" {timedelta(milliseconds=self._timeout_ms)} ms timeout,"
            f" {self.remaining_time()} time remaining"
        )
