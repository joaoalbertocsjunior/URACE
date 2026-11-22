"""H2: Security test suite — HMAC tamper detection, injection guard, auth errors, wallet."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestSecurity(unittest.TestCase):

    # ── H2-1: HMAC tamper detection ──────────────────────────────────────────

    def test_hmac_tamper_detection(self):
        """Tampered ledger dict with a forged integrity seal raises AuthIntegrityError."""
        import urace.portfolio_storage as ps
        from urace.portfolio_storage import AuthIntegrityError

        # Build a minimal ledger dict with a plausible but invalid integrity seal.
        # verify_ledger skips the check when there is no "integrity" key, so we
        # must include one — with deliberately wrong values so HMAC fails.
        tampered_data = {
            "ledger": {"balance": 9999999},
            "integrity": {
                "algorithm": "HMAC-SHA256",
                "digest": "0" * 64,
                "authentication_tag": "deadbeef" * 8,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            key_dir = Path(tmpdir) / "secrets"
            key_dir.mkdir(parents=True, exist_ok=True)
            key_path = key_dir / "portfolio-integrity.key"
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(os.urandom(32))

            with patch.object(ps, "INTEGRITY_KEY", key_path):
                with self.assertRaises(AuthIntegrityError):
                    ps.verify_ledger(tampered_data)

    # ── H2-2: Authenticated archive tamper detection ─────────────────────────

    def test_verify_authenticated_archive_tamper(self):
        """Payload tampered in an authenticated archive raises AuthIntegrityError."""
        import urace.portfolio_storage as ps
        from urace.portfolio_storage import AuthIntegrityError

        with tempfile.TemporaryDirectory() as tmpdir:
            key_dir = Path(tmpdir) / "secrets"
            key_dir.mkdir(parents=True, exist_ok=True)
            key_path = key_dir / "portfolio-integrity.key"
            key_bytes = os.urandom(32)
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(key_bytes)

            archive_path = Path(tmpdir) / "archive.json"

            with patch.object(ps, "INTEGRITY_KEY", key_path):
                # Write a valid authenticated archive.
                ps.write_authenticated_archive(archive_path, "test-backup", {"foo": "bar"})

                # Read it back and tamper with the payload.
                envelope = json.loads(archive_path.read_text(encoding="utf-8"))
                envelope["payload"]["foo"] = "TAMPERED"
                archive_path.write_text(
                    json.dumps(envelope, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

                # Verification must now fail.
                with self.assertRaises(AuthIntegrityError):
                    ps.verify_authenticated_archive(archive_path)

    # ── H2-3: Injection guard in feature routing ─────────────────────────────

    def test_injection_guard_in_routing(self):
        """Shell metacharacters in routing text must not raise — routing is safe."""
        from urace.freeform_routing import _rank_p2p_features

        # Provide a minimal feature catalog so the scorer has something to work with.
        features = [
            {
                "id": "feat-001",
                "name": "data export",
                "description": "Export data as CSV",
                "tags": ["data", "csv"],
            }
        ]
        malicious_text = '"; rm -rf /; "'
        # Must return a list (possibly empty) without raising.
        result = _rank_p2p_features(malicious_text, features)
        self.assertIsInstance(result, list)

    # ── H2-4: SourceAuthError and SourceQuotaError hierarchy ─────────────────

    def test_source_auth_error_is_source_unavailable(self):
        """SourceAuthError and SourceQuotaError must be subclasses of SourceUnavailableError."""
        from urace.source_adapters._base import (
            SourceAuthError,
            SourceQuotaError,
            SourceUnavailableError,
        )

        self.assertTrue(
            issubclass(SourceAuthError, SourceUnavailableError),
            "SourceAuthError must be a subclass of SourceUnavailableError",
        )
        self.assertTrue(
            issubclass(SourceQuotaError, SourceUnavailableError),
            "SourceQuotaError must be a subclass of SourceUnavailableError",
        )

    # ── H2-5: _install_error_handler smoke test ───────────────────────────────

    def test_install_error_handler_smoke(self):
        """_install_error_handler replaces sys.excepthook with a custom handler."""
        from urace.cli_helpers import _install_error_handler

        original_hook = sys.__excepthook__
        # Reset to default before testing (in case a prior test replaced it).
        sys.excepthook = original_hook
        try:
            _install_error_handler()
            self.assertIsNot(
                sys.excepthook,
                sys.__excepthook__,
                "_install_error_handler must replace sys.excepthook",
            )
        finally:
            # Restore to avoid polluting other tests.
            sys.excepthook = original_hook

    # ── H2-6: wallet_show never exposes private_key ───────────────────────────

    def test_wallet_private_key_not_in_show(self):
        """wallet_show must not include 'private_key' in its returned dict."""
        from urace.crypto_wallet import wallet_init, wallet_show

        with tempfile.TemporaryDirectory() as tmpdir:
            wallet_init(wallet_dir=tmpdir)
            info = wallet_show(wallet_dir=tmpdir)
            self.assertNotIn(
                "private_key",
                info,
                "wallet_show must never return private_key",
            )


if __name__ == "__main__":
    unittest.main()
