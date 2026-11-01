import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli,_common,user_controls,executor
class UserControlsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/"config.json"
  self.path.write_text(json.dumps({"executor":{"providers":[{"id":"codex","adapter":"codex-cli"},{"id":"claude","adapter":"claude-cli"}]}}))
 def runcli(self,*args):
  with patch.object(cli,"CONFIG_PATH",self.path),patch.object(_common,"CONFIG_PATH",self.path),contextlib.redirect_stdout(io.StringIO()) as output:
   self.assertEqual(cli.main(list(args)),0)
  return json.loads(output.getvalue())
 def config(self):return json.loads(self.path.read_text())
 def test_grouped_help_and_invalid_arguments(self):
  with contextlib.redirect_stdout(io.StringIO()) as out:
   with self.assertRaises(SystemExit) as result:cli.main(["configuration","--help"])
   self.assertEqual(result.exception.code,0)
  self.assertIn("configuration executor",out.getvalue())
  before=self.path.read_bytes()
  with patch.object(cli,"CONFIG_PATH",self.path),patch.object(_common,"CONFIG_PATH",self.path),contextlib.redirect_stderr(io.StringIO()):
   self.assertEqual(cli.main(["configuration","effort","high","extra"]),1)
  self.assertEqual(self.path.read_bytes(),before)
 def test_medium_default_status_does_not_write(self):
  before=self.path.read_bytes();self.assertEqual(self.runcli("configuration","effort")["global"],"medium");self.assertEqual(before,self.path.read_bytes())
 def test_global_and_provider_resource_effort(self):
  self.runcli("configuration","effort","high");self.runcli("configuration","effort","low","--executor","claude")
  self.assertEqual(self.runcli("configuration","effort")["effective"],{"codex":"high","claude":"low"})
  self.runcli("configuration","effort","inherit","--executor","claude");self.assertEqual(self.runcli("configuration","effort")["effective"]["claude"],"high")
 def test_native_settings_are_independent(self):
  self.runcli("configuration","effort","high");self.runcli("configuration","executor","codex","--model","test-model","--native-effort","low")
  c=self.config();self.assertEqual(user_controls.resource_profile(c,"codex")["effort"],"high")
  self.assertEqual(executor.provider_settings(c["executor"],{"id":"codex","model":"old"})["model"],"test-model")
  self.assertEqual(executor.provider_settings(c["executor"],{"id":"codex"})["native_effort"],"low")
  self.assertNotIn("native_effort",executor.provider_settings(c["executor"],{"id":"claude"}))
 def test_native_inheritance(self):
  self.runcli("configuration","executor","claude","--model","test","--native-effort","high")
  self.assertEqual(self.runcli("configuration","executor","claude","--inherit-model","--native-effort","inherit")["native_options"],{})
 def test_auto_goals_master_preserves_subtoggle(self):
  self.runcli("configuration","auto-goals","replenish","disable");self.runcli("configuration","auto-goals","disable");self.runcli("configuration","auto-goals","enable")
  self.assertFalse(self.runcli("configuration","auto-goals")["effective_replenishment"])
  self.runcli("configuration","auto-goals","replenish","enable");self.assertTrue(self.runcli("configuration","auto-goals")["effective_replenishment"])
 def test_profiles_increase_evidence_precision_not_native_effort(self):
  profiles=[user_controls.resource_profile({"resources":{"effort":e}},"codex") for e in ("low","medium","high")]
  self.assertEqual([p["initial_matched_samples_per_effort"] for p in profiles],[2,5,10])
  self.assertEqual([p["descriptive_wilson_lower_target"] for p in profiles],[.8,.9,.95])
  self.assertTrue(all("native_effort" not in p for p in profiles))
if __name__=="__main__":unittest.main()
