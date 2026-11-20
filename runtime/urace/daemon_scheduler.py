"""Daemon scheduling abstraction.

Provides a simple interval-tick model so _daemon.py does not depend on
APScheduler directly. When APScheduler is available it is used for
missed-run handling. Otherwise the stdlib polling loop is used.
"""
from __future__ import annotations

import threading
import time
from typing import Callable


class PollingScheduler:
    """Scheduler backed by a manual time.sleep polling loop."""

    def __init__(self, interval_sec: float, job: Callable[[], None], *, stop_flag: list[bool]) -> None:
        self._interval_sec = max(1.0, interval_sec)
        self._job = job
        self._stop_flag = stop_flag

    def run_blocking(self) -> None:
        while not self._stop_flag[0]:
            self._job()
            if self._stop_flag[0]:
                break
            deadline = time.monotonic() + self._interval_sec
            while time.monotonic() < deadline and not self._stop_flag[0]:
                time.sleep(min(5.0, deadline - time.monotonic()))


class APSchedulerScheduler:
    """Scheduler backed by APScheduler BackgroundScheduler.

    Uses misfire_grace_time so missed cycles are still run once if the
    daemon was delayed (e.g., system sleep). max_instances=1 prevents
    concurrent cycle execution.
    """

    def __init__(self, interval_sec: float, job: Callable[[], None], *, stop_flag: list[bool]) -> None:
        self._interval_sec = max(1.0, interval_sec)
        self._job = job
        self._stop_flag = stop_flag

    def run_blocking(self) -> None:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = BackgroundScheduler()
        trigger = IntervalTrigger(seconds=self._interval_sec)
        scheduler.add_job(
            self._job,
            trigger=trigger,
            max_instances=1,
            misfire_grace_time=int(self._interval_sec),
        )
        scheduler.start()
        try:
            self._job()
            while not self._stop_flag[0]:
                time.sleep(1.0)
        finally:
            scheduler.shutdown(wait=False)


def make_scheduler(
    interval_sec: float,
    job: Callable[[], None],
    *,
    stop_flag: list[bool],
) -> PollingScheduler | APSchedulerScheduler:
    """Return APSchedulerScheduler if available, else PollingScheduler."""
    try:
        import apscheduler  # noqa: F401
        return APSchedulerScheduler(interval_sec=interval_sec, job=job, stop_flag=stop_flag)
    except ImportError:
        return PollingScheduler(interval_sec=interval_sec, job=job, stop_flag=stop_flag)
