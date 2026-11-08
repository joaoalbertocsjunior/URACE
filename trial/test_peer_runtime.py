"""Signed fixture peer requests require local review and use the unchanged qualification queue."""
from pathlib import Path
from unittest.mock import patch
import json,tempfile,unittest
import peer_runtime as pr,runtime_evaluation as ev,runtime_cycle as cycle
from test_runtime_cycle import Fixture
from urace import peer_exchange as pe

class PeerRuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.f=Fixture(self.root/'runtime-fixture',False);self.a=pe.Exchange(self.root/'sender');self.b=pe.Exchange(self.root/'receiver')
  for ex in (self.a,self.b):ex.configure(enabled=True);ex.feature('planning',[])
  self.aid=self.a.identity()['peer_id'];self.bid=self.b.identity()['peer_id'];self.a.peer(self.b.identity()['certificate'],post_quantum=self.b.identity()['post_quantum']);self.b.peer(self.a.identity()['certificate'],post_quantum=self.a.identity()['post_quantum']);self.a.rule(self.bid,'planning','send',True);self.b.rule(self.aid,'planning','receive',True)
  payload={'schema':'runtime-source-edits-v1','module':'milestone_suggestions.py','edits':[{'old':"goal.get('status') in ('ACHIEVED','COMPLETED','SUPERSEDED','CANCELLED')",'new':"str(goal.get('status','')).upper() in ('ACHIEVED','COMPLETED','SUPERSEDED','CANCELLED')"}]};result=self.a.prepare(self.bid,'planning',json.dumps(payload),True);self.bundle=result['bundle_id'];self.b.receive(self.a.inspect(self.bundle)['bundle']);self.mock=patch.object(pr,'exchange',return_value=self.b);self.mock.start();self.addCleanup(self.mock.stop)
 def test_owner_review_required_before_enqueue(self):
  with self.assertRaises(ValueError):pr.enqueue(self.f.base,self.bundle)
  self.assertFalse((self.f.base/'runtime-peer-requests').exists())
 def test_queued_receipt_has_separate_unknown_remote_costs_no_native_call(self):
  self.b.review(self.bundle,'approved-for-evaluation','fixture');result=pr.enqueue(self.f.base,self.bundle);self.assertEqual(result['status'],'QUEUED_FOR_LOCAL_QUALIFICATION');self.assertFalse(result['applied']);self.assertEqual(pr.enqueue(self.f.base,self.bundle)['status'],'ALREADY_QUEUED');request=json.loads((self.f.base/'runtime-peer-requests'/(self.bundle+'.json')).read_text());receipt=json.loads((self.f.base/'transport'/(request['receipt_id']+'.json')).read_text());self.assertEqual(receipt['tokens'],0);self.assertIsNone(receipt['remote_tokens']);self.assertEqual(receipt['role'],'PEER_CANDIDATE')
 def test_block_after_queue_prevents_evaluation_and_retains_rejected_request(self):
  self.b.review(self.bundle,'approved-for-evaluation','fixture');pr.enqueue(self.f.base,self.bundle);self.b.block(self.aid,True)
  with patch.object(ev,'measure',side_effect=AssertionError('Policy denied before evaluation')):result=pr.process_one(self.f.base,{},self.f.config,10800)
  self.assertEqual(result['status'],'REJECTED');self.assertEqual(len(list((self.f.base/'runtime-cycles').glob('*/peer-request-completed.json'))),1);self.assertEqual(list((self.f.base/'runtime-peer-requests').glob('*.json')),[])
 def test_guard_controller_source_patch_cannot_be_queued(self):
  payload={'schema':'runtime-source-edits-v1','module':'authority.py','edits':[{'old':'a','new':'b'}]};bid=self.a.prepare(self.bid,'planning',json.dumps(payload),True)['bundle_id'];self.b.receive(self.a.inspect(bid)['bundle']);self.b.review(bid,'approved-for-evaluation','fixture')
  with self.assertRaises(ValueError):pr.enqueue(self.f.base,bid)
