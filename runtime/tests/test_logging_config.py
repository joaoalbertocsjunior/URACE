"""Phase IV-A — logging_config tests."""
import json
import logging
import unittest


class GetLoggerTests(unittest.TestCase):
    def test_returns_logger_instance(self):
        from urace.logging_config import get_logger
        log = get_logger("urace.test_module")
        self.assertIsInstance(log, logging.Logger)
        self.assertEqual(log.name, "urace.test_module")

    def test_same_name_returns_same_instance(self):
        from urace.logging_config import get_logger
        a = get_logger("urace.same")
        b = get_logger("urace.same")
        self.assertIs(a, b)


class JsonFormatterTests(unittest.TestCase):
    def _record(self, msg="hello", level=logging.WARNING, name="urace.x"):
        record = logging.LogRecord(
            name=name, level=level, pathname="", lineno=0,
            msg=msg, args=(), exc_info=None,
        )
        return record

    def test_produces_valid_json(self):
        from urace.logging_config import JsonFormatter
        fmt = JsonFormatter()
        line = fmt.format(self._record())
        obj = json.loads(line)
        self.assertIn("ts", obj)
        self.assertIn("level", obj)
        self.assertIn("logger", obj)
        self.assertIn("msg", obj)

    def test_level_field_matches(self):
        from urace.logging_config import JsonFormatter
        fmt = JsonFormatter()
        obj = json.loads(fmt.format(self._record(level=logging.ERROR)))
        self.assertEqual(obj["level"], "ERROR")

    def test_msg_field_contains_message(self):
        from urace.logging_config import JsonFormatter
        fmt = JsonFormatter()
        obj = json.loads(fmt.format(self._record(msg="test message")))
        self.assertEqual(obj["msg"], "test message")


class ConfigureLoggingTests(unittest.TestCase):
    def setUp(self):
        self._root = logging.getLogger()
        self._original_handlers = list(self._root.handlers)
        for h in list(self._root.handlers):
            self._root.removeHandler(h)

    def tearDown(self):
        for h in list(self._root.handlers):
            self._root.removeHandler(h)
        for h in self._original_handlers:
            self._root.addHandler(h)

    def test_adds_handler_to_root(self):
        from urace.logging_config import configure_logging
        configure_logging()
        self.assertGreater(len(self._root.handlers), 0)

    def test_second_call_is_noop(self):
        from urace.logging_config import configure_logging
        configure_logging()
        n = len(self._root.handlers)
        configure_logging()
        self.assertEqual(len(self._root.handlers), n)

    def test_json_format_installs_json_formatter(self):
        from urace.logging_config import configure_logging, JsonFormatter
        configure_logging(json_format=True)
        handler = self._root.handlers[0]
        self.assertIsInstance(handler.formatter, JsonFormatter)
