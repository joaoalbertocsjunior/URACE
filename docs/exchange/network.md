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

## Node Roles

Every node auto-detects its capabilities on first run (`urace init --auto`) and is assigned the best role set it can physically support. Roles are stored in `node_roles` in the exchange policy and can be overridden manually.

| Role | Description | Requirement |
|------|-------------|-------------|
| `bootstrap` | Announces stable address so new peers can join the network | Public IP or stable port-forward; cone or direct NAT |
| `relay` | Forwards traffic between peers that cannot connect directly | Cone NAT + UPnP success, or direct public IP |
| `consumer` | Borrows features and commissions work | Outbound only — always available |
| `creator` | Publishes features for other peers to adopt | Outbound only — always available |

Roles can be combined. `bootstrap + relay` is the most useful combination for a home server. `consumer + creator` is the default for nodes behind strict NAT.

Check and set roles:

```sh
urace exchange network reachability --json       # probe NAT type + UPnP + feasible roles
urace exchange node check --json                 # full capability report
urace exchange node roles --json                 # show current configured roles
urace exchange node roles --set bootstrap,relay  # override auto-assigned roles
```

Auto-detection logic:

| NAT type | UPnP | Auto-assigned roles | `network_mode` |
|----------|------|---------------------|---------------|
| Direct (VPS/server) | n/a | bootstrap + relay + consumer + creator | internet |
| Cone NAT + UPnP success | yes | relay + consumer + creator | hybrid |
| Cone NAT, no UPnP | no | consumer + creator | hybrid |
| Symmetric NAT | no | consumer + creator | hybrid |
| No internet | — | consumer + creator | intranet |

---

## NAT Traversal

When a node is behind NAT, URACE attempts reachability in this order:

1. **UPnP** — automatic port-mapping request to the local gateway; runs on startup when `relay` role is assigned. Requires router UPnP enabled and `miniupnpc` (included in base install).
2. **STUN probe** — determines public IP and NAT type (cone vs symmetric) via `stun.l.google.com`, `stun.cloudflare.com`, `stun.stunprotocol.org`. No single-point-of-failure.
3. **Manual port-forward** — configure TCP external:7301 → local:7301 on the router for stable inbound without UPnP.
4. **DHT relay** — if direct inbound is unavailable, URACE routes through relay-role peers automatically.

Check your current reachability:

```sh
urace exchange network reachability --json
```

Output includes `nat_type` (`direct`/`cone`/`symmetric`/`unknown`), `upnp_available`, `can_bootstrap`, `can_relay`, and `recommended_roles`.

---

## Peer Reputation Persistence

Peer delivery receipts (`QUALIFICATION_RECEIPT`) survive restarts. URACE persists them to `~/.urace/peer_reputation.jsonl` and reloads on startup. The reputation score uses a Wilson 90%-CI lower bound on failure rate — lower is better (0.0 = perfect record). Nodes are ranked by ascending failure rate when selecting peers for work requests.

---

## Security Defaults

- TLS 1.3 mandatory on all connections
- Certificate pinning — peers not pinned are not trusted
- RPC flood protection: 10 rejections/hour triggers automatic peer block
- DHT bootstrap rate limiting: minimum 5 minutes between attempts
- IP anonymization: DHT uses hashed node IDs; IPs are not stored in audit trail

See [Peer Security](../security/peer-security.md) for the full security model.

---

## Bootstrap Peer RPC Endpoints

When `network_mode` is `internet` or `hybrid`, URACE issues live HTTP calls to configured bootstrap peers. Three endpoints are used:

### `GET /urace/rpc/v1/find-node`

Peer routing lookup. Called when the local node needs to locate a specific peer by ID via the Kademlia DHT.

Query parameter: `target_peer_id=<id>`

Returns a JSON object with the routing result.

### `POST /urace/rpc/v1/shamir-deliver`

DEK share delivery. Called when a node needs to deliver an encrypted DEK share to a replica holder during a feature listing flow.

Request body (JSON): `{"feature_id": "...", "holder_peer_id": "...", "share_index": <int>}`

Returns a JSON object confirming delivery status.

### `GET /urace/rpc/v1/ledger-tail`

Fetch the current ledger tail from a full peer. Used by light peers to synchronize their sliding-window view of the audit chain without downloading the full history.

Returns a JSON object with keys `seal` (the latest seal row or `null`) and `tail` (rows since the seal).

These endpoints are only called when `network_mode` is set to `internet` or `hybrid`. In `intranet` mode all three return a local stub response without any network I/O.

---

## Related

- [Setup](setup.md) — enable networking first
- [Peer Security](../security/peer-security.md) — TLS, post-quantum, quarantine
- [Search Guide](../guides/search.md) — search P2P audit trail
- [urace-rpc-v1](../reference/urace-rpc-v1.md) — full RPC contract reference
