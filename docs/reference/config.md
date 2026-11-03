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
| `network_mode` | `hybrid` | Network reach: `intranet`, `hybrid`, or `internet` |
| `internet_gateway` | — | Peer ID of the internet-facing gateway (hybrid mode only) |
| `auto_select` | `true` | Auto-probe pinned peers on startup |
| `token_settlement` | `false` | Token transfers disabled (reputation-only until enabled) |
| `max_transfers_per_day` | `20` | Daily bundle transfer limit |
| `max_rpc_per_day` | `200` | Daily RPC call limit |
| `max_rpc_per_peer_per_day` | `50` | Per-peer daily RPC limit |
| `feature_borrow_enabled` | `true` | P2P is first source for feature requests |
| `compress_wire` | `false` | Gzip HTTP body on all P2P RPC calls (opt-in; minimal gain on encrypted payloads) |
| `bandwidth_profile` | `auto` | Transfer profile: `auto` (4 KB chunks), `low` (1 KB chunks), `high` (64 KB chunks) |
| `transfer_chunk_size` | `4096` | Override wire read chunk size in bytes (512–131072); overrides `bandwidth_profile` default |
| `consensus_min_threshold` | `2` | Minimum peers required for consensus decisions |
| `baseline_grant_tokens` | `3` | Tokens granted to each new peer on join |
| `listing_ttl_days` | `90` | Days after which a listing with zero adoption is considered expired |

---

## Executor Settings

Configured in the `executor` block of `config.json`.

| Key | Default | Description |
|-----|---------|-------------|
| `max_tokens_per_cycle_warn` | `50000` | Token count above which a KPI warning is logged per cycle |
| `freeform_max_tokens_per_24h` | `200000` | 24h freeform token budget before hard stop |

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
| `compliance_mode` | `false` | Stricter audit logging and governance enforcement |

---

## Product Type

Set via `urace init --type` or `urace product register --type`.

| Type | Description |
|------|-------------|
| `software` | Software development pipeline (default) |
| `content` | Content production pipeline |
| `media` | AI-generated media pipeline |
| `model` | ML training/evaluation pipeline |
| `data` | Data ingestion or transformation pipeline |

`--type` sets executor context hints and default metric suggestions for the improvement cycle.

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

## Inspect All Active Config

Show all resolved configuration values — including the source of each value (default, file, or environment variable):

```sh
urace config show-all
urace config show-all --json
```

Use this after a manual config edit or fleet config push to verify the active state before running improvement cycles.

---

## Context Ledger

| Key | Default | Description |
|-----|---------|-------------|
| `ledger_size_warn_mb` | `50` | Ledger size in MB above which status/doctor warn to run compact |

---

## Related

- [CLI Reference](cli.md) — all commands for setting config
- [Controls Guide](../guides/controls.md) — capability controls in depth
- [Exchange Setup](../exchange/setup.md) — exchange configuration walkthrough
