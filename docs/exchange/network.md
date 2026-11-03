# P2P Network

[← Documentation](../index.md)

Here's how URACE's peer-to-peer network works: discovery, connection, consensus, and audit.

---

## Network Mode {#network-mode}

Network mode controls how far your node reaches on the exchange. Set it once during setup; change it as your deployment grows.

| Mode | Description |
|------|-------------|
| `intranet` | LAN-only — no internet peers, no DHT bootstrap |
| `hybrid` | LAN-first with an optional internet-facing gateway (default) |
| `internet` | Full public deployment — DHT discovery and bootstrap peers |

```sh
urace exchange settings set --network-mode intranet
urace exchange settings set --network-mode hybrid
urace exchange settings set --network-mode internet
```

**Upgrading from intranet to internet**: resolve your public address first, then switch mode:

```sh
urace exchange network public-address
urace exchange settings set --network-mode internet
```

**Hybrid mode with a gateway**: keep most peers on the LAN while one designated peer bridges to the internet:

```sh
urace exchange settings set --network-mode hybrid --internet-gateway <peer-id>
```

---

## Resolve Your Public Address

When moving to internet or hybrid mode, find your external IP and port via STUN:

```sh
urace exchange network public-address
urace exchange network public-address --stun-host stun.example.com --stun-port 3478
```

---

## Peer Roles

Control what each connected peer may do on your node. Roles apply on top of certificate pinning.

| Role | Permissions |
|------|-------------|
| `admin` | Full access — manage rules, settings, and peers |
| `operator` | Run operations and transfer features; cannot change settings |
| `readonly` | Query only — no state-modifying commands |

```sh
# Show a peer's current role
urace exchange peer role <peer_id>

# Set a role
urace exchange peer role <peer_id> --set admin
urace exchange peer role <peer_id> --set operator
urace exchange peer role <peer_id> --set readonly
```

---

## Discover Peers

Find peers on your local network (LAN/DNS-SD) or via DHT bootstrap:

```sh
urace exchange network discover
```

Refresh offers from peers you've already pinned:

```sh
urace exchange network refresh
```

Probe a specific peer to see what they offer:

```sh
urace exchange network probe <peer_id>
```

---

## Start the P2P Listener

To accept incoming connections from peers:

```sh
urace exchange network serve
```

This starts the local P2P listener on the configured port.

---

## Manage Peers

```sh
# Pin a peer by certificate
urace exchange peer add --certificate peer-cert.pem

# List all known peers
urace exchange peer list

# Block a peer
urace exchange peer block <peer_id>

# Unblock a peer
urace exchange peer unblock <peer_id>

# Rotate your identity and migrate rules to a new certificate
urace exchange peer rotate <old_id> --new-certificate new-cert.pem
```

---

## Consensus

URACE uses a consensus threshold to verify corpus updates. The threshold is based on the **persistent all-time maximum** network size — not the current estimate — so an attacker can't lower it by isolating part of the network:

```
threshold = max(2, min(10, ceil(10% × max(current_estimate, all_time_max)))
```

Check current consensus state:

```sh
urace exchange network consensus-status
```

---

## Temporary Disconnect

Pause networking without disabling the exchange:

```sh
# Pause for 60 minutes
urace exchange network disconnect --duration-minutes 60

# Pause indefinitely (until reconnect)
urace exchange network disconnect
```

Reconnect:

```sh
urace exchange network reconnect
```

---

## P2P Audit Trail

Every significant network event is recorded: peer connections, bundle transfers, consensus votes, RPC calls.

```sh
# List all P2P audit events
urace exchange network-audit list

# Filter by kind and peer
urace exchange network-audit list --kind bundle_transfer --peer <peer_id>
```

Audit trail is append-only and searchable via `urace compact search`.

---

## Security Defaults

- TLS 1.3 mandatory on all connections
- Certificate pinning — peers not pinned are not trusted
- RPC flood protection: 10 rejections/hour triggers automatic peer block
- DHT bootstrap rate limiting: minimum 5 minutes between attempts
- IP anonymization: DHT uses hashed node IDs; IPs are not stored in audit trail

See [Peer Security](../security/peer-security.md) for the full security model.

---

## Related

- [Setup](setup.md) — enable networking first
- [Peer Security](../security/peer-security.md) — TLS, post-quantum, quarantine
- [Search Guide](../guides/search.md) — search P2P audit trail
