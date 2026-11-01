# Exchange Setup

[← Documentation](../index.md)

Here's how to enable the URACE exchange, create your peer identity, and configure settings.

---

## Step 1: Enable the Exchange

The exchange is off by default. Enable it explicitly:

```sh
urace exchange settings set --enabled true
```

Enable P2P networking (so you can discover and connect to peers):

```sh
urace exchange settings set --enabled true --network true
```

Enable LAN advertising (so peers on your local network can discover you):

```sh
urace exchange settings set --enabled true --network true --advertise true
```

---

## Step 2: Create Your Peer Identity

Generate a cryptographic identity for your node:

```sh
urace exchange peer identity
```

This creates a certificate keypair used to authenticate all peer connections. Your peer ID is derived from your certificate.

---

## Step 3: Configure Capabilities

Control what your node does on the network:

```sh
# Enable token settlement (off by default — enables real token transfers)
urace exchange settings set --token-settlement true

# Set daily transfer limits
urace exchange settings set --max-transfers-per-day 50

# Enable auto-probing of pinned peers
urace exchange settings set --auto-select true
```

---

## Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Exchange is off until explicitly enabled |
| `network` | `false` | P2P networking off until enabled |
| `advertise` | `false` | LAN advertising off |
| `auto_select` | `true` | Auto-probe pinned peers on startup |
| `token_settlement` | `false` | Token transfers disabled (reputation-only until enabled) |
| `max_transfers_per_day` | `20` | Daily bundle transfer limit |
| `max_rpc_per_day` | `200` | Daily RPC call limit |
| `max_rpc_per_peer_per_day` | `50` | Per-peer RPC limit |
| `feature_borrow_enabled` | `true` | P2P is first source for feature requests |

Show current settings:

```sh
urace exchange settings show
```

---

## Add Peers

Pin a specific peer by their certificate:

```sh
urace exchange peer add --certificate peer-cert.pem
```

List all pinned peers:

```sh
urace exchange peer list
```

---

## Enable P2P Capabilities in Controls

Make sure your product-level controls allow P2P operations:

```sh
urace controls set --p2p-mint-enabled true --p2p-sell-enabled true --p2p-borrow-enabled true
```

---

## Related

- [Exchange Overview](overview.md) — what the exchange is
- [Features](features.md) — start minting and borrowing
- [Network](network.md) — peer discovery and networking
- [Controls Guide](../guides/controls.md) — product-level capability flags
