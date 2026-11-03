import copy,unittest
from unittest.mock import patch
from urace import auto_goals,cli
class ProjectAutoGoals(unittest.TestCase):
 def cfg(self,name='Customer billing'):
  return {'authority':{'delegated':['objectives']},'project':{'id':name,'intent':'Improve '+name,'source':'user project brief','requirements':[{'id':'export','title':'Export '+name,'success_measure':'Independent export validation passes'}]}}
 def test_default_enabled_project_derived(self):
  s={};g=auto_goals.select(self.cfg(),s);self.assertIn('Customer billing',g['title']);self.assertEqual(g['project_source'],'user project brief');self.assertEqual(s['current_objective'],g['id'])
 def test_second_project_not_urace(self):
  g=auto_goals.select(self.cfg('Garden planner'),{});self.assertIn('Garden planner',g['title']);self.assertNotIn('URACE',g['title'])
 def test_explicit_disable(self):
  c=self.cfg();c['auto_goals']={'enabled':False};s={};self.assertIsNone(auto_goals.select(c,s));self.assertNotIn('objectives',s)
 def test_no_project_no_invented_goal(self):self.assertIsNone(auto_goals.select({'authority':{'delegated':['objectives']}},{}))
 def test_no_delegation_no_goal(self):
  c=self.cfg();c['authority']['delegated']=[];self.assertIsNone(auto_goals.select(c,{}))
 def test_manual_goal_preserved(self):
  manual={'id':'owner','title':'Owner request','status':'active'};s={'objectives':[manual],'current_objective':'owner'};self.assertEqual(auto_goals.select(self.cfg(),s),manual);self.assertEqual(s['current_objective'],'owner');self.assertEqual(len(s['objectives']),1)
 def test_new_manual_goal_defers_auto_selection(self):
  s={};automatic=auto_goals.select(self.cfg(),s);s['objectives'].append({'id':'new-owner','title':'Owner priority','status':'planned','priority':1});selected=auto_goals.select(self.cfg(),s);self.assertEqual(selected['id'],'new-owner');self.assertEqual(automatic['status'],'deferred');self.assertEqual(s['current_objective'],'new-owner')
 def test_project_change_retires_old_automatic_goal(self):
  state={};old=auto_goals.select(self.cfg('Garden'),state);auto_goals.select(self.cfg('Billing'),state);self.assertEqual(old['status'],'superseded')
 def test_changed_requirement_retires_stale_goal(self):
  state={};config=self.cfg();old=auto_goals.select(config,state);config['project']['requirements'][0]['success_measure']='New verified acceptance criteria';auto_goals.select(config,state);self.assertEqual(old['status'],'superseded')
 def test_removed_requirement_not_scheduled(self):
  state={};config=self.cfg();old=auto_goals.select(config,state);config['project']['requirements']=[];self.assertIsNone(auto_goals.select(config,state));self.assertEqual(old['status'],'superseded')
 def test_project_completed_requirement_not_scheduled(self):
  state={};config=self.cfg();old=auto_goals.select(config,state);config['project']['requirements'][0]['status']='completed';self.assertIsNone(auto_goals.select(config,state));self.assertEqual(old['status'],'superseded')
 def test_toggle_off_pauses_existing_auto_goal(self):
  state={};config=self.cfg();goal=auto_goals.select(config,state);config['auto_goals']={'enabled':False};self.assertIsNone(auto_goals.select(config,state));self.assertEqual(goal['status'],'deferred')
 def test_toggle_on_resumes_same_goal(self):
  state={};config=self.cfg();goal=auto_goals.select(config,state);config['auto_goals']={'enabled':False};auto_goals.select(config,state);config['auto_goals']['enabled']=True;again=auto_goals.select(config,state);self.assertEqual(again['id'],goal['id']);self.assertEqual(again['status'],'planned')
 def test_stable_duplicate_free(self):
  s={};a=auto_goals.select(self.cfg(),s);b=auto_goals.select(self.cfg(),s);self.assertEqual(a['id'],b['id']);self.assertEqual(len(s['objectives']),1)
 def test_completed_goal_not_reopened(self):
  s={};g=auto_goals.select(self.cfg(),s);g['status']='completed';self.assertIsNone(auto_goals.select(self.cfg(),s))
 def test_requirement_dependency(self):
  c=self.cfg();c['project']['requirements'][0]['dependencies']=['contract'];self.assertIsNone(auto_goals.select(c,{}));c['project']['requirements'].append({'id':'contract','status':'completed'});self.assertIsNotNone(auto_goals.select(c,{}))
 def test_authority_not_changed_by_project_content(self):
  c=self.cfg();s={'authority':{'delegated':['objectives'],'reserved':['publish externally']}};before=copy.deepcopy(s['authority']);auto_goals.select(c,s);self.assertEqual(s['authority'],before)
 def test_cycle_calls_existing_selector(self):
  import inspect
  source=inspect.getsource(cli.cycle);self.assertIn('auto_goals.select(config, state)',source);self.assertLess(source.index('auto_goals.select(config, state)'),source.index('    candidates ='))
if __name__=='__main__':unittest.main()
