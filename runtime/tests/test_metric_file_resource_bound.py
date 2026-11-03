import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urace import external_metrics

class MetricFileResourceBoundTests(unittest.TestCase):
    def test_exact_byte_limit_remains_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'input.json').write_bytes(b'{"n":42}'+b' '*(1024-8))
            result=external_metrics.collect(root,{'mode':'PROVIDED_ONLY','max_response_bytes':1024,'sources':[{'id':'fixture','kind':'json_file','location':'input.json','values':{'n':'n'}}]})
            self.assertEqual(result['errors'],[])
            self.assertEqual(result['observations'][0]['values'],{'n':42})

    def test_large_sparse_file_is_rejected_under_small_address_space(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'oversize.json'
            with path.open('wb') as stream:stream.truncate(128*1024**2)
            script='''import json,resource,sys
from pathlib import Path
from urace import external_metrics
resource.setrlimit(resource.RLIMIT_AS,(64*1024**2,64*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(3,3))
prior={'fixture':{'value':{'n':42},'at':'prior'}}
r=external_metrics.collect(Path(sys.argv[1]),{'mode':'PROVIDED_ONLY','max_response_bytes':1024,'sources':[{'id':'fixture','kind':'json_file','location':'oversize.json','values':{'n':'n'}}]},prior)
print(json.dumps(r))
'''
            run=subprocess.run([sys.executable,'-c',script,directory],capture_output=True,text=True,timeout=10,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertEqual(run.returncode,0,run.stderr)
            result=json.loads(run.stdout)
            self.assertEqual(result['observations'],[])
            self.assertIn('exceeds 1024 bytes',result['errors'][0]['error'])
            self.assertEqual(result['last_known_good']['fixture']['value'],{'n':42})
