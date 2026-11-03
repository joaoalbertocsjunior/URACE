import tempfile,unittest
from pathlib import Path
from urace.feature_catalog import Catalog,RULES_ID,atom_id
class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.catalog=Catalog(Path(self.temp.name)/'catalog');self.value={'capability':'One independently testable parser operation','interface_sha384':'a'*96,'acceptance_sha384':'b'*96,'content_sha384':'c'*96,'dependencies':[],'publisher_id':'publisher','license_id':'MIT'}
 def test_exact_replay_and_alias_do_not_duplicate_atoms_content_or_rewards(self):
  first=self.catalog.declare('A-v1',self.value);self.assertEqual(self.catalog.declare('A-v1',self.value)['status'],'ALREADY_DECLARED');self.catalog.declare('alias',self.value);state=self.catalog.state();self.assertEqual(len(state['atoms']),1);self.assertEqual(len(state['contents']),1);self.assertEqual(first['new_reward_units'],0);self.assertFalse(first['ownership_proven'])
 def test_version_alias_cannot_be_rebound_and_dependencies_must_exist(self):
  first=self.catalog.declare('A-v1',self.value)
  with self.assertRaises(ValueError):self.catalog.declare('A-v1',{**self.value,'content_sha384':'d'*96})
  with self.assertRaises(ValueError):self.catalog.declare('B-v1',{**self.value,'dependencies':['f'*96]})
  self.catalog.declare('B-v1',{**self.value,'dependencies':[first['atom_id']]})
 def test_lifecycle_preserves_history_and_no_admin_override(self):
  first=self.catalog.declare('A-v1',self.value);self.catalog.lifecycle(first['atom_id'],'deprecated');state=self.catalog.state();self.assertEqual(state['atoms'][first['atom_id']]['lifecycle'],'deprecated')
  with self.assertRaises(ValueError):self.catalog._apply(state,{'rules_sha384':RULES_ID,'operation':'ADMIN_OVERRIDE'})
 def test_empty_inspection_is_read_only_and_no_semantic_perfection_claim(self):
  state=self.catalog.state();self.assertFalse(self.catalog.root.exists());self.assertFalse(state['semantic_deduplication_proven']);self.assertFalse(state['global_monopoly_prevention_proven'])
 def test_qualify_sets_reward_eligible(self):
  decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
  state=self.catalog.state();self.assertFalse(state['atoms'][atom]['reward_eligible'])
  result=self.catalog.qualify(atom,{'peer_count':3,'canonical_fingerprint':'a'*64,'outcome_fingerprint':'b'*64})
  self.assertEqual(result['status'],'QUALIFIED');self.assertTrue(result['reward_eligible'])
  state=self.catalog.state();self.assertTrue(state['atoms'][atom]['quality_proven']);self.assertTrue(state['atoms'][atom]['reward_eligible'])
 def test_qualify_by_alias(self):
  self.catalog.declare('A-v1',self.value)
  result=self.catalog.qualify('A-v1',{'peer_count':2,'canonical_fingerprint':'c'*64,'outcome_fingerprint':'d'*64})
  self.assertEqual(result['status'],'QUALIFIED')
 def test_qualify_requires_two_peers(self):
  decl=self.catalog.declare('A-v1',self.value)
  with self.assertRaises(ValueError):self.catalog.qualify(decl['atom_id'],{'peer_count':1,'canonical_fingerprint':'a'*64,'outcome_fingerprint':'b'*64})
 def test_qualify_idempotent(self):
  decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
  self.catalog.qualify(atom,{'peer_count':2,'canonical_fingerprint':'a'*64,'outcome_fingerprint':'b'*64})
  result=self.catalog.qualify(atom,{'peer_count':5,'canonical_fingerprint':'a'*64,'outcome_fingerprint':'b'*64})
  self.assertEqual(result['status'],'ALREADY_QUALIFIED')
 def test_qualify_unknown_atom_raises(self):
  with self.assertRaises(ValueError):self.catalog.qualify('no-such-atom',{'peer_count':3,'canonical_fingerprint':'a'*64,'outcome_fingerprint':'b'*64})
 def test_qualify_with_exchange_derives_peer_count_from_audit(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   a=pe.Exchange(root/'a');b=pe.Exchange(root/'b');c=pe.Exchange(root/'c')
   for e in (a,b,c):e.configure(enabled=True);e.feature('feat',[])
   aid=a.identity()['peer_id'];bid=b.identity()['peer_id'];cid=c.identity()['peer_id']
   canon_fp='a'*64
   # Two distinct peers qualify same artifact
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='b'*64,score_delta=5.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[],receipt_verified=True,qualification_id=None)
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=cid,feature='feat',bundle='c'*64,score_delta=5.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[],receipt_verified=True,qualification_id=None)
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   result=self.catalog.qualify(atom,{'canonical_fingerprint':canon_fp,'outcome_fingerprint':'b'*64},exchange=b)
   self.assertEqual(result['status'],'QUALIFIED')
   self.assertEqual(result['peer_count'],2)

 def test_qualify_with_exchange_rejects_when_only_one_peer(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   b=pe.Exchange(root/'b');b.configure(enabled=True);b.feature('feat',[])
   aid='a'*64;canon_fp='a'*64
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='b'*64,score_delta=5.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[],receipt_verified=True,qualification_id=None)
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   with self.assertRaises(ValueError):
    self.catalog.qualify(atom,{'canonical_fingerprint':canon_fp,'outcome_fingerprint':'b'*64},exchange=b)

 def test_qualify_with_exchange_ignores_caller_supplied_peer_count(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   b=pe.Exchange(root/'b');b.configure(enabled=True);b.feature('feat',[])
   aid='a'*64;canon_fp='a'*64
   # Caller tries to supply peer_count=99 but only 1 audit peer — should still fail
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='b'*64,score_delta=5.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[],receipt_verified=True,qualification_id=None)
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   with self.assertRaises(ValueError):
    self.catalog.qualify(atom,{'peer_count':99,'canonical_fingerprint':canon_fp,'outcome_fingerprint':'b'*64},exchange=b)

 def test_feature_score_returns_zero_with_no_borrows(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe
  with tempfile.TemporaryDirectory() as tmp:
   b=pe.Exchange(Path(tmp)/'b');b.configure(enabled=True);b.feature('feat',[])
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   score=self.catalog.feature_score(atom,b,canonical_fp='a'*64)
   self.assertEqual(score['distinct_borrowers'],0)
   self.assertEqual(score['propagation_score'],0.0)
   self.assertFalse(score['reward_threshold_met'])

 def test_feature_score_threshold_met_with_two_peers(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe
  with tempfile.TemporaryDirectory() as tmp:
   b=pe.Exchange(Path(tmp)/'b');b.configure(enabled=True);b.feature('feat',[])
   aid='a'*64;cid='c'*64;canon_fp='f'*64
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='b1'*32,score_delta=3.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[])
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=cid,feature='feat',bundle='b2'*32,score_delta=3.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[])
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   score=self.catalog.feature_score(atom,b,canonical_fp=canon_fp)
   self.assertEqual(score['distinct_borrowers'],2)
   self.assertAlmostEqual(score['propagation_score'],6.0)
   self.assertTrue(score['reward_threshold_met'])

 def test_borrow_emits_audit_event_and_credits_creator(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe,token_ledger as tl
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   a=pe.Exchange(root/'a');b=pe.Exchange(root/'b')
   for e in (a,b):e.configure(enabled=True);e.feature('feat',[])
   aid=a.identity()['peer_id'];canon_fp='f'*64
   # Simulate node B having applied A's artifact
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='x'*64,score_delta=3.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[])
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   # Node B borrows the feature from A
   result=self.catalog.borrow(atom,b,canonical_fp=canon_fp,outcome_delta=2.5,receipt_verified=True)
   self.assertEqual(result['status'],'BORROWED')
   self.assertEqual(result['creator_peer_id'],aid)
   rows=b.audit_rows()
   borrow_rows=[r for r in rows if r.get('kind')=='FEATURE_BORROWED']
   self.assertEqual(len(borrow_rows),1)
   self.assertEqual(borrow_rows[0]['creator_peer_id'],aid)
   # Creator earns from borrow (grant=3 + improvement=3 + borrow=1)
   bal=tl.balance(b,aid)
   self.assertAlmostEqual(bal,7.0)

 def test_borrow_with_settlement_requires_receipt_verified(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe,token_ledger as tl
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   a=pe.Exchange(root/'a');b=pe.Exchange(root/'b')
   for e in (a,b):e.configure(enabled=True,token_settlement=True);e.feature('feat',[])
   aid=a.identity()['peer_id'];canon_fp='f'*64
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='x'*64,score_delta=3.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[])
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   # Borrow without receipt_verified — should NOT credit creator with settlement=True
   self.catalog.borrow(atom,b,canonical_fp=canon_fp,outcome_delta=2.5,receipt_verified=False)
   bal=tl.balance(b,aid)
   self.assertAlmostEqual(bal,3.0)  # baseline only, no propagation earn
   # Borrow with receipt_verified — should credit creator
   self.catalog.borrow(atom,b,canonical_fp=canon_fp,outcome_delta=2.5,receipt_verified=True)
   bal=tl.balance(b,aid)
   self.assertAlmostEqual(bal,4.0)  # 3 + 1 borrow credit (same borrower node, deduped)

 def test_borrow_deduplicates_same_borrower(self):
  """Multiple borrows from the same node only earn one credit for the creator."""
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe,token_ledger as tl
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   a=pe.Exchange(root/'a');b=pe.Exchange(root/'b')
   for e in (a,b):e.configure(enabled=True);e.feature('feat',[])
   aid=a.identity()['peer_id'];canon_fp='f'*64
   with b.lock():b.event('APPLIED_AFTER_LOCAL_QUALIFICATION',peer=aid,feature='feat',bundle='x'*64,score_delta=3.0,canonical_fingerprint=canon_fp,outcome_fingerprint='o'*64,affected_files=[])
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   self.catalog.borrow(atom,b,canonical_fp=canon_fp,outcome_delta=2.5,receipt_verified=True)
   self.catalog.borrow(atom,b,canonical_fp=canon_fp,outcome_delta=2.5,receipt_verified=True)
   bal=tl.balance(b,aid)
   self.assertAlmostEqual(bal,7.0)  # 3(grant)+3(improvement)+1(borrow×1 deduped), not +2

 def test_borrow_invalid_canonical_fp_raises(self):
  import tempfile
  from pathlib import Path
  from urace import peer_exchange as pe
  with tempfile.TemporaryDirectory() as tmp:
   b=pe.Exchange(Path(tmp)/'b');b.configure(enabled=True)
   decl=self.catalog.declare('A-v1',self.value);atom=decl['atom_id']
   with self.assertRaises(ValueError):
    self.catalog.borrow(atom,b,canonical_fp='not-hex',outcome_delta=1.0)

 def test_old_rules_v1_events_still_accepted(self):
  from urace.feature_catalog import RULES_V1_ID,RULES_V2_ID
  self.assertNotEqual(RULES_V1_ID,RULES_V2_ID)
  state={'atoms':{},'aliases':{},'contents':{},'schema':'x','rules_sha384':RULES_V1_ID,'native_inference_calls':0,'globally_minimal_features_proven':False,'semantic_deduplication_proven':False,'global_monopoly_prevention_proven':False}
  from urace.feature_catalog import atom_id,descriptor
  val={'capability':'cap','interface_sha384':'a'*96,'acceptance_sha384':'b'*96,'content_sha384':'c'*96,'dependencies':[],'publisher_id':'pub','license_id':'MIT'}
  key=atom_id(descriptor(val))
  event={'rules_sha384':RULES_V1_ID,'operation':'DECLARE_ATOM','alias':'x','atom':key,'descriptor':val}
  self.catalog._apply(state,event)
  self.assertIn(key,state['atoms'])
