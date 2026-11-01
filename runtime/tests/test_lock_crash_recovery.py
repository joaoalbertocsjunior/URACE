"""Controlled real-process lock publication and recovery checks."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from urace import _common


class LockCrashRecoveryTests(unittest.TestCase):
    def test_crash_before_metadata_write_never_publishes_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)/'state.json'
            ready = Path(directory)/'ready'
            script = '''from pathlib import Path
import os,signal,sys
from urace import _common
real_write=os.write
def pause(fd,data):
    Path(sys.argv[2]).touch()
    os.kill(os.getpid(),signal.SIGSTOP)
    return real_write(fd,data)
os.write=pause
with _common.state_lock(Path(sys.argv[1])):pass
'''
            child = subprocess.Popen([sys.executable,'-c',script,str(state),str(ready)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                deadline=time.monotonic()+10
                while not ready.exists() and child.poll() is None and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(ready.exists(),'Child did not reach write boundary')
                published=state.with_suffix('.lock').exists()
                child.kill()
                child.communicate(timeout=5)
                self.assertEqual(child.returncode,-signal.SIGKILL)
                self.assertFalse(published,'Incomplete lock became visible')
                with _common.state_lock(state):
                    self.assertEqual(json.loads(state.with_suffix('.lock').read_text())['pid'],os.getpid())
            finally:
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=5)

    def test_contender_preserves_live_owner_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json'
            with _common.state_lock(state):
                before=state.with_suffix('.lock').read_bytes()
                child=subprocess.run([sys.executable,'-c','from pathlib import Path; from urace._common import state_lock; import sys\nwith state_lock(Path(sys.argv[1])): pass',str(state)],capture_output=True,text=True,timeout=10)
                self.assertNotEqual(child.returncode,0)
                self.assertIn('locked by live process',child.stderr)
                self.assertEqual(state.with_suffix('.lock').read_bytes(),before)

    def test_dead_published_owner_is_recovered_and_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json'
            child=subprocess.run([sys.executable,'-c','import os; from pathlib import Path; from urace._common import state_lock; import sys\nwith state_lock(Path(sys.argv[1])): os._exit(0)',str(state)],capture_output=True,timeout=10)
            self.assertEqual(child.returncode,0)
            with _common.state_lock(state):
                self.assertEqual(json.loads(state.with_suffix('.lock').read_text())['pid'],os.getpid())
            observations=[json.loads(x) for x in (state.parent/'stale-lock-observations.jsonl').read_text().splitlines()]
            self.assertTrue(any(x['disposition']=='removed' for x in observations))
            self.assertFalse(state.with_suffix('.lock').exists())

    def test_partial_metadata_is_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json'
            with patch.object(_common.os,'write',return_value=1):
                with self.assertRaisesRegex(OSError,'Incomplete'):
                    with _common.state_lock(state):pass
            self.assertFalse(state.with_suffix('.lock').exists())
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),['state.lock.guard'])

    def test_guard_inode_survives_successive_acquisitions(self):
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)/'state.json'
            with _common.state_lock(state):
                first=state.with_suffix('.lock.guard').stat().st_ino
            with _common.state_lock(state):
                self.assertEqual(state.with_suffix('.lock.guard').stat().st_ino,first)

    def test_simultaneous_stale_reclamation_has_one_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            state=base/'state.json'
            dead=subprocess.Popen([sys.executable,'-c','pass'])
            dead.wait(timeout=5)
            state.with_suffix('.lock').write_text(json.dumps({'pid':dead.pid}))
            script='''from pathlib import Path
import os,signal,sys,time
from urace._common import state_lock
state,base,role=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
real_unlink=Path.unlink
paused=False
def unlink(self,*args,**kwargs):
    global paused
    if role=='delayed' and self==state.with_suffix('.lock') and not paused:
        paused=True
        (base/'delayed-ready').touch()
        os.kill(os.getpid(),signal.SIGSTOP)
    return real_unlink(self,*args,**kwargs)
Path.unlink=unlink
try:
    with state_lock(state):
        (base/(role+'-entered')).touch()
        deadline=time.monotonic()+10
        while not (base/'release').exists() and time.monotonic()<deadline:time.sleep(.01)
except RuntimeError:
    (base/(role+'-rejected')).touch()
'''
            children=[]
            def start(role):
                child=subprocess.Popen([sys.executable,'-c',script,str(state),str(base),role],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                children.append(child)
                return child
            def wait_for(names):
                deadline=time.monotonic()+5
                while not any((base/name).exists() for name in names) and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(any((base/name).exists() for name in names),str(names))
            try:
                delayed=start('delayed')
                wait_for(['delayed-ready'])
                start('owner')
                wait_for(['owner-entered','owner-rejected'])
                os.kill(delayed.pid,signal.SIGCONT)
                wait_for(['delayed-entered','delayed-rejected'])
                self.assertTrue((base/'owner-rejected').exists())
                self.assertTrue((base/'delayed-entered').exists())
                self.assertFalse((base/'owner-entered').exists())
            finally:
                (base/'release').touch()
                for child in children:
                    if child.poll() is None:
                        os.kill(child.pid,signal.SIGCONT)
                        try:child.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=5)


if __name__=='__main__':unittest.main()
