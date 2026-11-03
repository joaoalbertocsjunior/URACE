"""Non-candidate evolution acceptance guard.

Ordinary runtime evolution may call this module but may not replace it. Kernel
changes require a separate operator-controlled bootstrap or review path.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


# Kernel files the improvement pipeline can never touch.
PROTECTED_FILES = (
    "urace/runtime/urace/launcher.py",
    "urace/runtime/urace/evolution_guard.py",
    # P2P security kernel — crypto primitives, protocol, audit chain, token ledger
    "urace/runtime/urace/peer_exchange.py",
    "urace/runtime/urace/peer_discovery.py",
    "urace/runtime/urace/ledger_crypto.py",
    "urace/runtime/urace/signed_ledger.py",
    "urace/runtime/urace/token_ledger.py",
    # Economic primitives — token supply constants and tokenomics definition
    # Changes require explicit governance (operator authorization + quality gate)
    "urace/runtime/urace/credit_ledger.py",
    "urace/runtime/urace/tokenomics.py",
)

# Subset used for the P2P corpus fingerprint (handshake integrity check).
P2P_SECURITY_FILES = (
    "urace/runtime/urace/peer_exchange.py",
    "urace/runtime/urace/peer_discovery.py",
    "urace/runtime/urace/ledger_crypto.py",
    "urace/runtime/urace/signed_ledger.py",
    "urace/runtime/urace/token_ledger.py",
)

# ── Release authority — multi-sig ─────────────────────────────────────────────
#
# Tuple of trusted Ed25519 public keys (hex).  All must be set before deployment.
# REQUIRED_SIGNATURES governs how many must sign each update bundle.
#
# SETUP:
#   urace p2p keygen --out ~/.urace/key1.hex   # generates key, prints pub_hex
#   # Paste pub_hex entries here; commit; distribute binary to all nodes.
#   # Private keys → HSM / air-gapped vault, NEVER in this repo.
#
# DEV KEY-1 — deterministic seed, local testing only.
# Run `urace p2p keygen` to generate real keys before distributing.
RELEASE_AUTHORITY_KEYS: tuple[str, ...] = (  # See OPERATORS.md §1 — replace dev key before deploying
    "5243de12e036c7219a0a08f0459ab17965fde97c98a9ac9aaa672881ecb6f66e",  # key-1-dev
)
REQUIRED_SIGNATURES: int = 1   # raise to 2+ for M-of-N once multiple keys are added  # See OPERATORS.md §4 — raise to 2+ when second key added

# Backward-compat alias — single-key APIs still work.
RELEASE_AUTHORITY_PUB_KEY_HEX: str = RELEASE_AUTHORITY_KEYS[0] if RELEASE_AUTHORITY_KEYS else ""

# ── Central update hub ────────────────────────────────────────────────────────
#
# Canonical URL where the operator always publishes the latest signed bundle JSON.
# Hardcoded here (PROTECTED_FILES) — the improvement pipeline can never change it.
# Nodes check this URL every ~60 min (DiscoverySession._reannounce_loop) and also
# whenever ≥2 distinct peers are seen running a newer corpus fingerprint.
#
# Set to your GitHub Releases URL once the release repo is created, e.g.:
#   https://github.com/your-org/urace/releases/latest/download/p2p-bundle.json
# Empty string = not yet configured; update checks silently skip.
P2P_UPDATE_BUNDLE_URL: str = ""  # See OPERATORS.md §1 and §2 — set before deploying


# ── Signature verification ────────────────────────────────────────────────────

def verify_release_signature(corpus_fp_bytes: bytes, sig_bytes: bytes) -> bool:
    """Verify a signature against ANY key in RELEASE_AUTHORITY_KEYS.

    Returns False if no key is configured or none match.
    Used as the default author_verify_fn throughout the update pipeline.
    """
    for key_hex in RELEASE_AUTHORITY_KEYS:
        if not key_hex:
            continue
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex))
            pub.verify(sig_bytes, corpus_fp_bytes)
            return True
        except Exception:
            continue
    return False


def verify_multi_sig(corpus_fp_hex: str, sigs: dict[str, str]) -> tuple[bool, int]:
    """Check M-of-N signatures from RELEASE_AUTHORITY_KEYS.

    sigs: {pub_key_hex: sig_hex} — subset of keys that signed the bundle.
    Returns (meets_threshold, valid_count).
    """
    data      = corpus_fp_hex.encode()
    valid     = 0
    for key_hex in RELEASE_AUTHORITY_KEYS:
        sig_hex = sigs.get(key_hex, "")
        if not sig_hex:
            continue
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(key_hex)).verify(
                bytes.fromhex(sig_hex), data
            )
            valid += 1
        except Exception:
            pass
    return valid >= REQUIRED_SIGNATURES, valid


# ── Transparency log — Sigstore Rekor ─────────────────────────────────────────

def log_to_rekor(corpus_fp_hex: str, pub_key_hex: str, sig_hex: str) -> dict:
    """Submit update bundle metadata to Sigstore's Rekor transparency log.

    Rekor is a free, publicly auditable, append-only log (used by npm, Maven,
    Kubernetes).  Once submitted, the entry cannot be removed — any published
    update is permanently visible and verifiable by anyone.

    Returns {"log_index": N, "integrated_time": T, "log_id": "...", "uuid": "..."}
    on success, or {"error": "..."} on failure.  Never raises.
    """
    import urllib.request as _ur
    REKOR_URL = "https://rekor.sigstore.dev/api/v1/log/entries"
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        pub_pem = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_key_hex)).public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        )
        payload = json.dumps({
            "kind":       "hashedrekord",
            "apiVersion": "0.0.1",
            "spec": {
                "signature": {
                    "content":   base64.b64encode(bytes.fromhex(sig_hex)).decode(),
                    "publicKey": {"content": base64.b64encode(pub_pem).decode()},
                },
                "data": {
                    "hash": {"algorithm": "sha256", "value": corpus_fp_hex}
                },
            },
        }).encode()
        req = _ur.Request(REKOR_URL, data=payload,
                          headers={"Content-Type": "application/json"}, method="POST")
        with _ur.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
        entry = next(iter(body.values()))
        return {
            "log_index":       entry.get("logIndex"),
            "integrated_time": entry.get("integratedTime"),
            "log_id":          entry.get("logID", ""),
            "uuid":            next(iter(body)),
        }
    except Exception as exc:
        return {"error": str(exc)}


# ── On-chain anchoring — OpenTimestamps (Bitcoin) ─────────────────────────────

def anchor_opentimestamps(sha256_hex: str) -> str:
    """Anchor a SHA256 hash to Bitcoin via OpenTimestamps calendar servers.

    Submits the hash to public OTS calendar servers (free, no fees).  The
    calendar batches many hashes into a single Bitcoin OP_RETURN transaction
    every ~6 hours, producing an irrefutable timestamp proof.

    Returns base64-encoded partial OTS file on success, '' on failure.
    The partial can be upgraded to a full proof after Bitcoin confirmation.
    Never raises.
    """
    import urllib.request as _ur
    OTS_CALENDARS = [
        "https://alice.btc.calendar.opentimestamps.org",
        "https://bob.btc.calendar.opentimestamps.org",
        "https://finney.calendar.eternitywall.com",
    ]
    sha256_bytes = bytes.fromhex(sha256_hex)
    for url in OTS_CALENDARS:
        try:
            req = _ur.Request(url, data=sha256_bytes,
                              headers={"Content-Type": "application/x-www-form-urlencoded"},
                              method="POST")
            with _ur.urlopen(req, timeout=10) as resp:
                return base64.b64encode(resp.read()).decode()
        except Exception:
            continue
    return ""


# ── Keygen ─────────────────────────────────────────────────────────────────────

def p2p_keygen(output_path: "Path | None" = None) -> dict:
    """Generate a new Ed25519 release keypair for P2P update signing.

    Writes the private key hex to output_path (default: ~/.urace/release_key.hex).
    KEEP THE PRIVATE KEY OFFLINE.  Only the public key goes in RELEASE_AUTHORITY_KEYS.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    import os as _os

    priv_key  = Ed25519PrivateKey.generate()
    priv_raw  = priv_key.private_bytes_raw()
    pub_bytes = priv_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    pub_hex   = pub_bytes.hex()

    if output_path is None:
        output_path = Path(_os.path.expanduser("~")) / ".urace" / "release_key.hex"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(priv_raw.hex() + "\n", encoding="utf-8")
    output_path.chmod(0o600)

    return {
        "pub_key_hex":   pub_hex,
        "priv_key_path": str(output_path),
        "instructions": (
            f"1. Add to RELEASE_AUTHORITY_KEYS in evolution_guard.py:\n"
            f"   \"{pub_hex}\",\n"
            f"2. Commit & distribute to all nodes.\n"
            f"3. Private key: {output_path}  (chmod 600 — keep offline)"
        ),
    }


# ── Bundle build / verify / apply ─────────────────────────────────────────────

PROTECTED_CONFIG_PATHS = (
    ("authority",),
    ("constraints",),
    ("self_evolution_policy",),
    ("executor", "max_executor_calls_per_24h"),
    ("executor", "max_executor_calls_per_30d"),
)


def _value(value: dict, path: tuple[str, ...]):
    for key in path:
        value = value[key]
    return value


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def p2p_corpus_fingerprint(product_root: Path) -> str:
    """SHA256 of all P2P security file contents, sorted by path."""
    h = hashlib.sha256()
    for relative in sorted(P2P_SECURITY_FILES):
        path = product_root / relative
        if path.exists():
            h.update(relative.encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def build_p2p_update_bundle(
    product_root: Path,
    author_sign_fns,
    *,
    log_rekor: bool = False,
    anchor_ots: bool = False,
) -> dict:
    """Package current P2P security files into a signed update bundle.

    author_sign_fns:
      Single callable fn(bytes) -> str          — v1-compat, single sig
      List of (pub_key_hex, fn(bytes)->str)      — v2 multi-sig

    log_rekor=True  → submit to Sigstore Rekor transparency log
    anchor_ots=True → submit to OpenTimestamps Bitcoin calendar (non-blocking)

    Returns bundle dict; schema is "urace-p2p-update-v2" for multi-sig, v1 otherwise.
    """
    files: dict[str, str] = {}
    h = hashlib.sha256()
    for relative in sorted(P2P_SECURITY_FILES):
        path = product_root / relative
        if path.exists():
            content = path.read_bytes()
            files[relative] = content.hex()
            h.update(relative.encode())
            h.update(content)
    corpus_fp = h.hexdigest()

    # Determine signing mode
    multi = isinstance(author_sign_fns, list)
    if multi:
        sigs: dict[str, str] = {}
        first_pub = None
        first_sig = None
        for pub_hex, sign_fn in author_sign_fns:
            raw = sign_fn(corpus_fp.encode())
            sig_hex = raw if isinstance(raw, str) else raw.hex()
            sigs[pub_hex] = sig_hex
            if first_pub is None:
                first_pub, first_sig = pub_hex, sig_hex
        bundle: dict = {
            "schema":             "urace-p2p-update-v2",
            "corpus_fingerprint": corpus_fp,
            "files":              files,
            "author_signatures":  sigs,
            "announced_at":       int(__import__("time").time()),
        }
    else:
        raw = author_sign_fns(corpus_fp.encode())
        sig_hex = raw if isinstance(raw, str) else raw.hex()
        first_pub  = RELEASE_AUTHORITY_PUB_KEY_HEX
        first_sig  = sig_hex
        bundle = {
            "schema":             "urace-p2p-update-v1",
            "corpus_fingerprint": corpus_fp,
            "files":              files,
            "author_signature":   sig_hex,
            "announced_at":       int(__import__("time").time()),
        }

    if log_rekor and first_pub and first_sig:
        bundle["transparency_log"] = log_to_rekor(corpus_fp, first_pub, first_sig)

    if anchor_ots:
        bundle["opentimestamps_proof"] = anchor_opentimestamps(corpus_fp)

    return bundle


def verify_p2p_update_bundle(bundle: dict, author_verify_fn=None) -> list[str]:
    """Verify a P2P update bundle (v1 or v2) before applying.

    author_verify_fn(corpus_fp: bytes, sig: bytes) -> bool
      Defaults to verify_release_signature() when None.
    Returns [] on success, list of error strings on failure.
    """
    if author_verify_fn is None:
        author_verify_fn = verify_release_signature

    errors: list[str] = []
    schema = bundle.get("schema", "")
    if schema not in ("urace-p2p-update-v1", "urace-p2p-update-v2"):
        errors.append("invalid bundle schema")
        return errors

    files = bundle.get("files", {})
    if not files:
        errors.append("bundle contains no files")

    h = hashlib.sha256()
    for relative in sorted(files):
        h.update(relative.encode())
        h.update(bytes.fromhex(files[relative]))
    computed = h.hexdigest()
    if computed != bundle.get("corpus_fingerprint"):
        errors.append("corpus fingerprint mismatch — bundle integrity compromised")

    if schema == "urace-p2p-update-v2":
        sigs = bundle.get("author_signatures", {})
        valid, count = verify_multi_sig(computed, sigs)
        if not valid:
            errors.append(
                f"multi-sig threshold not met: {count}/{REQUIRED_SIGNATURES} valid signatures"
            )
    else:
        # v1 single sig
        sig_hex = bundle.get("author_signature", "")
        try:
            if not author_verify_fn(computed.encode(), bytes.fromhex(sig_hex)):
                errors.append("author signature verification failed")
        except (ValueError, TypeError) as exc:
            errors.append(f"author signature unparseable: {exc}")

    unknown = sorted(set(files) - set(P2P_SECURITY_FILES))
    if unknown:
        errors.append(f"bundle contains unexpected files: {unknown}")
    return errors


def apply_p2p_update_bundle(bundle: dict, product_root: Path, author_verify_fn=None,
                             run_tests: bool = True, timeout: int = 120) -> list[str]:
    """Apply a verified P2P update bundle with operator-gate.

    Stages files, runs the accepted test suite, only copies to product_root on pass.
    ALWAYS operator-initiated — never called autonomously by URACE.
    """
    if author_verify_fn is None:
        author_verify_fn = verify_release_signature

    errors = verify_p2p_update_bundle(bundle, author_verify_fn)
    if errors:
        return errors
    if not run_tests:
        for relative, hex_content in bundle["files"].items():
            dest = product_root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(bytes.fromhex(hex_content))
        return []
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp)
        shutil.copytree(product_root / "urace/runtime", staging / "urace/runtime")
        for relative, hex_content in bundle["files"].items():
            dest = staging / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(bytes.fromhex(hex_content))
        subprocess.run(["git", "init", "-q"], cwd=staging, check=True)
        subprocess.run(["git", "add", "."], cwd=staging, check=True)
        subprocess.run(["git", "-c", "user.name=P2P Update", "-c",
                        "user.email=update@localhost", "commit", "-qm", "p2p-update"],
                       cwd=staging, check=True)
        result = subprocess.run(
            ["python3", "-m", "pytest", "urace/runtime/tests/", "-q", "--tb=short"],
            cwd=staging, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, check=False,
        )
        if result.returncode:
            errors.append("update rejected by test suite:\n" + result.stdout[-2000:])
            return errors
    for relative, hex_content in bundle["files"].items():
        dest = product_root / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(bytes.fromhex(hex_content))
    return []


# ── Candidate validation ───────────────────────────────────────────────────────

def kernel_hashes(product_root: Path) -> dict[str, str]:
    return {relative: digest(product_root / relative) for relative in PROTECTED_FILES}


def validate_candidate(product_root: Path, candidate_root: Path, stable_runtime: Path,
                        timeout: int = 120,
                        expected_kernel_hashes: dict[str, str] | None = None) -> list[str]:
    """Validate candidate code with the accepted guard and accepted tests."""
    errors: list[str] = []
    expected_kernel_hashes = expected_kernel_hashes or kernel_hashes(product_root)
    for relative in PROTECTED_FILES:
        candidate = candidate_root / relative
        if not candidate.exists() or digest(candidate) != expected_kernel_hashes.get(relative):
            errors.append(f"protected evolution-kernel file changed: {relative}")
    try:
        accepted_config = stable_runtime / "urace/runtime/urace/config.json"
        accepted = json.loads(
            (accepted_config if accepted_config.exists()
             else product_root / "urace/runtime/urace/config.json").read_text(encoding="utf-8")
        )
        proposed = json.loads(
            (candidate_root / "urace/runtime/urace/config.json").read_text(encoding="utf-8")
        )
        for path in PROTECTED_CONFIG_PATHS:
            if _value(proposed, path) != _value(accepted, path):
                errors.append("protected evolution policy changed: " + ".".join(path))
        for scope, files in proposed["executor"]["allowed_files_by_scope"].items():
            overlap = sorted(set(files) & set(PROTECTED_FILES))
            if overlap:
                errors.append(f"scope {scope} may mutate protected kernel: {', '.join(overlap)}")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        errors.append(f"candidate configuration cannot be independently validated: {type(error).__name__}")
    accepted_tests = stable_runtime / "urace/runtime/tests"
    if not accepted_tests.exists():
        errors.append("accepted independent test baseline is unavailable")
    if errors:
        return errors
    temporary_root = product_root / "urace" / "generated" / "temporary"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="accepted-validator-", dir=temporary_root) as directory:
        verifier_root = Path(directory)
        shutil.copytree(candidate_root / "urace/runtime", verifier_root / "urace/runtime")
        shutil.rmtree(verifier_root / "urace/runtime/tests", ignore_errors=True)
        shutil.copytree(accepted_tests, verifier_root / "urace/runtime/tests")
        for name in ("URACE.md", "README.md"):
            source = candidate_root / name
            if source.exists():
                shutil.copy2(source, verifier_root / name)
        subprocess.run(["git", "init", "-q"], cwd=verifier_root, check=True)
        subprocess.run(["git", "add", "."], cwd=verifier_root, check=True)
        subprocess.run(["git", "-c", "user.name=URACE Guard", "-c",
                        "user.email=guard@localhost", "commit", "-qm", "accepted-test candidate"],
                       cwd=verifier_root, check=True)
        test_bootstrap = """
import sys, unittest
from unittest.mock import patch
from urace import launcher
suite = unittest.defaultTestLoader.discover('tests')
with patch.object(launcher, 'validate_activation_candidate', return_value=[]):
    result = unittest.TextTestRunner(verbosity=0).run(suite)
raise SystemExit(not result.wasSuccessful())
"""
        result = subprocess.run(
            ["python3", "-c", test_bootstrap],
            cwd=verifier_root / "urace/runtime", text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, check=False,
        )
        if result.returncode:
            errors.append("accepted independent tests rejected candidate: " + result.stdout[-2000:])
    return errors
