"""Phase II-E — daemon_scheduler tests with mocked clock."""
import threading
import time
import unittest


class PollingSchedulerTests(unittest.TestCase):
    def test_job_called_once_then_stops(self):
        from urace.daemon_scheduler import PollingScheduler
        calls = []
        stopped = [False]

        def job():
            calls.append(1)
            stopped[0] = True

        sched = PollingScheduler(interval_sec=0.1, job=job, stop_flag=stopped)
        sched.run_blocking()
        self.assertEqual(len(calls), 1)

    def test_job_called_multiple_times(self):
        from urace.daemon_scheduler import PollingScheduler
        calls = []
        stopped = [False]

        def job():
            calls.append(1)
            if len(calls) >= 3:
                stopped[0] = True

        sched = PollingScheduler(interval_sec=0.05, job=job, stop_flag=stopped)
        sched.run_blocking()
        self.assertGreaterEqual(len(calls), 3)

    def test_stop_flag_prevents_next_run(self):
        from urace.daemon_scheduler import PollingScheduler
        calls = []
        stopped = [True]  # pre-stopped

        def job():
            calls.append(1)

        sched = PollingScheduler(interval_sec=0.01, job=job, stop_flag=stopped)
        sched.run_blocking()
        self.assertEqual(len(calls), 0)


class MakeSchedulerTests(unittest.TestCase):
    def test_make_scheduler_returns_apscheduler_when_available(self):
        from urace.daemon_scheduler import make_scheduler, APSchedulerScheduler
        try:
            import apscheduler  # noqa: F401
        except ImportError:
            self.skipTest("apscheduler not installed")
        sched = make_scheduler(60.0, lambda: None, stop_flag=[False])
        self.assertIsInstance(sched, APSchedulerScheduler)

    def test_make_scheduler_returns_polling_fallback(self):
        from urace.daemon_scheduler import make_scheduler, PollingScheduler
        from unittest.mock import patch
        with patch.dict("sys.modules", {"apscheduler": None}):
            sched = make_scheduler(60.0, lambda: None, stop_flag=[False])
        self.assertIsInstance(sched, PollingScheduler)


class APSchedulerSchedulerTests(unittest.TestCase):
    def test_job_runs_immediately_then_stops(self):
        try:
            import apscheduler  # noqa: F401
        except ImportError:
            self.skipTest("apscheduler not installed")

        from urace.daemon_scheduler import APSchedulerScheduler
        calls = []
        stopped = [False]

        def job():
            calls.append(1)
            stopped[0] = True

        sched = APSchedulerScheduler(interval_sec=60.0, job=job, stop_flag=stopped)
        t = threading.Thread(target=sched.run_blocking, daemon=True)
        t.start()
        t.join(timeout=5.0)
        self.assertGreaterEqual(len(calls), 1)
