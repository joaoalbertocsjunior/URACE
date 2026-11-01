"""Hybrid-signed commitments for existing JSONL journals, preserving original readers.

Historical/gap bytes are explicitly observed, never retroactively origin-authenticated.
A crash can leave an uncovered tail; coverage reports it rather than inventing proof.
"""
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import fcntl,hashlib,json,os
from .ledger_crypto import canonical
from .signed_ledger import Ledger

CHUNK=1048576

@lru_cache(maxsize=64)
def _ledger(path):return Ledger(Path(path).with_name(Path(path).name+'.pq')/'blocks')

@contextmanager
def _lock(path):
 root=path.with_name(path.name+'.pq');root.mkdir(parents=True,exist_ok=True,mode=0o700)
 if path.is_symlink() or root.is_symlink():raise ValueError('Journal symlink prohibited')
 os.chmod(root,0o700)
 with (root/'append.lock').open('a') as stream:
  fcntl.flock(stream,fcntl.LOCK_EX);yield

def _last(ledger):
 if not (ledger.root/'head.json').exists():return 0
 head=ledger._head();page=ledger.page(max(0,head['sequence']-1),1)
 row=page['rows'][0]['payload']
 if row['kind']!='JOURNAL_BYTES':raise ValueError('Unexpected journal commitment')
 return row['details']['end']

def _commit(ledger,start,data,claim):
 return ledger.append('JOURNAL_BYTES',{'start':start,'end':start+len(data),'bytes':len(data),'sha384':hashlib.sha384(data).hexdigest(),'origin_claim':claim})

def append_row(path,row):
 path=Path(path)
 if path.suffix!='.jsonl' or not isinstance(row,dict):raise ValueError('Typed JSONL journal required')
 data=canonical(row)+b'\n'
 if len(data)>CHUNK:raise ValueError('Journal row exceeds bounded record size')
 path.parent.mkdir(parents=True,exist_ok=True)
 with _lock(path):
  ledger=_ledger(str(path.resolve()));ledger.identity();end=_last(ledger);size=path.stat().st_size if path.exists() else 0
  if size<end:raise ValueError('Journal truncation conflicts with authenticated history')
  if size:
   with path.open('rb') as stream:
    stream.seek(-1,2)
    if stream.read(1)!=b'\n':raise ValueError('Incomplete existing journal row; preserve and recover before appending')
  if size>end:
   with path.open('rb') as stream:
    stream.seek(end)
    while end<size:
     chunk=stream.read(min(CHUNK,size-end));_commit(ledger,end,chunk,'LEGACY_OR_GAP_BYTES_OBSERVED_NOT_ORIGIN_AUTHENTICATED');end+=len(chunk)
  with path.open('ab') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
  _commit(ledger,end,data,'ROW_WRITTEN_AND_COMMITTED_BY_INSTRUMENTED_WRITER')
 return row

def coverage(path,checkpoint=None):
 path=Path(path);ledger=_ledger(str(path.resolve()))
 if not ledger.root.exists():return {'status':'NOT_AUTHENTICATED','covered_bytes':0,'uncovered_tail_bytes':path.stat().st_size if path.exists() else 0,'historical_authorship_proven':False,'native_inference_calls':0}
 verified=ledger.verify(checkpoint);end=historical=attributed=0;offset=0
 with path.open('rb') as stream:
  while offset<verified['blocks']:
   page=ledger.page(offset,100)
   for block in page['rows']:
    payload=block['payload'];value=payload['details']
    if payload['kind']!='JOURNAL_BYTES' or set(value)!={'start','end','bytes','sha384','origin_claim'} or type(value['bytes']) is not int or not 0<value['bytes']<=CHUNK or value['start']!=end or value['end']!=end+value['bytes']:raise ValueError('Journal range commitment invalid')
    raw=stream.read(value['bytes'])
    if len(raw)!=value['bytes'] or hashlib.sha384(raw).hexdigest()!=value['sha384']:raise ValueError('Journal bytes differ from signed commitment')
    end=value['end']
    if value['origin_claim']=='ROW_WRITTEN_AND_COMMITTED_BY_INSTRUMENTED_WRITER':attributed+=value['bytes']
    elif value['origin_claim']=='LEGACY_OR_GAP_BYTES_OBSERVED_NOT_ORIGIN_AUTHENTICATED':historical+=value['bytes']
    else:raise ValueError('Unsupported journal origin claim')
   offset+=len(page['rows'])
  tail=max(0,path.stat().st_size-end)
 return {'status':'AUTHENTICATED_OBSERVED_BYTES' if not tail else 'UNCOVERED_TAIL','covered_bytes':end,'instrumented_writer_bytes':attributed,'historically_observed_bytes':historical,'uncovered_tail_bytes':tail,'historical_authorship_proven':False,'global_consensus':False,'native_inference_calls':0,'head':verified['head'],'signature_storage_bytes':verified['stored_bytes']}
