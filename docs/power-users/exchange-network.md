# P2P Network

[← Documentation](../index.md)

Here's how URACE's peer-to-peer network works: discovery, connection, consensus, and audit.

---

## Pick Your Setup

| Your situation | Best option | Why |
|----------------|-------------|-----|
| VPS / server with public IP | No tunnel needed — use `internet` mode | Direct inbound; most reliable bootstrap/relay |
| Home router, want permanent URL | cloudflared named tunnel | Free Cloudflare account; URL never changes across reboots |
| Home router, quick start | `--tunnel auto` (SSH via localhost.run) | Zero install, zero account; URL changes on reconnect but peers are notified automatically |
| Corp firewall / no outbound SSH | cloudflared named tunnel | HTTPS only; SSH may be blocked |
| Home router, no third-party services | Port-forward + DuckDNS | Full control; free DDNS; most stable after setup |
| LAN-only deployment | `intranet` mode | No external services contacted |

---

## Network Mode {#network-mode}

Network mode controls how far your node reaches on the exchange. Set it once during setup; change it as your deployment grows.

| Mode | Description |
|------|-------------|
| `intranet` | LAN-only — no internet peers, no DHT bootstrap |
| `hybrid` | LAN-first with an optional internet-facing gateway (default) |
| `internet` | Full public deployment — DHT discovery and bootstrap peers |

```sh
urace network settings set --network-mode intranet
urace network settings set --network-mode hybrid
urace network settings set --network-mode internet
```

**Upgrading from intranet to internet**: resolve your public address first, then switch mode:

```sh
urace network network public-address
urace network settings set --network-mode internet
```

**Hybrid mode with a gateway**: keep most peers on the LAN while one designated peer bridges to the internet:

```sh
urace network settings set --network-mode hybrid --internet-gateway <peer-id>
```

---

## Resolve Your Public Address

When moving to internet or hybrid mode, find your external IP and port via STUN:

```sh
urace network network public-address
urace network network public-address --stun-host stun.example.com --stun-port 3478
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
urace network peer role <peer_id>

# Set a role
urace network peer role <peer_id> --set admin
urace network peer role <peer_id> --set operator
urace network peer role <peer_id> --set readonly
```

---

## Discover Peers

Find peers on your local network (LAN/DNS-SD) or via DHT bootstrap:

```sh
urace network network discover
```

Refresh offers from peers you've already pinned:

```sh
urace network network refresh
```

Probe a specific peer to see what they offer:

```sh
urace network network probe <peer_id>
```

---

## Start the P2P Listener

To accept incoming connections from peers:

```sh
urace network network serve
```

This starts the local P2P listener on the configured port.

---

## Manage Peers

```sh
# Pin a peer by certificate
urace network peer add --certificate peer-cert.pem

# List all known peers
urace network peer list

# Block a peer
urace network peer block <peer_id>

# Unblock a peer
urace network peer unblock <peer_id>

# Rotate your identity and migrate rules to a new certificate
urace network peer rotate <old_id> --new-certificate new-cert.pem
```

---

## Consensus

URACE uses a consensus threshold to verify corpus updates. The threshold is based on the **persistent all-time maximum** network size — not the current estimate — so an attacker can't lower it by isolating part of the network:

```
threshold = max(2, min(10, ceil(10% × max(current_estimate, all_time_max)))
```

Check current consensus state:

```sh
urace network network consensus-status
```

---

## Temporary Disconnect

Pause networking without disabling the exchange:

```sh
# Pause for 60 minutes
urace network network disconnect --duration-minutes 60

# Pause indefinitely (until reconnect)
urace network network disconnect
```

Reconnect:

```sh
urace network network reconnect
```

---

## P2P Audit Trail

Every significant network event is recorded: peer connections, bundle transfers, consensus votes, RPC calls.

```sh
# List all P2P audit events
urace network network-audit list

# Filter by kind and peer
urace network network-audit list --kind bundle_transfer --peer <peer_id>
```

Audit trail is append-only and searchable via `urace compact search`.

---

## Node Roles

Every node auto-detects its capabilities on first run (`urace init --auto`) and is assigned the best role set it can physically support. Roles are stored in `node_roles` in the exchange policy and can be overridden manually.

| Role | Description | Requirement | Default |
|------|-------------|-------------|---------|
| `bootstrap` | Announces stable address so new peers can join the network | Public IP, port-forward, or SSH tunnel (auto-configured) | ✓ |
| `relay` | Forwards traffic between peers that cannot connect directly | Same as bootstrap — tunnel satisfies this automatically | ✓ |
| `delivery` | Serves artifact bundles to buyers; earns delivery relay credit | Outbound only — always available | ✓ |
| `block_sealer` | Seals ledger blocks and earns seal rewards | Outbound only — always available | ✓ |
| `consumer` | Borrows features and commissions work | Outbound only — always available | (implicit) |
| `creator` | Publishes features for other peers to adopt | Outbound only — always available | (implicit) |
| `verifier` | Runs LLM similarity checks for peer rewards | Executor credits required | opt-in |

Default roles for all new nodes are `bootstrap + relay + delivery + block_sealer`. When direct inbound is blocked by NAT, `urace start` automatically establishes a localhost.run SSH tunnel so the node can serve as bootstrap and relay without router configuration.

Check and set roles:

```sh
urace network network reachability --json                             # probe NAT type + UPnP + feasible roles
urace network node check --json                                       # full capability report
urace network node roles --json                                       # show current configured roles
urace network node roles --set bootstrap,relay,delivery,block_sealer  # override auto-assigned roles
```

Auto-detection logic:

| NAT type | Tunnel needed | Effective roles | `network_mode` |
|----------|--------------|-----------------|---------------|
| Direct (VPS/server) | no | bootstrap + relay + consumer + creator | internet |
| Cone NAT + UPnP | no | bootstrap + relay + consumer + creator | hybrid |
| Cone NAT, no UPnP | auto (localhost.run SSH) | bootstrap + relay + consumer + creator | hybrid |
| Symmetric NAT | auto (localhost.run SSH) | bootstrap + relay + consumer + creator | hybrid |
| No internet | — | consumer + creator | intranet |

---

## NAT Traversal

When a node is behind NAT, URACE attempts reachability in this order:

1. **UPnP** — automatic port-mapping request to the local gateway. Requires router UPnP enabled and `miniupnpc` (included in base install).
2. **STUN probe** — determines public IP and NAT type (cone vs symmetric) via `stun.l.google.com`, `stun.cloudflare.com`, `stun.stunprotocol.org`. No single-point-of-failure.
3. **Cloudflare Tunnel (preferred when available)** — if `cloudflared` is installed and authenticated, URACE uses a named tunnel (`urace-<peer_id>`) with a **permanent URL** that survives restarts and reconnects. Zero URL churn. See [Permanent URL via cloudflared](#permanent-url-via-cloudflared) below.
4. **SSH tunnel (auto fallback)** — when cloudflared is unavailable, URACE creates a localhost.run reverse SSH tunnel (no account, no install required). URL changes on each reconnect; active peers are notified automatically.
5. **Direct port-forward** — configure TCP external:7301 → local:7301 on the router for a stable tunnel-free URL. Use `urace network network setup-port-forward` to get router-specific instructions and optional DDNS setup.
6. **DHT relay** — traffic routed through relay-role peers for symmetric NAT where tunnels are also insufficient.

Tunnel auto mode runs cloudflared and localhost.run in parallel when both are available — if one drops, the other keeps serving.

Check your current reachability:

```sh
urace network network reachability --json
```

Output includes `nat_type` (`direct`/`cone`/`symmetric`/`unknown`), `upnp_available`, `can_bootstrap`, `can_relay`, `recommended_roles`, and — when a tunnel is active — `active_tunnel_endpoint` with updated `can_bootstrap: true` / `can_relay: true`.

---

## Permanent URL via cloudflared

A named cloudflared tunnel gives your bootstrap/relay node a URL that **never changes** — no peer confusion on reconnect, no session drops.

**One-time setup:**

```sh
# 1. Install cloudflared (once)
curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o ~/.local/bin/cloudflared && chmod +x ~/.local/bin/cloudflared

# 2. Authenticate with your Cloudflare account (opens browser)
cloudflared tunnel login

# 3. Run — URACE auto-creates a named tunnel for this node
urace network network serve --tunnel auto --port 7301
```

After `cloudflared tunnel login`, URACE automatically creates a tunnel named `urace-<peer_id>` on first run. The resulting `https://<uuid>.cfargotunnel.com` URL is permanent — it stays the same across process restarts, machine reboots, and reconnects.

A free Cloudflare account is sufficient. No domain or paid plan required for the tunnel itself.

---

## Direct Port-Forward + DDNS

For the most reliable inbound without any third-party tunnel service:

```sh
urace network network setup-port-forward [--port 7301] [--ddns-token TOKEN] [--ddns-domain HOSTNAME]
```

Outputs router-specific instructions for configuring TCP port-forward external:7301 → local:7301. If your ISP assigns a dynamic IP, pass `--ddns-token` and `--ddns-domain` to configure a free [DuckDNS](https://www.duckdns.org) hostname — URACE will keep it updated automatically whenever your IP changes.

```sh
# Example: get instructions only
urace network network setup-port-forward --port 7301

# Example: with DuckDNS auto-update
urace network network setup-port-forward --ddns-token abc123 --ddns-domain mynode
# → registers mynode.duckdns.org, starts background IP watcher
```

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

- [Setup](exchange-setup.md) — enable networking first
- [Peer Security](../security/peer-security.md) — TLS, post-quantum, quarantine
- [Search Guide](search.md) — search P2P audit trail
- [urace-rpc-v1](../power-users/urace-rpc-v1.md) — full RPC contract reference

---
→ [Next: Peer Security](../security/peer-security.md) — TLS 1.3, post-quantum hybrid signatures, quarantine model
