# P2P Network

[← Documentation](../index.md)

Here's how URACE's peer-to-peer network works: discovery, connection, consensus, and audit.

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
