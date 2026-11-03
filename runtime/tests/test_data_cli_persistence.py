import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urace import cli
from urace._common import atomic_write_json, state_lock

class DataCliPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='urace-data-cli-')
        self.addCleanup(self.directory.cleanup)
        self.config=copy.deepcopy(cli.load_config())
        self.config['state_path']=str(Path(self.directory.name)/'state.json')
        self.config.pop('active_product',None)
        atomic_write_json(Path(self.config['state_path']),cli.initial_state(self.config))

    def invoke(self,*args):
        stream=io.StringIO()
        with patch.object(cli,'load_config',return_value=self.config),contextlib.redirect_stdout(stream):
            code=cli.main(['data',*args,'--format','json'])
        return code,json.loads(stream.getvalue())

    def test_add_is_durable_and_subsequent_read_does_not_modify_state(self):
        code,result=self.invoke('add','case','--type','json','--connect','missing.json','--auto','false')
        self.assertEqual(code,0)
        before=Path(self.config['state_path']).read_bytes()
        code,result=self.invoke('list')
        self.assertEqual(code,0)
        self.assertEqual(result['records'][0]['name'],'case')
        self.assertEqual(before,Path(self.config['state_path']).read_bytes())

    def test_failure_records_and_disconnected_status_are_durable(self):
        self.invoke('add','case','--type','json','--connect','missing.json')
        code,result=self.invoke('sync','case')
        self.assertEqual(code,1)
        state=json.loads(Path(self.config['state_path']).read_text())
        self.assertEqual(state['data_sync_records'][0]['status'],'FAILED')
        self.assertEqual(state['data_source_records'][0]['status'],'DISCONNECTED')

    def test_mutation_respects_existing_writer_lock(self):
        before=Path(self.config['state_path']).read_bytes()
        with state_lock(Path(self.config['state_path'])):
            with self.assertRaises(RuntimeError):
                self.invoke('add','case','--type','json','--connect','missing.json')
        self.assertEqual(before,Path(self.config['state_path']).read_bytes())
