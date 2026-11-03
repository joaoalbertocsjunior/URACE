"""Bounded compressed, hybrid-signed local blocks; no global consensus claims.

All writers serialize with flock. Blocks are immutable and the head is a cache;
recovery adopts a fully verified next block after an interrupted head update.
An independently retained checkpoint is required to detect whole-history rollback.
"""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import time
import tempfile
import zlib
from .ledger_crypto import Identity,canonical,verify,public_id,validate_public,MAX_BYTES

ZERO="0"*96

def pack(data):
 if len(data)>MAX_BYTES:raise ValueError("Block exceeds logical size")
 compressed=zlib.compress(data,6)
 return b"Z"+compressed if len(compressed)+1<len(data)*.9 else b"J"+data

def unpack(data):
 if not data or len(data)>MAX_BYTES+1:raise ValueError("Block storage bound exceeded")
 if data[:1]==b"J":value=data[1:]
 elif data[:1]==b"Z":
  decoder=zlib.decompressobj();value=decoder.decompress(data[1:],MAX_BYTES+1)
  if len(value)>MAX_BYTES or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:raise ValueError("Compressed block exceeds bound or has trailing data")
 else:raise ValueError("Unknown block encoding")
 if len(value)>MAX_BYTES:raise ValueError("Block logical bound exceeded")
 return value

class Ledger:
 def __init__(self,root):self.root=Path(root)
 @contextmanager
 def lock(self):
  self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.root.is_symlink():raise ValueError("Ledger symlink prohibited")
  os.chmod(self.root,0o700)
  with (self.root/"writer.lock").open("a") as f:
   fcntl.flock(f,fcntl.LOCK_EX);yield
 def identity(self):
  if not hasattr(self,"_identity"):self._identity=Identity(self.root/"identity.json")
  public=self._identity.public();path=self.root/"public.json"
  if path.exists():
   if path.is_symlink() or json.loads(path.read_text())!=public:raise ValueError("Historical signing identity changed")
  else:
   from ._common import atomic_write_json
   atomic_write_json(path,public);os.chmod(path,0o600)
  return self._identity
 def public(self):
  path=self.root/"public.json"
  if path.is_symlink() or path.stat().st_size>16384:raise ValueError("Invalid ledger public descriptor")
  return validate_public(json.loads(path.read_text()))
 @contextmanager
 def read_lock(self):
  # Public audit needs neither private keys nor a write/recovery operation.
  if self.root.is_symlink():raise ValueError("Ledger symlink prohibited")
  with (self.root/"writer.lock").open("rb") as f:
   fcntl.flock(f,fcntl.LOCK_SH);yield
 def _head(self):
  p=self.root/"head.json"
  return json.loads(p.read_text()) if p.exists() else {"sequence":0,"hash":ZERO,"author":public_id(self.public())}
 def _path(self,n):return self.root/("%020d.block"%n)
 def _read(self,n,previous,author):
  p=self._path(n)
  if p.is_symlink() or p.stat().st_size>MAX_BYTES+1:raise ValueError("Invalid ledger block file")
  raw=unpack(p.read_bytes());block=json.loads(raw)
  if canonical(block)!=raw or set(block)!={"payload","signature"}:raise ValueError("Noncanonical block")
  b=block["payload"]
  if b.get("schema")!="urace-signed-block-v1" or b.get("sequence")!=n or b.get("previous")!=previous or b.get("author")!=author or public_id(self.public())!=author:raise ValueError("Ledger sequence, fork or identity mismatch")
  verify(self.public(),b,block["signature"],"ledger-block")
  return block,hashlib.sha384(raw).hexdigest()
 def _save_head(self,head):
  from ._common import atomic_write_json
  atomic_write_json(self.root/"head.json",head);os.chmod(self.root/"head.json",0o600)
 def _recover(self):
  head=self._head();own=public_id(self.identity().public())
  if head.get("author")!=own:raise ValueError("Ledger author changed")
  if head["sequence"]:
   block,digest=self._read(head["sequence"],self._previous(head["sequence"]),own)
   if digest!=head["hash"]:raise ValueError("Ledger head mismatch")
  while self._path(head["sequence"]+1).exists():
   _,digest=self._read(head["sequence"]+1,head["hash"],own)
   head={"sequence":head["sequence"]+1,"hash":digest,"author":own};self._save_head(head)
  return head
 def _previous(self,n):
  if n==1:return ZERO
  p=self._path(n-1)
  if p.is_symlink() or p.stat().st_size>MAX_BYTES+1:raise ValueError("Invalid preceding block")
  return hashlib.sha384(unpack(p.read_bytes())).hexdigest()
 def append(self,kind,details):
  if not isinstance(kind,str) or not re.fullmatch("[A-Z][A-Z0-9_]{0,63}",kind) or not isinstance(details,dict):raise ValueError("Typed event required")
  with self.lock():
   identity=self.identity();head=self._recover()
   payload={"schema":"urace-signed-block-v1","author":head["author"],"sequence":head["sequence"]+1,"previous":head["hash"],"at_unix":time.time(),"kind":kind,"details":details}
   block={"payload":payload,"signature":identity.sign(payload,"ledger-block")};raw=canonical(block);stored=pack(raw)
   target=self._path(payload["sequence"])
   # A killed writer may leave a pending file, never a partly published block.
   with tempfile.NamedTemporaryFile(prefix="pending-",dir=self.root,delete=False) as f:
    pending=Path(f.name);os.chmod(pending,0o600);f.write(stored);f.flush();os.fsync(f.fileno())
   os.link(pending,target);pending.unlink()
   # Persist directory entry before publishing the new head.
   fd=os.open(self.root,os.O_RDONLY)
   try:os.fsync(fd)
   finally:os.close(fd)
   head={"sequence":payload["sequence"],"hash":hashlib.sha384(raw).hexdigest(),"author":head["author"]};self._save_head(head)
   return {**head,"stored_bytes":len(stored),"logical_bytes":len(raw)}
 def verify(self,checkpoint=None):
  if not self.root.exists():return {"status":"NOT_INITIALIZED","blocks":0,"global_consensus":False}
  with self.read_lock():
   head=self._head();previous=ZERO;stored=logical=0
   for n in range(1,head["sequence"]+1):
    block,previous=self._read(n,previous,head["author"]);stored+=self._path(n).stat().st_size;logical+=len(canonical(block))
    if checkpoint and n==checkpoint.get("sequence") and (previous!=checkpoint.get("hash") or head["author"]!=checkpoint.get("author")):raise ValueError("External checkpoint conflict")
   if previous!=head["hash"]:raise ValueError("Ledger terminal hash mismatch")
   if checkpoint and (checkpoint.get("author")!=head["author"] or checkpoint.get("sequence",0)>head["sequence"]):raise ValueError("Checkpoint indicates missing history")
   return {"status":"VERIFIED_LOCAL_CHAIN","head":head,"blocks":head["sequence"],"stored_bytes":stored,"logical_bytes":logical,"external_checkpoint_checked":checkpoint is not None,"global_consensus":False,"remote_claims_proven":False,"pending_files":sum(1 for _ in self.root.glob("pending-*")),"unpublished_next_block":self._path(head["sequence"]+1).exists(),"public":self.public()}
 def page(self,offset=0,limit=50):
  if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:raise ValueError("Bounded pagination required")
  with self.read_lock():
   head=self._head();rows=[]
   for n in range(offset+1,min(head["sequence"],offset+limit)+1):
    block,_=self._read(n,self._previous(n),head["author"]);rows.append(block)
   return {"head":head,"public":self.public(),"offset":offset,"rows":rows,"next_offset":offset+len(rows) if offset+len(rows)<head["sequence"] else None}
