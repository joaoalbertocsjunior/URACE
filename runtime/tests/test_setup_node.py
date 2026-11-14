"""Tests for exchange_cli: --install-service, setup-node, bootstrap announce."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest


def _make_exchange_and_config(tmp_dir, cfg_extra=None):
    from urace import peer_exchange as pe
    from urace._common import atomic_write_json
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
    if cfg_extra:
        c = e.load()
        c.update(cfg_extra)
        atomic_write_json(exchange_dir / 'policy.json', c)
    return e, config


def _make_args(**kwargs):
    args = MagicMock()
    args.json = True
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


# ── test 1: --install-service writes unit file ────────────────────────────────

def test_install_service_creates_unit_file(tmp_path):
    written = {}

    def fake_write_text(self, content):
        written['path'] = str(self)
        written['content'] = content

    with tempfile.TemporaryDirectory() as tmp_dir:
        exchange, config = _make_exchange_and_config(tmp_dir)
        from urace import exchange_cli

        args = _make_args(
            exchange_group='network', exchange_verb='serve',
            host='0.0.0.0', port=7301, install_service=True,
        )

        with patch.object(Path, 'write_text', fake_write_text), \
             patch.object(Path, 'mkdir', lambda self, **kw: None):
            ret = exchange_cli.run(args, config)

    assert ret == 0
    assert 'urace-exchange.service' in written['path']
    assert 'ExecStart=urace exchange network serve' in written['content']
    assert 'WantedBy=default.target' in written['content']


# ── test 2: setup-node sets roles in policy ───────────────────────────────────

def test_setup_node_sets_roles(tmp_path):
    cap = {
        'nat_type': 'cone',
        'public_ip': '1.2.3.4',
        'upnp_available': True,
        'can_bootstrap': True,
        'can_relay': True,
        'recommended_roles': ['bootstrap', 'relay'],
        'recommended_network_mode': 'internet',
    }

    written = {}

    def fake_atomic_write(path, value):
        written['path'] = path
        written['value'] = dict(value)

    with tempfile.TemporaryDirectory() as tmp_dir:
        exchange, config = _make_exchange_and_config(tmp_dir, {'network_mode': 'hybrid'})
        from urace import exchange_cli

        args = _make_args(exchange_group='network', exchange_verb='setup-node', timeout=5.0)

        with patch('urace.nat_check.check_node_capability', return_value=cap), \
             patch('urace._common.atomic_write_json', side_effect=fake_atomic_write):
            ret = exchange_cli.run(args, config)

    # run() returns None for non-special paths (result is printed)
    assert ret in (0, None)
    assert written['value']['node_roles'] == ['bootstrap', 'relay']
    assert written['value']['network_mode'] == 'internet'


# ── test 3: bootstrap announce uses STUN fallback ─────────────────────────────

def test_bootstrap_announce_stun_fallback():
    stun_result = {'ip': '5.6.7.8', 'port': 7301}

    written = {}

    def fake_atomic_write(path, value):
        written['path'] = path
        written['value'] = dict(value)

    with tempfile.TemporaryDirectory() as tmp_dir:
        exchange, config = _make_exchange_and_config(tmp_dir, {
            'bootstrap_peers': ['https://existing-peer.example.com:7301'],
        })
        from urace import exchange_cli

        args = _make_args(
            exchange_group='bootstrap', exchange_verb='announce',
            endpoint=None, timeout=5.0,
        )

        with patch('urace.stun_client.get_public_address', return_value=stun_result) as mock_stun, \
             patch('urace.peer_exchange.request', return_value={'status': 'ok'}), \
             patch('urace._common.atomic_write_json', side_effect=fake_atomic_write):
            ret = exchange_cli.run(args, config)

    assert ret in (0, None)
    mock_stun.assert_called_once_with('stun.l.google.com', 19302)
    # endpoint constructed from STUN ip:port should be first in peers list
    assert written['value']['bootstrap_peers'][0] == 'https://5.6.7.8:7301'
