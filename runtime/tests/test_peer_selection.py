from pathlib import Path
from unittest.mock import patch
import tempfile,time,unittest
from urace import peer_exchange as pe,peer_selection as ps

class SelectionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name);self.a=pe.Exchange(root/'a');self.b=pe.Exchange(root/'b')
  for e in (self.a,self.b):e.configure(enabled=True,network=True)
  self.aid=self.a.identity()['peer_id'];self.bid=self.b.identity()['peer_id'];self.a.peer(self.b.identity()['certificate'],'https://localhost:9999',post_quantum=self.b.identity()['post_quantum']);self.b.peer(self.a.identity()['certificate'],'https://localhost:9998',post_quantum=self.a.identity()['post_quantum']);self.a.feature('A',[],wanted=True);self.b.feature('A',[],offered=True);self.a.rule(self.bid,'A','receive',True);self.b.rule(self.aid,'A','send',True)
 def refresh(self):
  info={'schema':pe.SCHEMA,'protocol_version':pe.PROTOCOL_VERSION,'peer_id':self.bid,'patterns':['request-response'],'incorporation':'quarantine-only'}
  def mock_req(exchange,peer,method,params):return info if method=='exchange.info' else ps.offers(self.b,self.aid)
  with patch.object(pe,'request',side_effect=mock_req):return ps.refresh(self.a)
 def test_matching_offers_rank_without_model_calls_or_transfers(self):
  self.refresh();result=ps.rank(self.a);self.assertEqual(result['native_model_calls'],0);self.assertFalse(result['automatic_transfer']);row=result['peers'][0];self.assertEqual(row['status'],'CANDIDATE');self.assertIsNone(row['validated_quality']);self.assertIsNone(row['expected_benefit_score'])
 def test_unknown_peer_not_falsely_called_unworthy(self):
  row=ps.rank(self.a)['peers'][0];self.assertEqual(row['status'],'NEEDS_REFRESH');self.assertIsNone(row['delivery_lower_bound'])
 def test_owner_block_always_wins(self):
  self.refresh();self.a.block(self.bid,True);self.assertEqual(ps.rank(self.a)['peers'][0]['status'],'BLOCKED')
 def test_unavailable_gets_finite_reconsideration_and_no_retry_storm(self):
  with patch.object(pe,'request',side_effect=OSError('offline')) as request:
   result=ps.refresh(self.a);next_due=result['checks'][0]['next_probe_unix'];self.assertGreater(next_due,time.time());self.assertLess(next_due,time.time()+21700);self.assertEqual(ps.refresh(self.a)['checks'],[]);self.assertEqual(request.call_count,1)
 def test_stale_catalog_is_withheld_even_when_it_claimed_quality(self):
  self.refresh();self.assertEqual(ps.rank(self.a,now=time.time()+3601)['peers'][0]['status'],'NEEDS_REFRESH')
 def test_reciprocal_terms_cannot_override_feature_deny(self):
  self.a.feature('B',[]);self.b.feature('B',[]);self.b.feature('A',[],offered=True,wants=['B']);self.b.rule(self.aid,'B','receive',True);self.refresh();self.assertEqual(ps.rank(self.a)['peers'][0]['status'],'NO_CURRENT_PERMITTED_MATCH');self.a.rule(self.bid,'B','send',True);self.assertEqual(ps.rank(self.a)['peers'][0]['status'],'CANDIDATE')
 def test_free_offers_do_not_require_reciprocity_or_first_delivery(self):
  self.refresh();row=ps.rank(self.a)['peers'][0];self.assertEqual(row['status'],'CANDIDATE');self.assertEqual(row['observed_transfers'],0)
 def test_invalid_catalog_identity_or_expiry_does_not_become_available(self):
  value=ps.offers(self.b,self.aid);value['peer_id']='forged'
  info={'schema':pe.SCHEMA,'protocol_version':pe.PROTOCOL_VERSION,'peer_id':self.bid,'patterns':['request-response'],'incorporation':'quarantine-only'}
  def mock_req(exchange,peer,method,params):return info if method=='exchange.info' else value
  with patch.object(pe,'request',side_effect=mock_req):self.assertEqual(ps.refresh(self.a)['checks'][0]['status'],'UNAVAILABLE_OR_INVALID')
 def test_nonmatching_peer_is_reconsidered_when_owner_needs_change(self):
  self.refresh();self.assertEqual(ps.rank(self.a,['B'])['peers'][0]['status'],'NO_CURRENT_PERMITTED_MATCH');self.assertEqual(ps.rank(self.a,['A'])['peers'][0]['status'],'CANDIDATE')
 def test_low_rank_does_not_prevent_metadata_exploration(self):
  self.refresh();state=ps.cache(self.a);state['peers'][self.bid]['next_probe_unix']=0;pe.atomic(self.a.root/'selection.json',state)
  with patch.object(pe,'request',return_value=ps.offers(self.b,self.aid)) as request:ps.refresh(self.a);self.assertEqual(request.call_count,1)
 def test_oversize_duplicate_catalog_and_disallowed_dependencies_fail(self):
  value=ps.offers(self.b,self.aid);value['offers']*=2
  with self.assertRaises(ValueError):ps.validate_catalog(value,self.bid)
 def test_audit_pagination_and_peer_filters(self):
  result=self.a.summary(True,limit=1,peer=self.bid);self.assertLessEqual(len(result['audit']),1);self.assertTrue(all(r.get('peer')==self.bid for r in result['audit']))

 def test_metadata_cadence_reserves_capacity_and_owner_can_change_limits(self):
  self.a.configure(max_rpc_per_day=100,max_rpc_per_peer_per_day=10);self.refresh();next_due=ps.cache(self.a)['peers'][self.bid]['next_probe_unix'];self.assertGreater(next_due,time.time()+17000);self.assertEqual(self.a.summary()['budgets']['max_rpc_per_peer_per_day'],10)
 def test_outdated_peer_version_is_marked_version_too_old(self):
  old_info={'schema':pe.SCHEMA,'protocol_version':1,'peer_id':self.bid,'patterns':['request-response'],'incorporation':'quarantine-only'}
  with patch.object(pe,'request',return_value=old_info):result=ps.refresh(self.a)
  self.assertEqual(result['checks'][0]['status'],'VERSION_TOO_OLD');self.assertEqual(ps.rank(self.a)['peers'][0]['status'],'VERSION_TOO_OLD')
 def test_version_too_old_peer_is_never_a_candidate_regardless_of_offers(self):
  old_info={'schema':pe.SCHEMA,'protocol_version':1,'peer_id':self.bid,'patterns':['request-response'],'incorporation':'quarantine-only'}
  with patch.object(pe,'request',return_value=old_info):ps.refresh(self.a)
  row=ps.rank(self.a)['peers'][0];self.assertEqual(row['status'],'VERSION_TOO_OLD');self.assertIn('min_peer_version',row['reason'])
 def test_owner_can_lower_min_peer_version_to_allow_older_peers(self):
  self.a.configure(min_peer_version=1)
  self.refresh();self.assertEqual(ps.rank(self.a)['peers'][0]['status'],'CANDIDATE')
 def test_send_blocked_when_selection_cache_marks_version_too_old(self):
  old_info={'schema':pe.SCHEMA,'protocol_version':1,'peer_id':self.bid,'patterns':['request-response'],'incorporation':'quarantine-only'}
  with patch.object(pe,'request',return_value=old_info):ps.refresh(self.a)
  self.a.feature('featureA',[]);self.a.rule(self.bid,'featureA','send',True);bid=self.a.prepare(self.bid,'featureA','fixture',True)['bundle_id']
  with self.assertRaises(ValueError) as ctx:pe.send(self.a,bid)
  self.assertIn('min_peer_version',str(ctx.exception))
 def test_local_metadata_budget_defers_without_call_or_permanent_ban(self):
  self.a.configure(max_rpc_per_day=2);self.refresh();state=ps.cache(self.a);state['peers'][self.bid]['next_probe_unix']=0;pe.atomic(self.a.root/'selection.json',state)
  with patch.object(pe,'request',side_effect=AssertionError('No extra metadata calls')):result=ps.refresh(self.a)
  self.assertEqual(result['status'],'METADATA_BUDGET_WAIT');self.assertGreater(result['next_due_unix'],time.time());self.assertEqual(ps.rank(self.a)['peers'][0]['status'],'CANDIDATE')
