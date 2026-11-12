import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from urace import inputs as inp


def _item(kind, payload, iid="input-001", at="2024-01-01T00:00:00+00:00"):
 return {"id": iid, "at": at, "kind": kind, "payload": payload}


def _fresh_state():
 return {"objectives": [], "processed_input_ids": [], "evidence": []}


def _fresh_config():
 return {}


class HandleContextTests(unittest.TestCase):
 def test_appends_to_context_inputs(self):
  state = _fresh_state()
  item = _item("context", {"text": "hello"})
  inp._handle_context(item, item["payload"], _fresh_config(), state)
  self.assertEqual(len(state["context_inputs"]), 1)
  self.assertEqual(state["context_inputs"][0]["id"], "input-001")

 def test_sets_discovery_trigger(self):
  state = _fresh_state()
  item = _item("context", {"text": "hello"})
  inp._handle_context(item, item["payload"], _fresh_config(), state)
  self.assertIn("discovery_trigger", state["executor_state"])

 def test_caps_at_200_entries(self):
  state = _fresh_state()
  state["context_inputs"] = [{"id": f"c{i}"} for i in range(200)]
  item = _item("context", {"text": "new"})
  inp._handle_context(item, item["payload"], _fresh_config(), state)
  self.assertEqual(len(state["context_inputs"]), 200)


class HandleGoalTests(unittest.TestCase):
 def test_appends_objective(self):
  state = _fresh_state()
  payload = {"title": "Improve speed", "success_measure": "p50 < 100ms"}
  item = _item("goal", payload)
  inp._handle_goal(item, payload, _fresh_config(), state)
  self.assertEqual(len(state["objectives"]), 1)
  obj = state["objectives"][0]
  self.assertEqual(obj["title"], "Improve speed")
  self.assertEqual(obj["status"], "planned")

 def test_scope_is_runtime_when_target_urace(self):
  state = _fresh_state()
  payload = {"title": "Runtime goal", "success_measure": "runs", "target": "urace"}
  item = _item("goal", payload)
  inp._handle_goal(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["scope"], "runtime")

 def test_scope_is_documentation_when_target_product(self):
  state = _fresh_state()
  payload = {"title": "Doc goal", "success_measure": "published"}
  item = _item("goal", payload)
  inp._handle_goal(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["scope"], "documentation")

 def test_authority_basis_is_set(self):
  state = _fresh_state()
  payload = {"title": "T", "success_measure": "M"}
  item = _item("goal", payload)
  inp._handle_goal(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["authority_basis"], "authoritative queued user input")


class HandleGoalControlTests(unittest.TestCase):
 def _state_with_goal(self, status="planned"):
  return {
   "objectives": [{"id": "goal-1", "status": status, "title": "T",
                   "success_measure": "M"}],
   "processed_input_ids": [],
   "evidence": [],
  }

 def test_cancel_planned_goal(self):
  state = self._state_with_goal("planned")
  payload = {"id": "goal-1", "action": "cancel"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["status"], "cancelled")

 def test_disable_goal(self):
  state = self._state_with_goal("planned")
  payload = {"id": "goal-1", "action": "disable"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["status"], "disabled")

 def test_resume_deferred_goal(self):
  state = self._state_with_goal("deferred")
  payload = {"id": "goal-1", "action": "resume"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["status"], "planned")

 def test_pin_goal(self):
  state = self._state_with_goal("planned")
  payload = {"id": "goal-1", "action": "pin"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertTrue(state["objectives"][0]["pinned"])

 def test_unpin_goal(self):
  state = self._state_with_goal("planned")
  state["objectives"][0]["pinned"] = True
  payload = {"id": "goal-1", "action": "unpin"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertFalse(state["objectives"][0]["pinned"])

 def test_prioritize_goal(self):
  state = self._state_with_goal("planned")
  payload = {"id": "goal-1", "action": "prioritize", "priority": 90}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["priority"], 90)

 def test_delete_goal(self):
  state = self._state_with_goal("planned")
  payload = {"id": "goal-1", "action": "delete"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertEqual(state["objectives"][0]["status"], "deleted")

 def test_missing_goal_adds_rejection_evidence(self):
  state = {"objectives": [], "processed_input_ids": [], "evidence": []}
  payload = {"id": "nonexistent", "action": "cancel"}
  item = _item("goal_control", payload)
  result = inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertFalse(result)
  self.assertTrue(any(e["kind"] == "authoritative-input-rejected" for e in state["evidence"]))

 def test_control_history_recorded(self):
  state = self._state_with_goal("planned")
  payload = {"id": "goal-1", "action": "disable"}
  item = _item("goal_control", payload)
  inp._handle_goal_control(item, payload, _fresh_config(), state)
  self.assertTrue(len(state["objectives"][0]["control_history"]) >= 1)


class HandleSourceTests(unittest.TestCase):
 def test_json_file_source_configured(self):
  state = _fresh_state()
  payload = {"id": "src-1", "kind": "json_file", "path": "/tmp/x.json"}
  item = _item("source", payload)
  inp._handle_source(item, payload, _fresh_config(), state)
  sources = state["connector_sources"]
  self.assertEqual(len(sources), 1)
  self.assertEqual(sources[0]["status"], "CONFIGURED")

 def test_unsupported_kind_gets_adapter_required(self):
  state = _fresh_state()
  payload = {"id": "src-2", "kind": "kafka_stream"}
  item = _item("source", payload)
  inp._handle_source(item, payload, _fresh_config(), state)
  self.assertEqual(state["connector_sources"][0]["status"], "ADAPTER_REQUIRED")

 def test_replace_existing_source_by_id(self):
  state = {"connector_sources": [{"id": "src-1", "kind": "json_file", "status": "CONFIGURED"}],
           "objectives": [], "processed_input_ids": [], "evidence": []}
  payload = {"id": "src-1", "kind": "json_file", "path": "/new/path.json"}
  item = _item("source", payload)
  inp._handle_source(item, payload, _fresh_config(), state)
  self.assertEqual(len(state["connector_sources"]), 1)


class HandleMetricTests(unittest.TestCase):
 def test_metric_definition_added(self):
  state = _fresh_state()
  payload = {"name": "accuracy", "path": "$.accuracy", "source": "src-1"}
  item = _item("metric", payload)
  inp._handle_metric(item, payload, _fresh_config(), state)
  defs = state["metric_definitions"]
  self.assertEqual(len(defs), 1)
  self.assertEqual(defs[0]["name"], "accuracy")

 def test_metric_replaces_existing_same_name(self):
  state = _fresh_state()
  state["metric_definitions"] = [{"name": "accuracy", "path": "$.old"}]
  payload = {"name": "accuracy", "path": "$.new"}
  item = _item("metric", payload)
  inp._handle_metric(item, payload, _fresh_config(), state)
  self.assertEqual(len(state["metric_definitions"]), 1)
  self.assertEqual(state["metric_definitions"][0]["path"], "$.new")


class HandleMetricControlTests(unittest.TestCase):
 def test_removes_metric_definition(self):
  state = {**_fresh_state(), "metric_definitions": [{"name": "accuracy"}],
           "connector_sources": []}
  payload = {"name": "accuracy"}
  item = _item("metric_control", payload)
  inp._handle_metric_control(item, payload, _fresh_config(), state)
  self.assertEqual(state["metric_definitions"], [])


class HandleEvidenceTests(unittest.TestCase):
 def test_evidence_appended(self):
  state = _fresh_state()
  payload = {"kind": "operator-submitted", "summary": "looks good"}
  item = _item("evidence", payload)
  inp._handle_evidence(item, payload, _fresh_config(), state)
  self.assertEqual(len(state["evidence"]), 1)
  self.assertEqual(state["evidence"][0]["summary"], "looks good")


class ConsumeInputsTests(unittest.TestCase):
 def _make_config(self, td):
  """Return a minimal config that makes input_directory() point to td/inbox."""
  inbox = Path(td) / "inbox"
  inbox.mkdir(exist_ok=True)
  state_file = Path(td) / "state.json"
  state_file.write_text("{}")
  return {"state_path": str(state_file)}

 def _write_input(self, inbox_dir, kind, payload, iid=None, at=None):
  import uuid
  iid = iid or f"input-{uuid.uuid4()}"
  at = at or "2024-01-01T00:00:00+00:00"
  item = {"id": iid, "at": at, "kind": kind, "payload": payload}
  path = inbox_dir / f"{at.replace(':', '-')}-{iid}.json"
  path.write_text(json.dumps(item))
  return iid

 def test_consumes_valid_input(self):
  with tempfile.TemporaryDirectory() as td:
   config = self._make_config(td)
   inbox = Path(td) / "inbox"
   state = _fresh_state()
   iid = self._write_input(inbox, "context", {"text": "hello"})
   consumed = inp.consume_inputs(config, state)
   self.assertEqual(len(consumed), 1)
   self.assertIn(iid, state["processed_input_ids"])

 def test_skips_already_processed(self):
  with tempfile.TemporaryDirectory() as td:
   config = self._make_config(td)
   inbox = Path(td) / "inbox"
   state = _fresh_state()
   self._write_input(inbox, "context", {"text": "hello"}, iid="dup-id")
   state["processed_input_ids"].append("dup-id")
   consumed = inp.consume_inputs(config, state)
   self.assertEqual(len(consumed), 1)
   self.assertEqual(len(state.get("context_inputs", [])), 0)

 def test_unsupported_kind_adds_rejection_evidence(self):
  with tempfile.TemporaryDirectory() as td:
   config = self._make_config(td)
   inbox = Path(td) / "inbox"
   state = _fresh_state()
   self._write_input(inbox, "unknown_kind_xyz", {})
   inp.consume_inputs(config, state)
   kinds = [e["kind"] for e in state["evidence"]]
   self.assertIn("authoritative-input-rejected", kinds)

 def test_malformed_json_is_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   config = self._make_config(td)
   inbox = Path(td) / "inbox"
   state = _fresh_state()
   bad = inbox / "bad.json"
   bad.write_text("{not valid json")
   inp.consume_inputs(config, state)
   # malformed file renamed to .rejected — should not raise
   self.assertFalse(bad.exists())

 def test_tier0_control_processed_first(self):
  with tempfile.TemporaryDirectory() as td:
   config = self._make_config(td)
   inbox = Path(td) / "inbox"
   state = _fresh_state()
   # Write a standard context input with an earlier timestamp
   self._write_input(inbox, "context", {"text": "standard"},
                     iid="id-std", at="2024-01-01T00:00:01+00:00")
   # Write a tier-0 control (pause) with a later timestamp
   ctrl = {"id": "id-ctrl", "at": "2024-01-01T00:00:02+00:00",
           "kind": "control", "payload": {"action": "pause"},
           "priority_tier": 0}
   (inbox / "ctrl.json").write_text(json.dumps(ctrl))
   with patch("urace.inputs._INPUT_HANDLERS", {
    "control": lambda *a: True,
    "context": lambda i, p, c, s: s.setdefault("context_inputs", []).append({"id": i["id"]}) or True,
   }):
    inp.consume_inputs(config, state)
   order = state["processed_input_ids"]
   self.assertLess(order.index("id-ctrl"), order.index("id-std"))


class QueueInputTests(unittest.TestCase):
 def test_queues_to_directory(self):
  with tempfile.TemporaryDirectory() as td:
   state_file = Path(td) / "state.json"
   state_file.write_text("{}")
   config = {"state_path": str(state_file)}
   result = inp.queue_input(config, "context", {"text": "queued"})
   self.assertIn("id", result)
   inbox = Path(td) / "inbox"
   files = list(inbox.glob("*.json"))
   self.assertEqual(len(files), 1)
   data = json.loads(files[0].read_text())
   self.assertEqual(data["kind"], "context")


if __name__ == "__main__":
 unittest.main()
