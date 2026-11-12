"""Tests for HTTP RPC stubs in exchange_cli: find-node, shamir-deliver, tail-sync.
Phase 2.1 — Bootstrap Peer Transport gating on network_mode.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_exchange_and_config(tmp_dir, network_mode='intranet', bootstrap_peers=None):
    """Return (exchange, config) with exchange root pointing to the config-derived directory."""
    from urace import peer_exchange as pe
    from urace._common import atomic_write_json
    # Build a minimal state.json so pe.directory(config) resolves
    state_path = Path(tmp_dir) / 'state.json'
    state_path.write_text(json.dumps({
        'schema_version': 1, 'state_version': 1,
        'objectives': [], 'evidence': [], 'decisions': [],
        'operations': [], 'checkpoints': [], 'blockers': [], 'resource_calls': [],
    }))
    config = {'state_path': str(state_path)}
    exchange_dir = pe.directory(config)
    e = pe.Exchange(exchange_dir)
    e.configure(enabled=True, network=False)
    e.feature('feat', [])
    # Inject network_mode / bootstrap_peers into policy.json via load()+patch
    cfg = e.load()
    cfg['network_mode'] = network_mode
    if bootstrap_peers is not None:
        cfg['bootstrap_peers'] = bootstrap_peers
    # Persist to policy.json so exchange.load() inside run() picks it up
    atomic_write_json(exchange_dir / 'policy.json', cfg)
    return e, config


def _make_args(**kwargs):
    args = MagicMock()
    args.json = True
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


def _fake_urlopen_response(payload: bytes):
    """Return a context-manager mock that reads payload."""
    resp = MagicMock()
    resp.read = MagicMock(return_value=payload)
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class ExchangeRpcStubTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    # ── find-node ─────────────────────────────────────────────────────────────

    def test_find_node_local_only_when_intranet_mode(self):
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(self.tmp.name, network_mode='intranet')
        args = _make_args(
            exchange_group='network',
            exchange_verb='find-node',
            target_peer_id='peer-abc',
        )
        with patch('urllib.request.urlopen') as mock_open:
            exchange_cli.run(args, config)
            mock_open.assert_not_called()
        rows = exchange.audit_rows()
        find_rows = [r for r in rows if r.get('kind') == 'FIND_NODE_REQUESTED']
        self.assertEqual(len(find_rows), 1)
        self.assertEqual(find_rows[0]['target_peer_id'], 'peer-abc')

    def test_find_node_calls_bootstrap_peer_when_online(self):
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(
            self.tmp.name,
            network_mode='internet',
            bootstrap_peers=['https://bp.example.com'],
        )
        args = _make_args(
            exchange_group='network',
            exchange_verb='find-node',
            target_peer_id='peer-xyz',
        )
        payload = json.dumps({'status': 'found', 'peer_id': 'abc'}).encode()
        resp_mock = _fake_urlopen_response(payload)
        with patch('urllib.request.urlopen', return_value=resp_mock) as mock_open:
            exchange_cli.run(args, config)
            self.assertTrue(mock_open.called)
            call_req = mock_open.call_args[0][0]
            self.assertIn('find-node', call_req.full_url)
            self.assertIn('peer-xyz', call_req.full_url)

    def test_find_node_handles_rpc_error_gracefully(self):
        import urllib.error
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(
            self.tmp.name,
            network_mode='internet',
            bootstrap_peers=['https://bp.example.com'],
        )
        args = _make_args(
            exchange_group='network',
            exchange_verb='find-node',
            target_peer_id='peer-xyz',
        )
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError('connection refused')):
            # Must not raise
            exchange_cli.run(args, config)

    # ── shamir-deliver ────────────────────────────────────────────────────────

    def test_shamir_deliver_posts_online(self):
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(
            self.tmp.name,
            network_mode='internet',
            bootstrap_peers=['https://bp.example.com'],
        )
        args = _make_args(
            exchange_group='network',
            exchange_verb='shamir-deliver',
            feature_id='feat-001',
            holder_peer_id='holder-peer',
            share_index=0,
        )
        payload = json.dumps({'status': 'delivered'}).encode()
        resp_mock = _fake_urlopen_response(payload)
        with patch('urllib.request.urlopen', return_value=resp_mock) as mock_open:
            exchange_cli.run(args, config)
            self.assertTrue(mock_open.called)
            call_req = mock_open.call_args[0][0]
            body = json.loads(call_req.data)
            self.assertEqual(body['feature_id'], 'feat-001')
            self.assertEqual(body['holder_peer_id'], 'holder-peer')
            self.assertEqual(body['share_index'], 0)

    def test_shamir_deliver_local_only_when_intranet_mode(self):
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(self.tmp.name, network_mode='intranet')
        args = _make_args(
            exchange_group='network',
            exchange_verb='shamir-deliver',
            feature_id='feat-001',
            holder_peer_id='holder-peer',
            share_index=0,
        )
        with patch('urllib.request.urlopen') as mock_open:
            exchange_cli.run(args, config)
            mock_open.assert_not_called()
        rows = exchange.audit_rows()
        shamir_rows = [r for r in rows if r.get('kind') == 'SHAMIR_DELIVER_REQUESTED']
        self.assertEqual(len(shamir_rows), 1)

    # ── tail-sync ─────────────────────────────────────────────────────────────

    def test_tail_sync_fetches_from_peer_online(self):
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(
            self.tmp.name,
            network_mode='internet',
            bootstrap_peers=['https://bp.example.com'],
        )
        args = _make_args(
            exchange_group='network',
            exchange_verb='tail-sync',
            from_peer_id='some-full-peer',
        )
        payload = json.dumps({'seal': None, 'tail': []}).encode()
        resp_mock = _fake_urlopen_response(payload)
        with patch('urllib.request.urlopen', return_value=resp_mock) as mock_open:
            exchange_cli.run(args, config)
            self.assertTrue(mock_open.called)
            call_req = mock_open.call_args[0][0]
            self.assertIn('ledger-tail', call_req.full_url)

    def test_tail_sync_local_only_when_intranet_mode(self):
        from urace import exchange_cli
        exchange, config = _make_exchange_and_config(self.tmp.name, network_mode='intranet')
        args = _make_args(
            exchange_group='network',
            exchange_verb='tail-sync',
            from_peer_id='some-full-peer',
        )
        with patch('urllib.request.urlopen') as mock_open:
            exchange_cli.run(args, config)
            mock_open.assert_not_called()
