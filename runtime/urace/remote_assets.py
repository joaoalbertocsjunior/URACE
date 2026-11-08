"""Authenticated discovery and quarantine delivery for explicitly open P2P assets.

Paid listings are discoverable but are never settled by this module: the current
exchange has no shared, buyer-verifiable cross-peer payment ledger.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time

from . import peer_exchange as pe

CATALOG_SCHEMA = 'urace-public-asset-catalog-v1'
OPEN_ASSET_LIMIT = 300_000  # base64 envelope stays below the bounded RPC limit
CATALOG_LIMIT = 64


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _grant_index(rows: list[dict]) -> dict[str, dict]:
    result = {}
    for row in rows:
        if row.get('kind') == 'EQUITY_GRANT' and row.get('feature_id'):
            result[row['feature_id']] = row
    return result


def public_catalog(exchange: pe.Exchange, recipient: str) -> dict:
    """Return bounded, seller-authenticated metadata visible to a pinned peer."""
    policy = exchange.load()
    if recipient not in policy['peers'] or policy['peers'][recipient]['blocked']:
        raise ValueError('Unknown or blocked catalog recipient')
    rows = exchange.audit_rows()
    grants = _grant_index(rows)
    seller = exchange.identity()['peer_id']
    free_assets = []
    for feature_id, feature in sorted(policy.get('features', {}).items()):
        if not feature.get('offered') or feature_id not in grants:
            continue
        if not exchange.permitted(policy, recipient, feature_id, 'send'):
            continue
        grant = grants[feature_id]
        if grant.get('visibility', 'public') != 'public':
            continue
        artifact_sha = grant.get('artifact_ref')
        if (not isinstance(artifact_sha, str) or len(artifact_sha) != 64
                or any(c not in '0123456789abcdef' for c in artifact_sha)):
            continue
        artifact_size = grant.get('artifact_size_bytes')
        if type(artifact_size) is not int or not 0 <= artifact_size <= OPEN_ASSET_LIMIT:
            continue
        from .feature_policy import effective, validate
        terms = feature.get('distribution_policy')
        if not isinstance(terms, dict):
            continue
        try:
            terms = effective(validate(terms))
        except ValueError:
            continue
        if terms.get('effective_access') != 'open' or terms.get('usage_price_units') != 0:
            continue
        item = {
            'seller_peer_id': seller, 'feature_id': feature_id,
            'description': str(grant.get('description', ''))[:512],
            'spec_context': str(grant.get('spec_context', ''))[:512],
            'tags': [str(x)[:64] for x in (grant.get('tags') or [])[:24] if isinstance(x, str)],
            'dependencies': list(feature.get('dependencies', [])),
            'artifact_sha256': artifact_sha,
            'artifact_size_bytes': artifact_size,
            'content_type': str(grant.get('content_type', 'application/octet-stream'))[:128],
            'license_id': terms['license_id'], 'usage_price_units': 0,
            'payment_enabled': False,
        }
        item['asset_id'] = _sha(_canonical(item))
        free_assets.append(item)
        if len(free_assets) >= CATALOG_LIMIT:
            break

    # Paid ask prices are seller claims in a closed local ledger. They are shown
    # as discovery metadata only and are never converted to executor cost.
    paid_listings = []
    try:
        from .equity_auto_trade import open_listings
        for listing in sorted(open_listings(exchange), key=lambda row: row.get('listing_id', '')):
            feature_id = listing.get('feature_id')
            grant = grants.get(feature_id)
            if (not grant or listing.get('seller_id') != grant.get('peer_id')
                    or type(listing.get('ask_price_units')) is not int or listing['ask_price_units'] <= 0
                    or not exchange.permitted(policy, recipient, feature_id, 'send')):
                continue
            if grant.get('visibility', 'public') != 'public':
                continue
            paid_listings.append({
                'listing_id': listing.get('listing_id'), 'seller_peer_id': seller,
                'feature_id': feature_id, 'description': str(grant.get('description', ''))[:512],
                'tags': [str(x)[:64] for x in (grant.get('tags') or [])[:24] if isinstance(x, str)],
                'artifact_sha256': grant.get('artifact_ref'),
                'ask_price_units': int(listing.get('ask_price_units', 0)),
                'price_unit': 'URACE_LOCAL_REPUTATION_UNITS',
                'settlement_status': 'DISCOVERY_ONLY_NO_CROSS_PEER_SETTLEMENT',
            })
            if len(paid_listings) >= CATALOG_LIMIT:
                break
    except (ValueError, TypeError, OSError):
        paid_listings = []
    return {'schema': CATALOG_SCHEMA, 'seller_peer_id': seller,
            'created_unix': time.time(), 'expires_unix': time.time() + 300,
            'open_assets': free_assets, 'paid_listings': paid_listings,
            'settlement_supported': False,
            'price_interpretation': 'Seller ask prices are local reputation units, not executor-cost observations.'}


def validate_catalog(value: dict, peer_id: str) -> dict:
    if (not isinstance(value, dict) or value.get('schema') != CATALOG_SCHEMA
            or value.get('seller_peer_id') != peer_id
            or type(value.get('created_unix')) not in (int, float)
            or type(value.get('expires_unix')) not in (int, float)
            or not value['created_unix'] <= time.time() <= value['expires_unix'] <= value['created_unix'] + 360):
        raise ValueError('Invalid or expired seller catalog')
    for category in ('open_assets', 'paid_listings'):
        rows = value.get(category)
        if not isinstance(rows, list) or len(rows) > CATALOG_LIMIT:
            raise ValueError('Catalog count exceeded')
    seen = set()
    for item in value['open_assets']:
        if not isinstance(item, dict):
            raise ValueError('Invalid open asset entry')
        asset_id = item.get('asset_id')
        unsigned = {k: v for k, v in item.items() if k != 'asset_id'}
        if not isinstance(asset_id, str) or asset_id != _sha(_canonical(unsigned)) or asset_id in seen:
            raise ValueError('Open asset identity mismatch')
        seen.add(asset_id)
        artifact_sha = item.get('artifact_sha256')
        if not isinstance(artifact_sha, str) or len(artifact_sha) != 64 or any(c not in '0123456789abcdef' for c in artifact_sha):
            raise ValueError('Invalid artifact digest')
        try:
            pe.check_id(item.get('feature_id'))
        except (ValueError, TypeError) as error:
            raise ValueError('Invalid open asset feature identity') from error
        if not isinstance(item.get('dependencies'), list) or len(item['dependencies']) > 32:
            raise ValueError('Invalid open asset dependency list')
        for dependency in item['dependencies']:
            pe.check_id(dependency)
        if (item.get('usage_price_units') != 0 or item.get('payment_enabled') is not False
                or item.get('seller_peer_id') != peer_id or not item.get('license_id')):
            raise ValueError('Asset is not declared open and free for use')
        if type(item.get('artifact_size_bytes')) is not int or not 0 <= item['artifact_size_bytes'] <= OPEN_ASSET_LIMIT:
            raise ValueError('Open asset exceeds supported bounded transfer size')
    for item in value['paid_listings']:
        if (not isinstance(item, dict) or item.get('seller_peer_id') != peer_id
                or type(item.get('ask_price_units')) is not int or item['ask_price_units'] <= 0
                or item.get('settlement_status') != 'DISCOVERY_ONLY_NO_CROSS_PEER_SETTLEMENT'
                or item.get('price_unit') != 'URACE_LOCAL_REPUTATION_UNITS'
                or not isinstance(item.get('listing_id'), str)
                or not isinstance(item.get('feature_id'), str)):
            raise ValueError('Invalid paid listing discovery record')
    return value


def _make_open_bundle(exchange: pe.Exchange, recipient: str, asset_id: str) -> dict:
    catalog = public_catalog(exchange, recipient)
    item = next((row for row in catalog['open_assets'] if row['asset_id'] == asset_id), None)
    if item is None:
        raise ValueError('Open asset is no longer available to this peer')
    raw = exchange.artifact_bytes(item['artifact_sha256'])
    if raw is None or _sha(raw) != item['artifact_sha256']:
        raise ValueError('Seller artifact is missing or its digest does not match')
    if len(raw) > OPEN_ASSET_LIMIT:
        raise ValueError('Open asset exceeds bounded one-RPC transfer limit')
    feature_id = item['feature_id']
    prepared = exchange.prepare(recipient, feature_id, raw, True, content_type=item['content_type'])
    bundle = exchange.inspect(prepared['bundle_id'])['bundle']
    payload = dict(bundle['payload'])
    payload.pop('artifact', None)
    payload['artifact_b64'] = base64.b64encode(raw).decode('ascii')
    # The bytes and license/recipient terms are covered by the seller's signature.
    bundle = {'payload': payload, 'signature': exchange.sign(payload)}
    if len(pe.encoded(bundle)) > pe.LIMIT - 8192:
        raise ValueError('Signed artifact envelope exceeds safe RPC response size')
    bundle_id = pe.digest(bundle)
    reserved_bytes = len(pe.encoded(bundle)) + 8192  # encrypted RPC envelope overhead allowance
    with exchange.lock():
        exchange.budget(recipient, reserved_bytes)
        exchange.event('SEND_RESERVED', peer=recipient, bytes=reserved_bytes,
                       bundle=bundle_id, feature=feature_id, transport='bounded_open_asset_fetch')
    pe.atomic(exchange.root / 'outbox' / (bundle_id + '.json'), bundle)
    exchange.event('OPEN_ASSET_BUNDLE_PREPARED', peer=recipient, feature=feature_id,
                   asset_id=asset_id, bundle=bundle_id, artifact_sha256=item['artifact_sha256'])
    return bundle


def _validate_open_bundle(exchange: pe.Exchange, peer_id: str, bundle: dict) -> tuple[dict, bytes]:
    policy = exchange.load()
    if peer_id not in policy['peers'] or policy['peers'][peer_id]['blocked']:
        raise ValueError('Unknown or blocked asset seller')
    if len(pe.encoded(bundle)) > pe.LIMIT or not isinstance(bundle, dict) or set(bundle) != {'payload', 'signature'}:
        raise ValueError('Invalid or oversized signed asset bundle')
    payload = bundle['payload']
    if (not isinstance(payload, dict) or payload.get('schema') != pe.SCHEMA
            or payload.get('sender') != peer_id
            or payload.get('recipient') != exchange.identity()['peer_id']):
        raise ValueError('Asset sender or recipient does not match pinned exchange peers')
    from .feature_policy import effective, validate
    terms = payload.get('distribution_terms')
    if not isinstance(terms, dict) or type(payload.get('created_unix')) not in (int, float):
        raise ValueError('Asset distribution terms are malformed')
    normalized = validate({key: terms[key] for key in ('schema', 'access', 'license_id', 'essential', 'open_after_unix', 'resale')})
    if terms != effective(normalized, payload.get('created_unix')) or terms.get('effective_access') != 'open' or terms.get('usage_price_units') != 0:
        raise ValueError('Asset does not carry currently effective open-use terms')
    try:
        raw = base64.b64decode(payload['artifact_b64'], validate=True)
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError('Asset bytes are missing or invalid base64') from error
    if len(raw) > OPEN_ASSET_LIMIT or hashlib.sha256(raw).hexdigest() != payload.get('artifact_ref'):
        raise ValueError('Asset bytes exceed limit or fail the signed artifact digest')
    try:
        from .ledger_crypto import verify
        verify(exchange.trusted_crypto(policy, peer_id), payload, bundle['signature'], 'peer-bundle')
    except Exception as error:
        raise ValueError('Asset bundle seller signature is invalid') from error
    return payload, raw


def receive_open_bundle(exchange: pe.Exchange, peer_id: str, bundle: dict) -> dict:
    """Explicitly requested open asset receive; store only in quarantine."""
    payload, _ = _validate_open_bundle(exchange, peer_id, bundle)
    feature_id = pe.check_id(payload['feature'])
    dependencies = payload['dependencies']
    if not isinstance(dependencies, list) or len(dependencies) > 32:
        raise ValueError('Invalid dependency contract')
    policy = exchange.load()
    if feature_id in policy['features']:
        if policy['features'][feature_id]['dependencies'] != dependencies:
            raise ValueError('Local feature dependency contract conflicts with seller bundle')
    for dependency in dependencies:
        if dependency not in policy['features'] or not exchange.permitted(policy, peer_id, dependency, 'receive'):
            raise ValueError('Every dependency must be locally declared and permitted before fetching')
    if not exchange.permitted(policy, peer_id, feature_id, 'receive'):
        # The explicit fetch command is consent to receive this open asset only;
        # applying or executing it remains separately gated.
        if feature_id not in policy['features']:
            exchange.feature(feature_id, dependencies)
        exchange.rule(peer_id, feature_id, 'receive', True)
    return exchange.receive(bundle, authenticated_peer=peer_id)


def fetch_open_asset(exchange: pe.Exchange, peer_id: str, asset_id: str) -> dict:
    """Fetch a seller-attested open asset and quarantine it without executing it."""
    metrics = []
    catalog_metric = {}
    catalog = validate_catalog(pe.request(exchange, peer_id, 'exchange.assets.catalog', {},
                                           telemetry=catalog_metric), peer_id)
    metrics.append(catalog_metric)
    if not any(item.get('asset_id') == asset_id for item in catalog['open_assets']):
        raise ValueError('Asset is not present in the seller current open catalog')
    fetch_metric = {}
    bundle = pe.request(exchange, peer_id, 'exchange.assets.fetch', {'asset_id': asset_id},
                        telemetry=fetch_metric)
    metrics.append(fetch_metric)
    received = receive_open_bundle(exchange, peer_id, bundle)
    try:
        ack_metric = {}
        try:
            seller_ack = pe.request(exchange, peer_id, 'exchange.assets.receipt',
                                    {'asset_id': asset_id, 'status': received['status'],
                                     'receipt': received['receipt']}, telemetry=ack_metric)
        finally:
            if ack_metric:
                metrics.append(ack_metric)
        accept_seller_ack(exchange, peer_id, asset_id, received, seller_ack)
        return {**received, 'seller_ack': seller_ack,
                'network_metrics': _network_summary(metrics)}
    except (ValueError, OSError, TypeError, KeyError) as error:
        # Local quarantine has already succeeded. Preserve that fact while
        # flagging the seller-side acknowledgement as absent.
        return {**received, 'seller_ack': {'status': 'UNCONFIRMED',
                                            'reason': type(error).__name__},
                'network_metrics': _network_summary(metrics)}


def record_quarantine_receipt(exchange: pe.Exchange, peer_id: str, params: dict) -> dict:
    """Verify the buyer's signed quarantine receipt and bind it to a seller send."""
    if not isinstance(params, dict) or set(params) != {'asset_id', 'status', 'receipt'}:
        raise ValueError('Invalid quarantine receipt acknowledgement')
    if params['status'] not in ('QUARANTINED', 'ALREADY_QUARANTINED'):
        raise ValueError('Only a confirmed quarantined delivery can be acknowledged')
    envelope = params['receipt']
    if not isinstance(envelope, dict) or set(envelope) != {'payload', 'signature'}:
        raise ValueError('Signed buyer receipt required')
    payload = envelope['payload']
    if not isinstance(payload, dict):
        raise ValueError('Invalid buyer receipt payload')
    from .ledger_crypto import verify
    with exchange.lock():
        rows = exchange.audit_rows()
        prepared = [row for row in rows if row.get('kind') == 'OPEN_ASSET_BUNDLE_PREPARED'
                    and row.get('bundle') == payload.get('bundle_id')]
        if len(prepared) != 1:
            raise ValueError('No unique seller bundle preparation matches the receipt')
        prepared_event = prepared[0]
        expected = {'schema': 'urace-delivery-receipt-v1',
                    'bundle_id': prepared_event['bundle'], 'sender': exchange.identity()['peer_id'],
                    'recipient': peer_id, 'feature': prepared_event['feature'],
                    'artifact_sha256': prepared_event['artifact_sha256'],
                    'claim': 'BYTES_QUARANTINED_NOT_QUALIFIED'}
        if (prepared_event.get('asset_id') != params['asset_id'] or prepared_event.get('peer') != peer_id
                or payload != expected or params['status'] not in ('QUARANTINED', 'ALREADY_QUARANTINED')):
            raise ValueError('Buyer receipt does not match the prepared seller asset')
        verify(exchange.trusted_crypto(exchange.load(), peer_id), expected,
               envelope['signature'], 'delivery-receipt')
        prior = [row for row in rows if row.get('kind') == 'OPEN_ASSET_QUARANTINE_ACK'
                 and row.get('bundle') == expected['bundle_id'] and row.get('peer') == peer_id]
        if len(prior) > 1 or (prior and prior[0].get('buyer_receipt') != envelope):
            raise ValueError('Conflicting or duplicate buyer receipt for this bundle')
        event = prior[0] if prior else exchange.event(
            'OPEN_ASSET_QUARANTINE_ACK', peer=peer_id, feature=expected['feature'],
            asset_id=params['asset_id'], bundle=expected['bundle_id'],
            artifact_sha256=expected['artifact_sha256'], buyer_status=params['status'],
            buyer_receipt=envelope)
        attestation_payload = {
            'schema': 'urace-open-asset-seller-ack-v1', 'bundle_id': expected['bundle_id'],
            'asset_id': params['asset_id'], 'seller_peer_id': exchange.identity()['peer_id'],
            'buyer_peer_id': peer_id, 'artifact_sha256': expected['artifact_sha256'],
            'buyer_receipt_sha256': _sha(_canonical(envelope)),
            'seller_audit_event_sha256': event['sha256'], 'buyer_status': event['buyer_status'],
        }
        attested_rows = [row for row in rows if row.get('kind') == 'OPEN_ASSET_QUARANTINE_ACK_ATTESTED'
                         and row.get('bundle') == expected['bundle_id'] and row.get('peer') == peer_id]
        if len(attested_rows) > 1:
            raise ValueError('Multiple seller acknowledgement attestations exist for this bundle')
        if attested_rows:
            attestation = attested_rows[0].get('seller_attestation')
            if not isinstance(attestation, dict) or attestation.get('payload') != attestation_payload:
                raise ValueError('Stored seller acknowledgement conflicts with the buyer receipt')
            verify(exchange.crypto_identity().public(), attestation_payload,
                   attestation.get('signature'), 'open-asset-seller-ack')
        else:
            attestation = {'payload': attestation_payload,
                           'signature': exchange.crypto_identity().sign(attestation_payload,
                                                                       'open-asset-seller-ack')}
            exchange.event('OPEN_ASSET_QUARANTINE_ACK_ATTESTED', peer=peer_id,
                           feature=expected['feature'], asset_id=params['asset_id'],
                           bundle=expected['bundle_id'], seller_attestation=attestation)
    return {'status': 'BUYER_QUARANTINE_RECEIPT_VERIFIED', 'bundle_id': expected['bundle_id'],
            'audit_event_sha256': event['sha256'], 'claim': expected['claim'],
            'settlement': 'NONE_OPEN_LICENSE_TRANSFER', 'seller_attestation': attestation}


def accept_seller_ack(exchange: pe.Exchange, peer_id: str, asset_id: str,
                      received: dict, seller_ack: dict) -> dict:
    """Verify and durably record a portable seller-signed quarantine acknowledgement."""
    if not isinstance(received, dict) or not isinstance(seller_ack, dict):
        raise ValueError('Received bundle and seller acknowledgement are required')
    bundle_id = received.get('bundle_id')
    bundle = exchange.inspect(bundle_id)['bundle']
    payload = bundle.get('payload', {})
    receipt = received.get('receipt')
    attestation = seller_ack.get('seller_attestation')
    if not isinstance(receipt, dict) or not isinstance(attestation, dict):
        raise ValueError('Signed buyer receipt and seller acknowledgement are required')
    ack_payload = attestation.get('payload')
    attestation_payload = attestation.get('payload')
    expected = {
        'schema': 'urace-open-asset-seller-ack-v1', 'bundle_id': bundle_id,
        'asset_id': asset_id, 'seller_peer_id': peer_id,
        'buyer_peer_id': exchange.identity()['peer_id'],
        'artifact_sha256': payload.get('artifact_ref'),
        'buyer_receipt_sha256': _sha(_canonical(receipt)),
        'seller_audit_event_sha256': seller_ack.get('audit_event_sha256'),
        'buyer_status': attestation_payload.get('buyer_status') if isinstance(attestation_payload, dict) else None,
    }
    if (seller_ack.get('status') != 'BUYER_QUARANTINE_RECEIPT_VERIFIED'
            or seller_ack.get('bundle_id') != bundle_id or ack_payload != expected):
        raise ValueError('Seller acknowledgement does not match the quarantined bundle')
    if expected['buyer_status'] not in ('QUARANTINED', 'ALREADY_QUARANTINED'):
        raise ValueError('Seller acknowledgement lacks a confirmed quarantine status')
    from .ledger_crypto import verify
    verify(exchange.trusted_crypto(exchange.load(), peer_id), expected,
           attestation.get('signature'), 'open-asset-seller-ack')
    with exchange.lock():
        rows = exchange.audit_rows()
        prior = [row for row in rows if row.get('kind') == 'OPEN_ASSET_SELLER_ACK_RECEIVED'
                 and row.get('bundle') == bundle_id and row.get('peer') == peer_id]
        if prior:
            if len(prior) != 1 or prior[0].get('seller_attestation') != attestation:
                raise ValueError('Conflicting duplicate seller acknowledgement')
            event = prior[0]
        else:
            event = exchange.event('OPEN_ASSET_SELLER_ACK_RECEIVED', peer=peer_id,
                                   asset_id=asset_id, bundle=bundle_id,
                                   artifact_sha256=payload.get('artifact_ref'),
                                   buyer_status=received.get('status'),
                                   buyer_receipt=receipt, seller_attestation=attestation)
    return {'status': 'SELLER_ACK_VERIFIED_AND_RECORDED', 'event_sha256': event['sha256']}


def discover(exchange: pe.Exchange, *, query: str = '', peer_limit: int = 3) -> dict:
    """Search catalogs from currently pinned, unblocked peers; no model calls."""
    if type(peer_limit) is not int or not 1 <= peer_limit <= 10:
        raise ValueError('peer_limit must be between 1 and 10')
    policy = exchange.load()
    peers = [peer for peer, item in sorted(policy['peers'].items())
             if not item.get('blocked') and item.get('endpoint')][:peer_limit]
    terms = {word.casefold() for word in query.split() if len(word) > 1}
    started = time.monotonic()
    assets, paid, failures, network_metrics = [], [], [], []
    for peer in peers:
        try:
            metric = {}
            catalog = validate_catalog(pe.request(exchange, peer, 'exchange.assets.catalog', {},
                                                   telemetry=metric), peer)
            network_metrics.append(metric)
            for category, target in (('open_assets', assets), ('paid_listings', paid)):
                for item in catalog[category]:
                    text = ' '.join(str(item.get(key, '')) for key in ('feature_id', 'description', 'spec_context', 'tags')).casefold()
                    score = (sum(1 for word in terms if word in text) / len(terms)) if terms else 0.0
                    if not terms or score > 0:
                        target.append({**item, 'match_score': round(score, 4), 'source': 'PINNED_SELLER_RPC'})
        except (ValueError, OSError, TypeError, KeyError) as error:
            failures.append({'peer_id': peer, 'reason': type(error).__name__})
    assets.sort(key=lambda item: (-item['match_score'], item['seller_peer_id'], item['feature_id']))
    paid.sort(key=lambda item: (-item['match_score'], item['ask_price_units'], item['seller_peer_id']))
    return {'schema': CATALOG_SCHEMA, 'query': query, 'open_assets': assets,
            'paid_listings': paid, 'peer_failures': failures,
            'native_model_calls': 0, 'automatic_execution': False,
            'paid_borrow_enabled': False,
            'network_metrics': _network_summary(network_metrics, elapsed_seconds=time.monotonic()-started),
            'cost_comparison': 'UNQUALIFIED; ask prices are not executor-cost evidence'}


def _network_summary(metrics: list[dict], *, elapsed_seconds: float | None = None) -> dict:
    return {
        'accounting_scope': 'HTTP application payload bytes; excludes TLS/TCP/IP framing',
        'rpc_calls': len(metrics),
        'request_payload_bytes': sum(int(row.get('request_payload_bytes', 0)) for row in metrics),
        'response_payload_bytes': sum(int(row.get('response_payload_bytes', 0)) for row in metrics),
        'application_payload_bytes': sum(int(row.get('application_payload_bytes', 0)) for row in metrics),
        'rpc_elapsed_seconds': sum(float(row.get('elapsed_seconds', 0)) for row in metrics),
        'elapsed_seconds': elapsed_seconds if elapsed_seconds is not None else sum(float(row.get('elapsed_seconds', 0)) for row in metrics),
        'calls': metrics,
    }
