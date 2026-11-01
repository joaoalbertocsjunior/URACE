# Config Reference

[← Documentation](../index.md)

All URACE configuration options with their defaults and descriptions.

---

## Exchange Settings

Managed via `urace exchange settings set`.

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Exchange is off until explicitly enabled |
| `network` | `false` | P2P networking off until enabled |
| `advertise` | `false` | LAN advertising off |
| `auto_select` | `true` | Auto-probe pinned peers on startup |
| `token_settlement` | `false` | Token transfers disabled (reputation-only until enabled) |
| `max_transfers_per_day` | `20` | Daily bundle transfer limit |
| `max_rpc_per_day` | `200` | Daily RPC call limit |
| `max_rpc_per_peer_per_day` | `50` | Per-peer daily RPC limit |
| `feature_borrow_enabled` | `true` | P2P is first source for feature requests |

---

## Product Capability Controls

Managed via `urace controls set`.

| Control | Default | Description |
|---------|---------|-------------|
| `executor_enabled` | `true` | Allow executor to run operations |
| `freeform_enabled` | `true` | Enable freeform text routing |
| `p2p_mint_enabled` | `false` | Allow minting features to P2P |
| `p2p_sell_enabled` | `false` | Allow listing features for sale |
| `p2p_borrow_enabled` | `true` | Allow borrowing features from peers |
| `compress_enabled` | `true` | Enable ledger compaction |
| `decompress_enabled` | `true` | Enable ledger decompression |
| `machine_interface_enabled` | `false` | Enable machine-readable JSON interfaces |

---

## Network Security Defaults

These are enforced by the runtime — not configurable to weaker values.

| Property | Value |
|----------|-------|
| Minimum TLS version | 1.3 |
| DHT bootstrap min interval | 5 minutes |
| RPC flood threshold | 10 rejections/hour → auto-block |
| Consensus threshold formula | `max(2, min(10, ceil(10% × all_time_max_peers)))` |

---

## Token Supply Defaults

Used as starting point for `exchange ledger supply-calc`.

| Parameter | Default |
|-----------|---------|
| Baseline grant per peer | 3 tokens |
| Mint per adoption | 0.01 tokens |
| Default adoption rate | 10% of network peers |
| Ledger budget | min(50 MB, bandwidth × sync_secs) |
| Default sync target | 30 seconds |

---

## Update Source

| Setting | Default |
|---------|---------|
| Runtime release URL | Official URACE release endpoint |
| Signature verification | Always on — updates rejected if signature fails |

---

## Related

- [CLI Reference](cli.md) — all commands for setting config
- [Controls Guide](../guides/controls.md) — capability controls in depth
- [Exchange Setup](../exchange/setup.md) — exchange configuration walkthrough
