# Exchange Setup

[← Documentation](../index.md)

Here's how to enable the URACE exchange, create your peer identity, and configure settings.

---

## Step 1: Enable the Exchange

The exchange is **on by default** (`enabled=true`, `network=true`). No command needed to start connecting to peers.

To enable LAN advertising (so peers on your local network can discover you explicitly):

```sh
urace network settings set --advertise true
```

To disable the exchange entirely:

```sh
urace network settings set --enabled false
```

To disable internet P2P while keeping local-only exchange:

```sh
urace network settings set --network false
```

---

## Step 2: Create Your Peer Identity

Generate a cryptographic identity for your node:

```sh
urace network peer identity
```

This creates a certificate keypair used to authenticate all peer connections. Your peer ID is derived from your certificate.

---

## Step 3: Choose a Network Mode

Network mode controls how far your node reaches. The default (`hybrid`) works for most teams:

| Mode | When to use |
|------|-------------|
| `intranet` | Air-gapped or fully private LAN — no internet peers |
| `hybrid` | LAN-first with optional internet gateway (default) |
| `internet` | Fully public deployment with DHT discovery |

```sh
# Default — no action needed. Or set explicitly:
urace network settings set --network-mode hybrid

# Private/air-gapped team:
urace network settings set --network-mode intranet

# Ready to connect to the wider public network:
urace network settings set --network-mode internet
```

**Upgrading from intranet to internet**: First resolve your public address via STUN, then optionally designate one peer as the internet-facing gateway:

```sh
urace network network public-address
urace network settings set --network-mode internet
# Or in hybrid mode, set a gateway peer:
urace network settings set --network-mode hybrid --internet-gateway <peer-id>
```

---

## Step 4: Configure Capabilities

Control what your node does on the network:

```sh
# Enable token settlement (off by default — enables real token transfers)
urace network settings set --token-settlement true

# Set daily transfer limits
urace network settings set --max-transfers-per-day 50

# Enable auto-probing of pinned peers
urace network settings set --auto-select true

# Set minimum peers required for consensus decisions (default: 2)
urace network settings set --consensus-min-threshold 3

# Override baseline token grant per new peer
urace network settings set --baseline-grant-tokens 500
```

---

## Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `true` | Exchange on by default |
| `network` | `true` | P2P networking on by default |
| `advertise` | `false` | LAN advertising off (opt-in) |
| `network_mode` | `hybrid` | Network reach: `intranet`, `hybrid`, or `internet` |
| `internet_gateway` | — | Peer ID of the internet-facing gateway (hybrid mode) |
| `auto_select` | `true` | Auto-probe pinned peers on startup |
| `token_settlement` | `false` | Token transfers disabled (opt-in) |
| `feature_borrow_enabled` | `false` | Peers cannot borrow your features (opt-in) |
| `max_transfers_per_day` | `20` | Daily bundle transfer limit |
| `max_rpc_per_day` | `200` | Daily RPC call limit |
| `max_rpc_per_peer_per_day` | `50` | Per-peer RPC limit |
| `consensus_min_threshold` | `2` | Minimum peers for consensus decisions |
| `baseline_grant_tokens` | `3` | Tokens granted to each new peer on join |
| `mime_policy` | `quality_gate_only` | **Currently network-locked** — only `quality_gate_only` is accepted at the protocol level (source code + structured data); per-node configuration has no effect until `NETWORK_MIME_POLICY` in `mime_policy.py` is relaxed (temporary restriction) |

Show current settings:

```sh
urace network settings show
```

---

## Add Peers

Pin a specific peer by their certificate:

```sh
urace network peer add --certificate peer-cert.pem
```

List all pinned peers:

```sh
urace network peer list
```

---

## Enable P2P Capabilities in Controls

By default, your node connects to the network but does not share, borrow, mint, or sell anything. Each capability requires an explicit opt-in:

```sh
# Allow peers to borrow your features
urace network settings set --feature-borrow-enabled true

# Allow your node to borrow features from peers
urace controls set --p2p-borrow-enabled true

# Enable minting improvements to the P2P network
urace controls set --p2p-mint-enabled true

# Enable selling features to peers
urace controls set --p2p-sell-enabled true

# Enable token settlement for real transfers
urace network settings set --token-settlement true
```

### P2P Configuration for Product Improvement

If you want URACE to use the P2P network when evolving your product (borrowing proven features, contributing improvements back), enable these:

```sh
# Borrow from peers when improving your product
urace controls set --p2p-borrow-enabled true

# Contribute your product improvements back to the network
urace controls set --p2p-mint-enabled true

# Then run your product work loop normally — freeform goals and improvement
# cycles will automatically consider and surface P2P assets
urace "Improve checkout latency to under 200ms"
```

### Bootstrap + Relay Node

All new nodes default to `bootstrap + relay + delivery + block_sealer` roles. No manual role assignment needed unless overriding. When behind NAT, `urace start` automatically establishes an SSH tunnel (localhost.run) so the node can serve as bootstrap and relay without router configuration.

```sh
# 1. (Optional) Override roles — defaults already include bootstrap, relay, delivery, block_sealer
urace network node roles --set bootstrap,relay,delivery,block_sealer

# 2. Start the server — --tunnel auto detects NAT and uses SSH tunnel when needed
urace network network serve --host 0.0.0.0 --port 7301 --tunnel auto

# 3. Verify reachability (active_tunnel_endpoint overrides NAT-based can_bootstrap)
urace network network reachability --json

# 4. Monitor connected peers
urace network network peers --detail
```

---

## Related

- [Exchange Overview](exchange-overview.md) — what the exchange is
- [Features](exchange-features.md) — start minting and borrowing
- [Network](exchange-network.md) — peer discovery and networking
- [Controls Guide](controls.md) — product-level capability flags

---
→ [Next: Exchange Features](exchange-features.md) — mint, borrow, and trade features
