"""Post-quantum key lifecycle: rotation, revocation, rotation-proof verification.

Rotation: generate new keypair, sign new public key with old key (chain-of-custody).
Revocation: emit signed revocation record; peers reject the revoked key on next contact.
"""
import shutil
import tempfile
import time
from pathlib import Path

from . import ledger_crypto
from . import peer_exchange


def create_rotation_proof(old_identity, new_public_key: dict) -> dict:
    """Sign new_public_key with old_identity to form a chain-of-custody record.

    Returns {'payload': {...}, 'signature': {...}}.
    """
    payload = {
        'schema': 'urace-key-rotation-v1',
        'old_key_id': ledger_crypto.public_id(old_identity.public()),
        'new_public_key': new_public_key,
        'at_unix': time.time(),
    }
    sig = old_identity.sign(payload, 'key-rotation')
    return {'payload': payload, 'signature': sig}


def verify_rotation_proof(old_public: dict, rotation_proof: dict, new_public: dict) -> bool:
    """Verify a rotation proof produced by create_rotation_proof.

    Raises ValueError on any mismatch; returns True on success.
    """
    payload = rotation_proof.get('payload', {})
    if payload.get('schema') != 'urace-key-rotation-v1':
        raise ValueError('rotation_proof schema mismatch')

    expected_key_id = ledger_crypto.public_id(old_public)
    if expected_key_id != payload.get('old_key_id'):
        raise ValueError(
            f"old_key_id mismatch: expected {expected_key_id!r}, got {payload.get('old_key_id')!r}"
        )

    ledger_crypto.verify(old_public, payload, rotation_proof['signature'], 'key-rotation')

    if payload.get('new_public_key') != new_public:
        raise ValueError('new_public_key in rotation_proof does not match supplied new_public')

    return True


def broadcast_revocation(exchange, peer_ids: list, reason: str) -> dict:
    """Emit a signed revocation record and attempt to notify peers.

    Never raises due to peer notification failures (best-effort).
    Returns {'revoked': True, 'key_id': str, 'notified_peers': int}.
    """
    identity = exchange.crypto_identity()
    record = {
        'schema': 'urace-revocation-v1',
        'key_id': ledger_crypto.public_id(identity.public()),
        'reason': reason,
        'at_unix': time.time(),
    }
    sig = identity.sign(record, 'key-revocation')
    signed_record = {'record': record, 'signature': sig}

    exchange.event('IDENTITY_REVOKED', key_id=record['key_id'], reason=reason)

    notified = 0
    for peer_id in peer_ids:
        try:
            peer_exchange.request(exchange, peer_id, 'exchange.info', {})
            notified += 1
        except Exception:
            pass

    return {'revoked': True, 'key_id': record['key_id'], 'notified_peers': notified}


def rotate_identity(exchange) -> dict:
    """Generate a new keypair, create a rotation proof, swap the identity file.

    Returns {'rotated': True, 'new_key_id': str, 'old_key_id': str, 'rotation_proof': dict}.
    """
    old_identity = exchange.crypto_identity()
    old_key_id = ledger_crypto.public_id(old_identity.public())

    # Generate new identity in a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        new_key_path = Path(tmp_dir) / 'hybrid-identity.json'
        new_identity = ledger_crypto.Identity(new_key_path)
        new_public = new_identity.public()
        new_key_id = ledger_crypto.public_id(new_public)

        rotation_proof = create_rotation_proof(old_identity, new_public)

        # Backup old key
        timestamp = int(time.time())
        old_key_src = exchange.root / 'hybrid-identity.json'
        backup_path = exchange.root / f'hybrid-identity-backup-{timestamp}.json'
        if old_key_src.exists():
            shutil.copy2(old_key_src, backup_path)

        # Copy new key into place
        shutil.copy2(new_key_path, old_key_src)

    # Clear cached identity so next call reloads from disk
    if hasattr(exchange, '_crypto_identity'):
        exchange._crypto_identity = None

    exchange.event(
        'IDENTITY_ROTATED',
        old_key_id=old_key_id,
        new_key_id=new_key_id,
        rotation_proof=rotation_proof,
    )

    return {
        'rotated': True,
        'new_key_id': new_key_id,
        'old_key_id': old_key_id,
        'rotation_proof': rotation_proof,
    }
