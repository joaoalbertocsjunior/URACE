import unittest
from urace import context_relations as graph,executor_capabilities as ec,implementation_sequence as seq
class ContextRelationsTests(unittest.TestCase):
 def test_bidirectional_semantic_cycles_do_not_become_scheduling_dependencies(self):
  data={'a':{'relates_to':['b']},'b':{'relates_to':['a']}};g=graph.build(data);self.assertEqual(len(graph.related(g,'b')['nodes']),2);self.assertTrue(all(not e['authority_grant'] for e in g['edges']));self.assertEqual(len(seq.plan([{'id':'a'},{'id':'b'}])['dependency_phases'][0]),2)
 def test_reverse_dependencies_are_retrievable_and_unknown_links_are_explicit(self):
  g=graph.build({'a':{},'b':{'dependencies':['a','missing']}});self.assertEqual({n['id'] for n in graph.related(g,'a')['nodes']},{'a','b'});self.assertEqual(g['unresolved_edges'][0]['to'],'missing')
 def test_attention_prefers_owner_critical_changed_and_blocking_context_without_pruning(self):
  g=graph.build({'middle':{'requires_explicit_context_read':True},'changed':{'changed':True},'other':{'priority':100}});a=graph.attention(g);self.assertEqual(a['ordered_nodes'][0]['id'],'middle');self.assertFalse(a['pruning_enabled']);self.assertEqual(len(a['ordered_nodes']),3);self.assertEqual(a['native_model_calls'],0)
 def test_transformations_are_source_bound_projections(self):
  data={'a':{'title':'Original'}};first=graph.build(data);data['a']['title']='Changed';second=graph.build(data);self.assertNotEqual(first['sha256'],second['sha256']);self.assertFalse(first['semantic_comprehension_proven'])
 def test_virtual_attention_and_related_resources_reuse_scoped_reader(self):
  p=ec.prepare({},'codex',{'requirements':[{'id':'a','related_to':['b']},{'id':'b','relates_to':['a']}]});self.assertEqual(len(ec.read(p,'@attention')['ordered_nodes']),2);self.assertEqual(len(ec.read(p,'@related/a')['nodes']),2)
 def test_unknown_nodes_bad_bounds_and_identity_collisions_fail_closed(self):
  g=graph.build({'a':{}})
  with self.assertRaises(ValueError):graph.related(g,'unknown')
  with self.assertRaises(ValueError):graph.related(g,'a',depth=100)
  with self.assertRaises(ValueError):graph.from_state({'objectives':[{'id':'same'}],'context_inputs':[{'id':'same'}]})
