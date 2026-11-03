"""Regression coverage: metadata registration cannot attest to transport I/O."""
import contextlib
import io
import json
import unittest
from types import SimpleNamespace
from urace import cli

class DataSourceTruthfulnessTests(unittest.TestCase):
    def run_operation(self, action, direction='BIDIRECTIONAL'):
        source={'id':'dsr-case','name':'case','adapter_kind':'json','direction':direction,
                'connection_metadata':{'dsn':'https://user:FAKE_SECRET@invalid.example'},
                'status':'CONNECTED','last_sync_cycle':12,'last_push_cycle':13}
        state={'cycle':20,'data_source_records':[source],'data_sync_records':[], 'integrity_gaps':[]}
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):
            code=cli._handle_data_command(SimpleNamespace(data_action=action,name='case',format='json'),state,{})
        return code,state,source,stream.getvalue()

    def test_verify_does_not_attest_connectivity_without_transport(self):
        code,state,source,text=self.run_operation('verify')
        self.assertEqual(code,1)
        self.assertEqual(source['status'],'DISCONNECTED')
        self.assertEqual(json.loads(text)['error'],'ADAPTER_REQUIRED')
        self.assertEqual(state['data_sync_records'],[])

    def test_sync_and_push_record_failed_operations_without_advancing_checkpoints(self):
        for action in ('sync','push'):
            with self.subTest(action=action):
                code,state,source,text=self.run_operation(action)
                self.assertEqual(code,1)
                record=state['data_sync_records'][0]
                self.assertEqual(record['status'],'FAILED')
                self.assertEqual(record['rows_affected'],0)
                self.assertEqual(record['evidence_ids_produced'],[])
                self.assertEqual(record['records_written'],[])
                self.assertEqual(source['last_sync_cycle'],12)
                self.assertEqual(source['last_push_cycle'],13)

    def test_no_connection_secret_in_failure_outputs_or_gap_details(self):
        for action in ('verify','sync','push'):
            code,state,source,text=self.run_operation(action)
            self.assertNotIn('FAKE_SECRET',text+json.dumps(state['integrity_gaps'])+json.dumps(state['data_sync_records']))

    def test_direction_denials_remain_enforced(self):
        for action,direction in (('sync','WRITE'),('push','READ')):
            code,state,source,text=self.run_operation(action,direction)
            self.assertEqual(code,1)
            self.assertEqual(json.loads(text)['error'],'direction-violation')
            self.assertEqual(state['data_sync_records'],[])
