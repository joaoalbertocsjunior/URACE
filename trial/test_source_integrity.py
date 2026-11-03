import copy,json,tempfile,unittest
from pathlib import Path
from source_integrity import descriptor,matches
class IntegrityTests(unittest.TestCase):
 def test_only_controls_mutable(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"config.json";base={"authority":{"delegated":[]},"executor":{"enabled":False},"resources":{"max_tokens":100}}
   p.write_text(json.dumps(base));frozen=descriptor(p)
   changed=copy.deepcopy(base);changed.update(auto_goals={"enabled":False,"replenish_backlog":True});changed["resources"].update(effort="high",executor_effort={"codex":"low"});changed["executor"]["native_options"]={"codex":{"model":"example","native_effort":"high"}}
   p.write_text(json.dumps(changed));self.assertTrue(matches(p,frozen))
   changed["executor"]["enabled"]=True;p.write_text(json.dumps(changed));self.assertTrue(matches(p,frozen))
   for key,value in (("command","arbitrary"),):
    c=copy.deepcopy(changed);c["executor"][key]=value;p.write_text(json.dumps(c));self.assertFalse(matches(p,frozen))
   changed["resources"]["max_tokens"]=101;p.write_text(json.dumps(changed));self.assertFalse(matches(p,frozen))
 def test_invalid_control_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"config.json";p.write_text("{}");frozen=descriptor(p)
   for c in ({"auto_goals":{"enabled":"yes"}},{"resources":{"effort":"unlimited"}},{"executor":{"native_options":{"codex":{"command":"other"}}}}):
    p.write_text(json.dumps(c));self.assertFalse(matches(p,frozen))
