"""Real local cryptography/TLS, with isolated fixture nodes; no external peers or native calls."""
from pathlib import Path
from unittest.mock import patch
import copy,json,tempfile,threading,unittest
from urace import peer_exchange as pe,exchange_cli,cli,api_interface,command_surface,integration_bridge

class ExchangeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name);self.a=pe.Exchange(root/'a');self.b=pe.Exchange(root/'b')
 def pair(self,network=False):
  for e in (self.a,self.b):e.configure(enabled=True,network=network);e.feature('featureA',[])
  self.aid=self.a.identity()['peer_id'];self.bid=self.b.identity()['peer_id'];self.a.peer(self.b.identity()['certificate'],post_quantum=self.b.identity()['post_quantum']);self.b.peer(self.a.identity()['certificate'],post_quantum=self.a.identity()['post_quantum']);self.a.rule(self.bid,'featureA','send',True);self.b.rule(self.aid,'featureA','receive',True)
 def bundle(self):
  result=self.a.prepare(self.bid,'featureA','reviewed fixture patch',True);return self.a.inspect(result['bundle_id'])['bundle']
 def test_default_network_is_off_read_only_and_creates_nothing(self):
  # P2P-first default: exchange enabled=True but network=False (TCP requires explicit opt-in)
  self.assertTrue(self.a.summary()['settings']['enabled']);self.assertFalse(self.a.summary()['settings']['network']);self.assertFalse(self.a.root.exists())
  with self.assertRaises(ValueError):pe.server(self.a)  # server() raises because network=False
  self.assertFalse(self.a.root.exists())
 def test_explicit_export_and_import_are_distinct_and_never_apply(self):
  self.pair();bundle=self.bundle();self.assertEqual(self.a.summary()['counts']['EXPORTED'],1);result=self.b.receive(bundle);self.assertEqual(result['status'],'QUARANTINED');self.assertFalse(result['applied']);self.assertEqual(self.b.receive(bundle)['status'],'ALREADY_QUARANTINED');self.assertEqual(self.b.summary()['applied'],0)
 def test_no_permission_no_export(self):
  self.pair();self.a.rule(self.bid,'featureA','send',False)
  with self.assertRaises(ValueError):self.bundle()
 def test_dependency_deny_blocks_parent_and_cycles_fail_closed(self):
  self.pair();self.a.feature('featureB',[]);self.a.feature('featureA',['featureB'])
  with self.assertRaises(ValueError):self.bundle()
  self.a.rule(self.bid,'featureB','send',True);self.assertTrue(self.bundle());self.a.feature('featureB',['featureA'])
  with self.assertRaises(ValueError):self.bundle()
 def test_signature_and_content_digest_tampering_rejected(self):
  self.pair();bundle=self.bundle();bundle['payload']['artifact']='tampered'
  with self.assertRaises(ValueError):self.b.receive(bundle)
  bundle=self.bundle();bundle['signature']='AAAA'
  with self.assertRaises(ValueError):self.b.receive(bundle)
 def test_wrong_recipient_and_tls_identity_rejected(self):
  self.pair();bundle=self.bundle()
  with self.assertRaises(ValueError):self.a.receive(bundle)
  with self.assertRaises(ValueError):self.b.receive(bundle,'not-signer')
 def test_block_prevents_pending_receive_review_unblock_clears_grants(self):
  self.pair();bundle=self.bundle();bid=self.b.receive(bundle)['bundle_id'];self.b.block(self.aid,True)
  with self.assertRaises(ValueError):self.b.receive(bundle)
  with self.assertRaises(ValueError):self.b.review(bid,'approved-for-evaluation','ok')
  self.b.block(self.aid,False)
  with self.assertRaises(ValueError):self.b.receive(bundle)
 def test_review_never_claims_applied_or_used(self):
  self.pair();bid=self.b.receive(self.bundle())['bundle_id'];result=self.b.review(bid,'approved-for-evaluation','local tests still needed');self.assertFalse(result['applied'])
  with self.assertRaises(ValueError):self.b.review(bid,'applied','no proof')
 def test_replay_dedup_and_per_peer_budget(self):
  self.pair()
  for _ in range(5):self.b.receive(self.bundle())
  with self.assertRaises(ValueError):self.b.receive(self.bundle())
 def test_audit_chain_detects_altered_history(self):
  self.pair();path=self.a.root/'audit.jsonl';lines=path.read_text().splitlines();row=json.loads(lines[0]);row['kind']='FORGED';lines[0]=json.dumps(row);path.write_text('\n'.join(lines)+'\n')
  with self.assertRaises(ValueError):self.a.summary()
 def test_real_mutual_tls_fixture_transfer_probe_and_off_switch(self):
  self.pair(True)
  with pe.server(self.b) as server:
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    self.a.peer(self.b.identity()['certificate'],'https://127.0.0.1:'+str(server.server_port));info=pe.request(self.a,self.bid,'exchange.info',{});self.assertEqual(info['peer_id'],self.bid);self.assertEqual(info['protocol_version'],pe.PROTOCOL_VERSION)
    bid=self.a.prepare(self.bid,'featureA','fixture only',True)['bundle_id'];result=pe.send(self.a,bid);self.assertEqual(result['status'],'QUARANTINED');self.assertEqual(self.a.summary()['counts']['SENT_QUARANTINED'],1)
    self.b.configure(network=False)
    with self.assertRaises(ValueError):pe.request(self.a,self.bid,'exchange.info',{})
   finally:server.shutdown();thread.join(timeout=5)
 def test_pinned_certificate_mismatch_rejected(self):
  self.pair(True);third=pe.Exchange(Path(self.tmp.name)/'third');third.configure(enabled=True,network=True);third.peer(self.a.identity()['certificate'],post_quantum=self.a.identity()['post_quantum'])
  with pe.server(third) as server:
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    self.a.peer(self.b.identity()['certificate'],'https://127.0.0.1:'+str(server.server_port))
    with self.assertRaises((ValueError,OSError)):pe.request(self.a,self.bid,'exchange.info',{})
   finally:server.shutdown();thread.join(timeout=5)
 def test_settings_advertise_dependency_and_invalid_endpoints(self):
  # P2P-first default: enabled=True, so network=True is allowed without explicit enable.
  # The remaining dependency: advertise=True requires network=True first.
  with self.assertRaises(ValueError):self.a.configure(advertise=True)  # network=False → error
  for endpoint in ('http://localhost','https://user:secret@localhost','https://localhost/path','https://localhost/#x'):
   with self.assertRaises(ValueError):pe.validate_endpoint(endpoint)
 def test_discovery_is_off_by_default(self):
  with self.assertRaises(ValueError):pe.discover(self.a)
 def test_private_file_and_symlink_export_prohibited(self):
  root=Path(self.tmp.name);p=root/'credential.txt';p.write_text('secret')
  with self.assertRaises(ValueError):exchange_cli.bounded_file(str(p),100,True)
  symlink=root/'link.pem';symlink.symlink_to(p)
  with self.assertRaises(ValueError):exchange_cli.bounded_file(str(symlink),100)
 def test_cli_grammar_typed_api_discovery_and_stream_boundary(self):
  parser=cli.build_parser();catalog=command_surface.operation_parsers(parser)
  for name in ('product exchange status','product exchange rule set','product exchange network serve','api protocols'):self.assertIn(name,catalog)
  argv=api_interface.build_argv(parser,command='product exchange rule set',params={'peer_id':'p','feature_id':'A','direction':'send','allow':False});self.assertEqual(argv[-2:],['--allow','false'])
  self.assertTrue(api_interface.persistent(['product','exchange','network','serve']));self.assertTrue(command_surface.read_only(['product','exchange','status']));self.assertFalse(command_surface.read_only(['product','exchange','bundle','send','x']))
  raw={'schema':integration_bridge.SCHEMA,'project_id':'p','executor_id':'e','operator':True,'read_only':False,'commands':['product exchange network serve']}
  with self.assertRaises(integration_bridge.BridgeError):integration_bridge.Policy(parser,raw,root=Path(self.tmp.name),storage=Path(self.tmp.name)/'jobs')
 def test_protocol_catalog_refuses_universal_semantic_claim(self):
  from urace.protocol_catalog import describe
  result=describe();self.assertFalse(result['universal_translation']);self.assertEqual(len(result['bindings']),5);peer=next(v for v in result['bindings'] if v['id']=='peer-artifacts');self.assertTrue(peer['protocol_version'].startswith(pe.SCHEMA+' '));self.assertIn('ML-KEM-768',peer['application_encryption'])

 def test_min_peer_version_default_and_configure(self):
  self.assertEqual(self.a.load()['min_peer_version'],pe.PROTOCOL_VERSION)
  self.a.configure(enabled=True,min_peer_version=1);self.assertEqual(self.a.load()['min_peer_version'],1)
  with self.assertRaises(ValueError):self.a.configure(min_peer_version=0)
  with self.assertRaises(ValueError):self.a.configure(min_peer_version=pe.PROTOCOL_VERSION+1)
 def test_opt_out_cascades_to_network_and_advertising(self):
  self.pair(True);self.a.configure(advertise=True);result=self.a.configure(enabled=False);self.assertFalse(result['enabled']);self.assertFalse(result['network']);self.assertFalse(result['advertise'])
 def test_auto_selection_can_be_disabled_without_native_calls(self):
  self.a.configure(auto_select=False);self.assertFalse(self.a.summary()['settings']['auto_select'])
 def test_dns_sd_handler_uses_standard_keyword_contract_without_trusting_discovery(self):
  import types,sys
  self.pair(True)
  class Zeroconf:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def get_service_info(self,type_,name,timeout):return types.SimpleNamespace(port=8766,parsed_addresses=lambda:['127.0.0.1'])
  state=types.SimpleNamespace(Added=object(),Removed=object())
  class Browser:
   def __init__(self,z,type_,handlers):handlers[0](zeroconf=z,service_type=type_,name='fixture._urace-exchange._tcp.local.',state_change=state.Added)
   def cancel(self):pass
  module=types.SimpleNamespace(Zeroconf=Zeroconf,ServiceBrowser=Browser,ServiceStateChange=state)
  with patch.dict(sys.modules,{'zeroconf':module}),patch.object(pe.time,'sleep'):
   result=pe.discover(self.a,1);self.assertEqual(len(result['candidates']),1);self.assertFalse(result['auto_trusted']);self.assertFalse(result['auto_connected'])

 def test_simultaneous_reciprocal_tls_transfers_hold_no_cross_peer_locks(self):
  from concurrent.futures import ThreadPoolExecutor
  self.pair(True);self.a.rule(self.bid,'featureA','receive',True);self.b.rule(self.aid,'featureA','send',True)
  with pe.server(self.a) as sa,pe.server(self.b) as sb:
   threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in (sa,sb)]
   for t in threads:t.start()
   try:
    self.a.peer(self.b.identity()['certificate'],'https://127.0.0.1:'+str(sb.server_port));self.b.peer(self.a.identity()['certificate'],'https://127.0.0.1:'+str(sa.server_port));a=self.a.prepare(self.bid,'featureA','a to b',True)['bundle_id'];b=self.b.prepare(self.aid,'featureA','b to a',True)['bundle_id'];barrier=threading.Barrier(2)
    def transfer(ex,bid):barrier.wait(timeout=3);return pe.send(ex,bid)
    with ThreadPoolExecutor(max_workers=2) as pool:
     futures=[pool.submit(transfer,self.a,a),pool.submit(transfer,self.b,b)]
     for future in futures:self.assertEqual(future.result(timeout=15)['status'],'QUARANTINED')
   finally:
    for server in (sa,sb):server.shutdown()
    for t in threads:t.join(timeout=5)

class HybridProtocolBoundaryTests(unittest.TestCase):
 setUp=ExchangeTests.setUp
 pair=ExchangeTests.pair
 bundle=ExchangeTests.bundle
 def test_recomputed_classical_history_still_requires_hybrid_authentication(self):
  self.pair();path=self.a.root/'audit.jsonl';rows=[json.loads(v) for v in path.read_text().splitlines()];previous='0'*64
  for row in rows:
   row['previous']=previous;row['kind']='FORGED';row.pop('sha256');row['sha256']=pe.digest(row);previous=row['sha256']
  path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
  with self.assertRaises(ValueError):self.a.summary()
 def test_pq_identity_not_silently_replaced(self):
  self.pair();other=pe.Exchange(Path(self.tmp.name)/'replacement');other.configure(enabled=True)
  with self.assertRaises(ValueError):self.a.peer(self.b.identity()['certificate'],post_quantum=other.identity()['post_quantum'])
 def test_forged_counter_receipt_cannot_become_confirmed_delivery(self):
  from urace.ledger_crypto import Identity
  self.pair(True);bid=self.a.prepare(self.bid,'featureA','fixture',True)['bundle_id'];reply=self.b.receive(self.a.inspect(bid)['bundle'])
  bad=Identity(Path(self.tmp.name)/'forger.json');reply['receipt']['signature']=bad.sign(reply['receipt']['payload'],'delivery-receipt')
  with patch.object(pe,'request',return_value=reply),self.assertRaises(Exception):pe.send(self.a,bid)
  self.assertNotIn('SENT_QUARANTINED',self.a.summary()['counts'])
 def test_changed_derived_distribution_claims_rejected(self):
  self.pair();bundle=self.bundle();bundle['payload']['distribution_terms']['payment_enabled']=True;bundle['signature']=self.a.sign(bundle['payload'])
  with self.assertRaises(ValueError):self.b.receive(bundle)
