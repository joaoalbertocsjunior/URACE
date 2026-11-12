import json,tempfile,unittest
from pathlib import Path

from urace import crypto_wallet as cw


class WalletInitTests(unittest.TestCase):
 def test_creates_keyfile(self):
  with tempfile.TemporaryDirectory() as td:
   result = cw.wallet_init(td)
   self.assertEqual(result["status"], "ok")
   self.assertTrue(Path(td, "key.json").exists())

 def test_returns_address_and_public_key(self):
  with tempfile.TemporaryDirectory() as td:
   result = cw.wallet_init(td)
   self.assertIn("address", result)
   self.assertIn("public_key", result)
   self.assertTrue(result["address"].startswith("0x"))

 def test_does_not_return_private_key(self):
  with tempfile.TemporaryDirectory() as td:
   result = cw.wallet_init(td)
   self.assertNotIn("private_key", result)

 def test_keyfile_has_schema_version(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   data = json.loads(Path(td, "key.json").read_text())
   self.assertEqual(data["schema_version"], 1)

 def test_keyfile_has_private_key(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   data = json.loads(Path(td, "key.json").read_text())
   self.assertIn("private_key", data)
   self.assertEqual(len(data["private_key"]), 64)  # 32 bytes hex

 def test_raises_if_exists_without_overwrite(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   with self.assertRaises(FileExistsError):
    cw.wallet_init(td)

 def test_overwrite_replaces_keypair(self):
  with tempfile.TemporaryDirectory() as td:
   first = cw.wallet_init(td)
   second = cw.wallet_init(td, overwrite=True)
   # Addresses are extremely unlikely to collide
   self.assertNotEqual(first["address"], second["address"])

 def test_curve_is_secp256k1(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   data = json.loads(Path(td, "key.json").read_text())
   self.assertEqual(data["curve"], "secp256k1")

 def test_public_key_uncompressed_length(self):
  with tempfile.TemporaryDirectory() as td:
   result = cw.wallet_init(td)
   # Uncompressed secp256k1 pub key: 65 bytes = 130 hex chars
   self.assertEqual(len(result["public_key"]), 130)
   self.assertTrue(result["public_key"].startswith("04"))


class WalletShowTests(unittest.TestCase):
 def test_shows_address_and_public_key(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_show(td)
   self.assertEqual(result["status"], "ok")
   self.assertIn("address", result)
   self.assertIn("public_key", result)

 def test_does_not_expose_private_key(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_show(td)
   self.assertNotIn("private_key", result)

 def test_raises_if_no_wallet(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(FileNotFoundError):
    cw.wallet_show(td)

 def test_path_reported(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_show(td)
   self.assertIn("key.json", result["path"])


class WalletSignTests(unittest.TestCase):
 def test_sign_string_payload(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_sign("hello world", td)
   self.assertEqual(result["status"], "ok")
   self.assertIn("signature_der", result)
   self.assertIn("payload_sha256", result)

 def test_sign_bytes_payload(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_sign(b"binary data", td)
   self.assertEqual(result["status"], "ok")

 def test_signature_is_hex(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_sign("test", td)
   sig = result["signature_der"]
   # Should be valid hex
   bytes.fromhex(sig)

 def test_payload_sha256_is_correct(self):
  import hashlib
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_sign("hello", td)
   expected = hashlib.sha256(b"hello").hexdigest()
   self.assertEqual(result["payload_sha256"], expected)

 def test_algorithm_field(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_sign("x", td)
   self.assertEqual(result["algorithm"], "ECDSA-secp256k1-SHA256")

 def test_different_messages_produce_different_hashes(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   r1 = cw.wallet_sign("msg1", td)
   r2 = cw.wallet_sign("msg2", td)
   self.assertNotEqual(r1["payload_sha256"], r2["payload_sha256"])

 def test_raises_if_no_wallet(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(FileNotFoundError):
    cw.wallet_sign("hello", td)


class WalletRotateTests(unittest.TestCase):
 def test_rotate_produces_new_address(self):
  with tempfile.TemporaryDirectory() as td:
   first = cw.wallet_init(td)
   result = cw.wallet_rotate(td)
   self.assertEqual(result["status"], "ok")
   self.assertEqual(result["old_address"], first["address"])
   self.assertNotEqual(result["old_address"], result["new_address"])

 def test_backup_file_created(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_rotate(td)
   backup = Path(result["backup_path"])
   self.assertTrue(backup.exists())

 def test_custody_signature_in_result(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_rotate(td)
   self.assertIn("custody_signature", result)
   bytes.fromhex(result["custody_signature"])

 def test_backup_contains_retired_at(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   result = cw.wallet_rotate(td)
   backup_data = json.loads(Path(result["backup_path"]).read_text())
   self.assertIn("retired_at", backup_data)

 def test_raises_if_no_wallet(self):
  with tempfile.TemporaryDirectory() as td:
   with self.assertRaises(FileNotFoundError):
    cw.wallet_rotate(td)

 def test_new_wallet_is_readable_after_rotate(self):
  with tempfile.TemporaryDirectory() as td:
   cw.wallet_init(td)
   cw.wallet_rotate(td)
   result = cw.wallet_show(td)
   self.assertEqual(result["status"], "ok")


class DeriveAddressTests(unittest.TestCase):
 def test_address_starts_with_0x(self):
  import secrets
  pub = bytes([4]) + secrets.token_bytes(64)
  addr = cw._derive_address(pub)
  self.assertTrue(addr.startswith("0x"))

 def test_address_is_40_hex_chars_after_prefix(self):
  import secrets
  pub = bytes([4]) + secrets.token_bytes(64)
  addr = cw._derive_address(pub)
  self.assertEqual(len(addr), 42)

 def test_deterministic(self):
  pub = bytes(range(65))
  self.assertEqual(cw._derive_address(pub), cw._derive_address(pub))


if __name__ == "__main__":
 unittest.main()
