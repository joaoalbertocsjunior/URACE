"""Unit tests for the EventBus pub/sub infrastructure."""
import gc
import threading
import unittest

from urace.event_bus import EventBus, _BUS


class EventBusBasicTests(unittest.TestCase):

    def setUp(self):
        self.bus = EventBus()

    # ── subscribe / publish ───────────────────────────────────────────────────

    def test_subscribed_handler_called_on_publish(self):
        called = []
        def handler(**kw):
            called.append(kw)
        self.bus.subscribe('x', handler)
        self.bus.publish('x', value=1)
        self.assertEqual(called, [{'value': 1}])

    def test_no_handlers_publish_is_silent(self):
        self.bus.publish('noop.event')  # must not raise

    def test_multiple_handlers_all_called(self):
        log = []
        def h1(**kw): log.append('h1')
        def h2(**kw): log.append('h2')
        self.bus.subscribe('e', h1)
        self.bus.subscribe('e', h2)
        self.bus.publish('e')
        self.assertEqual(sorted(log), ['h1', 'h2'])

    def test_different_events_isolated(self):
        log = []
        def h(**kw): log.append(kw.get('tag'))
        self.bus.subscribe('a', h)
        self.bus.publish('b', tag='b')
        self.assertEqual(log, [])
        self.bus.publish('a', tag='a')
        self.assertEqual(log, ['a'])

    # ── unsubscribe ───────────────────────────────────────────────────────────

    def test_unsubscribe_stops_delivery(self):
        log = []
        def h(**kw): log.append(1)
        self.bus.subscribe('e', h)
        self.bus.unsubscribe('e', h)
        self.bus.publish('e')
        self.assertEqual(log, [])

    def test_unsubscribe_nonexistent_is_safe(self):
        def h(**kw): pass
        self.bus.unsubscribe('never.subscribed', h)  # must not raise

    # ── weak reference behaviour ──────────────────────────────────────────────

    def test_dead_handler_silently_expires(self):
        log = []
        def make_handler():
            def h(**kw): log.append(1)
            return h
        h = make_handler()
        self.bus.subscribe('e', h)
        del h
        gc.collect()
        self.bus.publish('e')
        self.assertEqual(log, [])  # dead ref — not called

    def test_bound_method_handler_works(self):
        class Listener:
            def __init__(self): self.calls = []
            def on_event(self, **kw): self.calls.append(kw)
        listener = Listener()
        self.bus.subscribe('e', listener.on_event)
        self.bus.publish('e', x=42)
        self.assertEqual(listener.calls, [{'x': 42}])

    def test_bound_method_expires_with_instance(self):
        class Listener:
            def on_event(self, **kw): pass
        listener = Listener()
        self.bus.subscribe('e', listener.on_event)
        del listener
        gc.collect()
        self.bus.publish('e')  # must not raise

    # ── exception isolation ───────────────────────────────────────────────────

    def test_bad_handler_does_not_block_others(self):
        log = []
        def bad(**kw): raise RuntimeError('boom')
        def good(**kw): log.append(1)
        self.bus.subscribe('e', bad)
        self.bus.subscribe('e', good)
        self.bus.publish('e')
        self.assertEqual(log, [1])

    # ── _clear_all ────────────────────────────────────────────────────────────

    def test_clear_all_removes_all_handlers(self):
        log = []
        def h(**kw): log.append(1)
        self.bus.subscribe('a', h)
        self.bus.subscribe('b', h)
        self.bus._clear_all()
        self.bus.publish('a')
        self.bus.publish('b')
        self.assertEqual(log, [])

    # ── thread safety ─────────────────────────────────────────────────────────

    def test_concurrent_publish_and_subscribe_safe(self):
        errors = []
        log = []
        def h(**kw): log.append(1)

        def subscriber():
            try:
                for _ in range(50):
                    self.bus.subscribe('t', h)
            except Exception as exc:
                errors.append(exc)

        def publisher():
            try:
                for _ in range(50):
                    self.bus.publish('t')
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=subscriber) for _ in range(3)]
        threads += [threading.Thread(target=publisher) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(errors, [])


class GlobalBusTests(unittest.TestCase):
    """Smoke-test the module-level _BUS singleton."""

    def tearDown(self):
        _BUS._clear_all()

    def test_global_bus_subscribe_and_publish(self):
        log = []
        def h(**kw): log.append(kw)
        _BUS.subscribe('smoke', h)
        _BUS.publish('smoke', ok=True)
        self.assertEqual(log, [{'ok': True}])


if __name__ == '__main__':
    unittest.main()
