"""Versioned hybrid signatures and recipient encryption using standardized primitives.

No network, provider calls, cryptocurrency or implicit peer trust. Key descriptors must
be authenticated out of band. Local administrator compromise remains out of scope.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

DOMAIN=b"URACE-LEDGER-v1"
MAX_BYTES=1048576

def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def b64(value):return base64.b64encode(value).decode("ascii")
def un64(value,limit=16384):
 if not isinstance(value,str) or len(value)>limit*2:raise ValueError("Invalid bounded encoding")
 data=base64.b64decode(value,validate=True)
 if len(data)>limit:raise ValueError("Encoding exceeds bound")
 return data

def primitives():
 try:
  from cryptography.hazmat.primitives.asymmetric import ed25519,mldsa,mlkem
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
  from cryptography.hazmat.primitives.kdf.hkdf import HKDF
  from cryptography.hazmat.primitives import hashes
 except ImportError as exc:raise ValueError("Post-quantum protection requires cryptography>=50; no classical downgrade") from exc
 return ed25519,mldsa,mlkem,AESGCM,HKDF,hashes

def public_id(public):return hashlib.sha384(canonical(public)).hexdigest()

def validate_public(public):
 if not isinstance(public,dict) or set(public)!={"schema","ed25519","ml_dsa_65","ml_kem_768"} or public["schema"]!="urace-hybrid-keys-v1":raise ValueError("Unsupported identity contract")
 ed,dsa,kem,*_=primitives()
 ed.Ed25519PublicKey.from_public_bytes(un64(public["ed25519"]))
 dsa.MLDSA65PublicKey.from_public_bytes(un64(public["ml_dsa_65"]))
 kem.MLKEM768PublicKey.from_public_bytes(un64(public["ml_kem_768"]))
 return public

class Identity:
 def __init__(self,path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
  if self.path.is_symlink():raise ValueError("Key symlink prohibited")
  ed,dsa,kem,*_=primitives()
  if not self.path.exists():
   value={"ed25519":b64(ed.Ed25519PrivateKey.generate().private_bytes_raw()),"ml_dsa_65":b64(dsa.MLDSA65PrivateKey.generate().private_bytes_raw()),"ml_kem_768":b64(kem.MLKEM768PrivateKey.generate().private_bytes_raw())}
   fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   with os.fdopen(fd,"wb") as f:f.write(canonical(value));f.flush();os.fsync(f.fileno())
  if self.path.stat().st_size>16384 or self.path.stat().st_mode&0o077:raise ValueError("Private key permissions or size invalid")
  value=json.loads(self.path.read_text())
  self.ed=ed.Ed25519PrivateKey.from_private_bytes(un64(value["ed25519"]))
  self.dsa=dsa.MLDSA65PrivateKey.from_seed_bytes(un64(value["ml_dsa_65"]))
  self.kem=kem.MLKEM768PrivateKey.from_seed_bytes(un64(value["ml_kem_768"]))
 def public(self):
  return {"schema":"urace-hybrid-keys-v1","ed25519":b64(self.ed.public_key().public_bytes_raw()),"ml_dsa_65":b64(self.dsa.public_key().public_bytes_raw()),"ml_kem_768":b64(self.kem.public_key().public_bytes_raw())}
 def sign(self,payload,domain):
  body=canonical({"domain":domain,"payload":payload})
  if len(body)>MAX_BYTES:raise ValueError("Signed payload too large")
  message=DOMAIN+hashlib.sha384(body).digest()
  return {"schema":"urace-hybrid-signature-v1","key_id":public_id(self.public()),"ed25519":b64(self.ed.sign(message)),"ml_dsa_65":b64(self.dsa.sign(message,DOMAIN))}
 def decrypt(self,envelope,context):
  if not isinstance(envelope,dict) or set(envelope)!={"schema","recipient","kem","nonce","ciphertext"} or envelope["schema"]!="urace-mlkem-aes256gcm-v1" or envelope["recipient"]!=public_id(self.public()):raise ValueError("Encryption identity/contract mismatch")
  *_,AESGCM,HKDF,hashes=primitives()
  secret=self.kem.decapsulate(un64(envelope["kem"]))
  key=HKDF(algorithm=hashes.SHA384(),length=32,salt=None,info=DOMAIN+canonical(context)).derive(secret)
  try:return AESGCM(key).decrypt(un64(envelope["nonce"],12),un64(envelope["ciphertext"],MAX_BYTES+16),canonical(context))
  except Exception as exc:raise ValueError('Recipient ciphertext authentication failed') from exc

def verify(public,payload,signature,domain):
 validate_public(public)
 if not isinstance(signature,dict) or set(signature)!={"schema","key_id","ed25519","ml_dsa_65"} or signature["schema"]!="urace-hybrid-signature-v1" or signature["key_id"]!=public_id(public):raise ValueError("Signature identity/contract mismatch")
 body=canonical({"domain":domain,"payload":payload})
 if len(body)>MAX_BYTES:raise ValueError("Signed payload too large")
 message=DOMAIN+hashlib.sha384(body).digest();ed,dsa,*_=primitives()
 ed.Ed25519PublicKey.from_public_bytes(un64(public["ed25519"])).verify(un64(signature["ed25519"]),message)
 dsa.MLDSA65PublicKey.from_public_bytes(un64(public["ml_dsa_65"])).verify(un64(signature["ml_dsa_65"]),message,DOMAIN)
 return True

def encrypt(public,data,context):
 validate_public(public)
 if not isinstance(data,bytes) or len(data)>MAX_BYTES:raise ValueError("Bounded plaintext required")
 _,_,kem,AESGCM,HKDF,hashes=primitives()
 secret,ciphertext=kem.MLKEM768PublicKey.from_public_bytes(un64(public["ml_kem_768"])).encapsulate()
 key=HKDF(algorithm=hashes.SHA384(),length=32,salt=None,info=DOMAIN+canonical(context)).derive(secret);nonce=os.urandom(12)
 return {"schema":"urace-mlkem-aes256gcm-v1","recipient":public_id(public),"kem":b64(ciphertext),"nonce":b64(nonce),"ciphertext":b64(AESGCM(key).encrypt(nonce,data,canonical(context)))}
