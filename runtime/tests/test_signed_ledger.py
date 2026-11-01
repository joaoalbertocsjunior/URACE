import copy
import json
from pathlib import Path
import tempfile
import unittest
import zlib
from urace.ledger_crypto import Identity,encrypt,verify
from urace.signed_ledger import Ledger,pack,unpack,MAX_BYTES

class CryptographyTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def test_hybrid_signature_rejects_either_half_tampering_and_domain(self):
  identity=Identity(self.root/"key.json");payload={"value":3};sig=identity.sign(payload,"test")
  self.assertTrue(verify(identity.public(),payload,sig,"test"))
  for field in ("ed25519","ml_dsa_65"):
   broken=copy.deepcopy(sig);broken[field]="AAAA"
   with self.assertRaises(Exception):verify(identity.public(),payload,broken,"test")
  with self.assertRaises(Exception):verify(identity.public(),payload,sig,"other")
 def test_encryption_recipient_context_and_tamper(self):
  sender=Identity(self.root/"a.json");other=Identity(self.root/"b.json");context={"sender":"a","purpose":"bundle"}
  envelope=encrypt(sender.public(),b"private artifact",context)
  self.assertEqual(sender.decrypt(envelope,context),b"private artifact")
  with self.assertRaises(Exception):other.decrypt(envelope,context)
  with self.assertRaises(Exception):sender.decrypt(envelope,{"purpose":"other"})
  envelope["ciphertext"]="AAAA"
  with self.assertRaises(Exception):sender.decrypt(envelope,context)
 def test_compression_bounds_and_trailing_data(self):
  self.assertEqual(unpack(pack(b"x"*10000)),b"x"*10000)
  with self.assertRaises(ValueError):unpack(b"Z"+zlib.compress(b"x"*(MAX_BYTES+1)))
  with self.assertRaises(ValueError):unpack(b"Z"+zlib.compress(b"x")+b"trailing")
 def test_ledger_recovery_checkpoint_and_tamper(self):
  ledger=Ledger(self.root/"ledger");first=ledger.append("RECEIVED",{"artifact":"x"*10000});checkpoint={k:first[k] for k in ("sequence","hash","author")}
  ledger.append("REVIEWED",{"status":"approved"});self.assertEqual(ledger.verify(checkpoint)["blocks"],2)
  ledger._save_head(checkpoint) # crash after block write but before head publication
  self.assertTrue(ledger.verify(checkpoint)["unpublished_next_block"])
  ledger.append("RECOVERY_CONFIRMED",{})
  self.assertEqual(ledger.verify(checkpoint)["blocks"],3)
  self.assertEqual(len(ledger.page(0,1)["rows"]),1)
  ledger._path(3).unlink();ledger._path(2).unlink();ledger._save_head(checkpoint)
  with self.assertRaises(ValueError):ledger.verify({"sequence":2,"hash":"f"*96,"author":checkpoint["author"]})
  raw=bytearray(ledger._path(1).read_bytes());raw[-5]^=1;ledger._path(1).write_bytes(raw)
  with self.assertRaises(Exception):ledger.verify()

if __name__=="__main__":unittest.main()

class PublicAuditTests(unittest.TestCase):
 def test_read_only_empty_audit_and_public_verification_without_private_key(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   ledger=Ledger(Path(folder)/'absent');self.assertEqual(ledger.verify()['status'],'NOT_INITIALIZED');self.assertFalse(ledger.root.exists())
   ledger.append('PUBLIC_AUDIT',{'content_digest':'e'*96});before={p.name:p.read_bytes() for p in ledger.root.iterdir()};(ledger.root/'identity.json').rename(ledger.root/'key-not-needed-for-audit')
   with patch('urace.signed_ledger.Identity',side_effect=AssertionError('Private key unavailable')):
    self.assertEqual(ledger.verify()['blocks'],1);page=ledger.page();self.assertNotIn('public',page['rows'][0]);self.assertIn('public',page)
