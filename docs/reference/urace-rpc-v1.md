# urace-rpc-v1 — Daemon Socket Protocol

Primary transport: TCP `127.0.0.1:7474`  
POSIX systems: additionally Unix socket `~/.urace/rpc.sock` (future)

## Protocol

Newline-delimited JSON (NDJSON). Send one JSON object per line, receive one JSON object per line.

## Methods

### ping
Request: `{"method": "ping"}`  
Response: `{"schema": "urace-rpc-v1", "pong": true}`

### status
Request: `{"method": "status"}`  
Response: `{"schema": "urace-rpc-v1", "status": "running"|"stopped", "pid": <int>|null}`

### stop
Request: `{"method": "stop"}`  
Response: `{"schema": "urace-rpc-v1", "status": "stopping"}`

### `dispatch`

Run any `urace` CLI command over the daemon socket and receive its JSON output.

Request: `{"method": "dispatch", "argv": ["exchange", "network", "discover"]}`

Response: `{"schema": "urace-rpc-v1", "output": "<captured JSON string>"}`

All `urace` commands are available. Equivalent to `urace m2m` but over the local TCP socket without process spawn.

### `events`

Fetch recent P2P audit events.

Request: `{"method": "events", "limit": 20}`

Response: `{"schema": "urace-rpc-v1", "output": "<audit rows JSON>"}`

`limit` defaults to 20 if omitted.

## Notes

- Server only runs when `urace daemon start` is active
- All clients (IDE plugins, shell widgets, mobile SSH tunnels) build against this contract
- URACE maintains only the server and this spec — not the clients

---

# Bootstrap Peer HTTP RPC — `/urace/rpc/v1/`

These endpoints are served by bootstrap peers (not the local daemon). They are only called when `network_mode` is `internet` or `hybrid`. All responses are JSON.

## `GET /urace/rpc/v1/find-node`

Peer routing lookup via Kademlia DHT.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_peer_id` | string | The peer ID to look up |

**Response:**

```json
{
  "status": "found" | "not_found" | "rpc_error",
  "peer_id": "<id>",
  "endpoint": "<https-url>"
}
```

---

## `POST /urace/rpc/v1/shamir-deliver`

Deliver an encrypted DEK share to a replica holder during a feature listing flow.

**Request body (JSON):**

```json
{
  "feature_id": "<id>",
  "holder_peer_id": "<peer-id>",
  "share_index": 0
}
```

**Response:**

```json
{
  "status": "delivered" | "rpc_error",
  "feature_id": "<id>"
}
```

---

## `GET /urace/rpc/v1/ledger-tail`

Fetch the current ledger tail from a full peer. Used by light peers to synchronize their sliding-window view without downloading the full audit history.

**Response:**

```json
{
  "seal": { "kind": "LEDGER_BLOCK_SEAL", "sequence": 42, ... } | null,
  "tail": [ ... ]
}
```

`seal` is `null` when the peer has no sealed block yet. `tail` contains all audit rows since the latest seal (or all rows if no seal exists).
