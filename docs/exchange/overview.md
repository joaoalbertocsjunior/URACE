# Exchange Overview

[← Documentation](../index.md)

The URACE exchange is a P2P feature marketplace. Peers share software improvements, earn reputation units from adoption, and can borrow each other's features. Whether a borrow is cheaper than executor work requires task-matched costs and acceptance evidence.

---

## What It Is

The exchange connects software teams working on similar problems. Instead of every team solving the same challenges independently, the exchange lets teams:

- **Mint** features they've built (verified by quality gate) and earn tokens when others adopt them
- **Receive** open-use artifacts from pinned peers into quarantine
- **Inspect** seller-stated paid asks; cross-peer settlement is not yet available
- **Commission work** from peers via the escrow-backed work market

---

## Who It's For

- **Teams improving existing products**: earn tokens from quality improvements, reinvest them to borrow features
- **Developers with reusable components**: mint and monetize verified work without building a marketplace
- **Organizations with shared infrastructure**: use the network to distribute internal improvements across teams
- **AI agent workflows**: the exchange is designed to be operated by both humans and AI agents

---

## How It Works

1. You enable networking and pin peer identities.
2. A peer can expose an authenticated catalog of explicitly open-use assets and seller-local paid listing asks.
3. Freeform routing searches pinned catalogs before executor implementation and ranks plausible task matches.
4. An explicitly selected open-use asset can be fetched into quarantine; applying and executing it remain separate operator-controlled steps.
5. Paid remote asks are discovery-only. Cross-peer purchase settlement is not implemented.

The closed-network ledger records URACE reputation units. Those units do not have a verified exchange rate to provider tokens or fiat, so ledger activity alone cannot prove economic savings.

---

## Key Properties

- **Off by default**: The exchange is disabled until you explicitly enable it
- **Price estimate**: a creator supplied reference may constrain a listing; no network consensus or universal lower-cost guarantee is implemented
- **Cryptographically verified**: All bundles are signed with post-quantum hybrid signatures
- **Quarantine model**: Borrowed features are never executed automatically
- **Open-asset fetch**: `urace exchange network assets "<intent>"` searches pinned peers; `urace exchange network fetch-asset <peer-id> <asset-id>` receives an open-licensed artifact into quarantine (maximum 300 KB per one-RPC transfer)
- **Paid remote asks**: visible only as seller-stated URACE local units; no network purchase, shared settlement, or executor-cost comparison is available
- **Price evidence**: P2P and reputation records are not executor cost receipts; cost claims need matched task evidence

---

## Market Stats

See live token velocity and network health at any time:

```sh
urace exchange market stats --json
```

Returns:
- **mints_24h** / **burns_24h**: qualification receipts and credit deltas in the last 24 hours
- **net_velocity**: mints minus burns (positive = net token creation)
- **velocity.trend**: direction of velocity change (`up`, `down`, `stable`)
- **velocity.trend_delta_pct**: percentage change in velocity vs. the previous equivalent window
- **total_features**: feature count from the initial ledger header
- **network_peers**: estimated peer count
- **window_hours**: configurable via `--window-hours`

---

## Artifact Bundles

A bundle is the unit of transfer on the P2P exchange. It carries a verified implementation alongside its metadata.

### Any Type, Any Size

Artifact content is stored in a **content-addressed store** (`exchange_root/bundle-artifacts/<sha256[:2]>/<sha256>`), not embedded in the audit log. The bundle JSON only carries a `sha256` reference — the actual bytes are transferred separately on demand.

| Field | Description |
|-------|-------------|
| `artifact_ref` | SHA-256 of artifact bytes — content-addressed pointer |
| `artifact_size_bytes` | Size of the artifact (not limited to text) |
| `content_type` | MIME type (`text/x-python`, `application/octet-stream`, `application/zip`, etc.) |
| `artifact` | Inline text (backward compat; only for ≤64 KiB text artifacts) |
| `spec_context` | Language-agnostic behavior spec — what it does, not how |

This means bundles can carry **any artifact type**: Python files, compiled binaries, datasets, model weights, ZIP archives, patches, or any binary payload. The audit log stays lean regardless of artifact size.

### Delivery Routing

When a buyer fills a listing, delivery is routed:

1. **Owner first** — original creator is tried via peer probe cache (5-minute window)
2. **Replica fallback** — any registered replica holder if owner is offline
3. **Delivery fee** — 10% of ask price to the replica holder via `DELIVERY_FEE` audit row

```sh
# Become a delivery replica holder for a feature
urace exchange equity register-replica <feature_id> --artifact-hash <sha256>

# Fetch artifact bytes after filling a listing
urace exchange bundle fetch-artifact <bundle_id> --out ./artifact_file
```

Replica holders earn delivery fees for bandwidth. The original creator always earns `FEATURE_BORROWED` token credit regardless of who delivered.

### Replication Offers

The auto-sell pass emits `BUNDLE_REPLICATION_OFFER` for single-holder features (cooldown: 24h). Peers with `auto_replicate: true` (default) automatically accept, registering as replica holders — keeping features available even if the creator goes offline.

---

## Bootstrap Peers

Bootstrap peers are fixed entry points that help new peers join the network without prior discovery. Add known peers before enabling networking:

```sh
urace exchange bootstrap add --address <peer-addr>
urace exchange bootstrap list
urace exchange bootstrap remove --address <peer-addr>
```

Bootstrap addresses can be shared out-of-band (e.g., in your team's README or a private channel).

---

## Network Mode

URACE supports three network modes for different deployment scenarios:

| Mode | Description | Use case |
|------|-------------|----------|
| `intranet` | LAN-only — no internet peers contacted | Air-gapped or private team networks |
| `internet` | Standard — bootstrap peers + DHT discovery | Public internet deployment |
| `hybrid` | LAN + optional internet gateway (default) | Teams that want LAN efficiency with internet reach |

Configure the mode:

```sh
urace exchange settings set --network-mode intranet
urace exchange settings set --network-mode hybrid
```

### Intranet → Internet Upgrade

When your team is ready to connect to the wider network:

1. Discover your public address via STUN:
   ```sh
   urace exchange network public-address --json
   ```
2. Register it as a bootstrap peer endpoint so other internet peers can find you:
   ```sh
   urace exchange bootstrap add --address https://<your-public-ip>:<port>
   ```
3. Switch network mode to hybrid:
   ```sh
   urace exchange settings set --network-mode hybrid
   ```

---

## Get Started

- [Setup](setup.md) — enable, create identity, configure
- [Features](features.md) — mint, borrow, and trade
- [Work Market](work-market.md) — commission and deliver work
- [Network](network.md) — P2P discovery and consensus
- [Reputation](reputation.md) — tokens, ledger, leaderboard
