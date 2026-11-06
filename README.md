# URACE

**Unified Runtime for Autonomous Collaborative Evolution.**

URACE is a lifecycle control plane that runs inside your software product. It manages goals, drives AI-assisted improvement cycles, enforces quality gates, and connects to a P2P network where verified features can be borrowed from peers — always cheaper than building from scratch.

```sh
pip install urace
urace init
urace daemon start
urace "Add goal: reduce p99 latency by 30%"
```

URACE runs autonomous improvement cycles, picks the best next action, executes it, and checkpoints the result. You come back to a better product.

---

## The loop

```
Goal → Discovery → Execution → Quality gate → Tokens → Borrow peer features → Better product
```

One earn path: verified quality improvement. One spend path: borrow verified peer features — always cheaper than building from scratch. That ceiling is enforced by the protocol, not a promise.

---

## Your product and your executor

**A product** is any software system you initialize URACE in — a web API, ML pipeline, data processor, content generator, or anything else. URACE does not care what language it runs in. Run `urace init` inside your project directory:

```sh
urace init                              # auto-detect product type from directory
urace init --type model                 # ML training or evaluation pipeline
urace init --type content               # content production pipeline
urace init --type data                  # data ingestion or transformation pipeline
urace init --type software --type media # mixed: code + media generation
```

Product types: `software` (default), `model`, `content`, `media`, `data`.

**An executor** is the agent that carries out operations each cycle. URACE auto-configures Claude or Codex from your API keys (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`). You can also wire any other tool:

```yaml
# config.json — executor.providers:
- id: my-agent
  adapter: script            # any CLI tool: stdin=prompt, stdout=JSON
  command: ./run_agent.sh

- id: my-api
  adapter: http              # any REST endpoint (retries on 429/503)
  endpoint: http://localhost:8080/improve

- id: my-mcp
  adapter: mcp               # MCP stdio JSONRPC 2024-11-05
  command: npx my-mcp-server
  tool: improve
```

`urace init --auto` wires the executor from environment variables in one step. The executor never modifies your source code without your approval.

→ [Full executor setup](docs/getting-started/quick-start.md#2-initialize-your-product) · [Concepts](docs/getting-started/concepts.md)

---

## In 5 minutes

```sh
urace init                                # wire up your product
urace daemon start                        # background cycles every 30 min
urace "What's blocking my latency goal?"  # plain text, any request
urace run                                 # trigger a cycle now
urace status                              # see what it found
```

---

## The P2P market — borrow before you build

Every verified feature on the network costs less than building it yourself:

```
ask_price ≤ (executor_reference_price − gas_overhead) × completeness × (1 − margin) − iter_savings
```

The reference price is derived automatically from median ledger fills. The minimum viable price floor (production + bandwidth + protocol fee) is enforced at listing. No config needed.

Your first borrow is free. After your first quality gate pass, you earn tokens automatically.

```sh
# Join the network
urace exchange settings set --enabled true --network true
urace exchange peer identity          # auto-generates your keypair

# Discover what's available
urace exchange compact search "rate limiter"
urace exchange compact search "image classifier"
urace exchange network discover

# Borrow — always cheaper than executor cost, guaranteed
urace exchange equity fill-listing <listing_id>

# Fetch artifact — any language, any format, any binary
urace exchange bundle fetch-artifact <bundle_id> --out ./artifact_file  # any language, format, binary

# Check your balance
urace exchange ledger summary
```

---

## Earn from your work

| Role | How you earn |
|------|-------------|
| Creator/Minter | `earn` — every time a peer borrows your feature |
| Delivery node (replica) | `delivery_fee` — proportional to delivery count |
| Composition owner | `composition_referral` — multi-level dynamic split |
| Challenger | `challenge_bounty` — successful APS challenge |
| Base/original owner | `provenance_compensation` — when derivative is listed |
| Ledger sealer | `seal_reward` — 1 unit per sealed block |
| LLM similarity peer | `llm_peer_reward` — 2 units per SIMILARITY_VERDICT |

Rewards are funded by a 2% protocol fee on every fill — not inflation.

```sh
# Mint a verified feature
urace exchange equity grant <feature_id> --creator <your_peer_id> \
  --description "Redis rate limiter with sliding window" \
  --spec-context "Limits reqs/key; evicts on TTL; thread-safe"

# List it — price ceiling auto-enforced
urace exchange equity list-for-sale <feature_id> --bp 5000 --price 80

# Become a delivery node — earn delivery fees per borrow
urace exchange equity register-replica <feature_id> --artifact-hash <sha256>

# Auto-trade — set thresholds once, runs itself
urace exchange equity auto-buy
urace exchange equity auto-sell
```

---

## Any artifact, any size

Bundles carry any file type at any size. Artifact bytes live in a content-addressed store — never in the audit log — with at-rest encryption. Replica holders store ciphertext only.

Artifact delivery uses per-session DEK wrapping (X25519 ECDH + AES-256-GCM). The raw key never leaves the device. Escrow auto-refunds after 48 hours if the seller fails to deliver.

```sh
urace exchange bundle fetch-artifact <bundle_id> --out ./model.bin
```

---

## Asset integrity — no stolen work ships

Every feature grant runs three layers before it reaches the market:

1. **Exact fingerprint** — SHA-256 collision detection
2. **Perceptual similarity** — dHash + Winnowing shingle overlap (threshold: 60%)
3. **LLM-peer check** — SIMILARITY_VERDICT from independent peers

Feature packs (bundles of multiple assets) are checked **per member** — not aggregated. A pack of stolen files each at 20% similarity is caught. A grant where > 95% of content traces back to known sources is hard-blocked.

Asset Provenance Staking (APS) adds a 30-day on-chain challenge window after mint. Successful challenge slashes the stake and compensates the original creator.

---

## Cartel and hijack prevention

A cluster of co-registered nodes cannot take availability-ransom over a feature:

- RS(4,6) erasure coding: needs any 4 of 6 chunks to reconstruct
- Cluster holding > ⅓ of chunk slots **or** ≥ 3 replica slots is flagged and penalized
- Pre-registration guard blocks the registration before it completes

MIME replication priority is auto-calibrated per node from audit history — each node preferentially replicates the content types its own features actually need.

---

## Security

TLS 1.3 + certificate pinning + post-quantum signatures (ML-KEM-768 + Ed25519) + quarantine model + at-rest artifact encryption + wash trading block + RPC flood protection + per-session DEK + escrow auto-refund + ALE/APS asset lineage enforcement + cartel chunk guard.

Incoming artifacts are never auto-executed. Self-evolution requires owner authorization.

→ [Full security overview](docs/security/overview.md)

---

## Works with AI agents

```sh
urace "What features on the network match my current goals?"
urace derive                           # generate implementation from active goals
urace freeform-text "explain the current bottleneck"
```

URACE is designed for both humans and AI agents. Full MCP and A2A support. Freeform queries use semantic synonym expansion — "visualization" matches "chart", "llm" matches "model".

---

## Docs

| | |
|---|---|
| [Quick start](docs/getting-started/quick-start.md) | [CLI reference](docs/reference/cli.md) |
| [P2P exchange](docs/exchange/overview.md) | [Token economy](docs/economics/tokenomics.md) |
| [Asset integrity](docs/concepts/asset-integrity.md) | [Node rewards](docs/concepts/node-rewards.md) |
| [Security model](docs/concepts/security-model.md) | [Price mechanics](docs/economics/price-mechanics.md) |
| [Security overview](docs/security/overview.md) | [Agent integrations](docs/agent-integrations.md) |
| [Full docs index](docs/index.md) | |

---

## Structure

```
urace/
├── runtime/urace/   — lifecycle control plane and CLI
├── runtime/tests/   — 2900+ behavioral regression tests
├── exchange/        — initial ledger (1370 free features)
├── trial/           — supervised improvement workflow
├── docs/            — full documentation
└── state/           — local deployment data (not tracked)
```

v0.4.0 · Code: [Apache 2.0](LICENSES/Apache-2.0.txt) · Spec (`URACE.md`): [CSL 1.0](LICENSES/CSL-1.0.txt) · Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
