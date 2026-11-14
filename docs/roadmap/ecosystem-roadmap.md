# URACE Ecosystem Roadmap

**Last updated:** 2026-11-10  
**Status:** Living document — updated as contracts are added or revised

---

## Why This Document Exists

URACE is a runtime for LLM agent orchestration. As the runtime grew, a recurring decision had to be made: *should URACE build the client, or should URACE publish the contract and let the ecosystem build the client?*

This document explains every time we chose the second path, **why** we chose it, and what it enables for builders who want to extend URACE without forking it.

---

## The Principle: Contracts, Not UIs

Every UI-like feature (VS Code extension, web dashboard, mobile app, real-time collaboration) has a hidden maintenance cost: **coupling**. A VS Code extension that surfaces `urace status` must be updated every time a new field appears in `status`. A web dashboard that polls a live server must be updated every time the state schema changes. A mobile app must be deployed through App Store review.

These are not features — they are **parallel products** that mirror the runtime. If the runtime moves fast (and it does — `cli.py` is 10k+ lines), they fall behind and become liabilities.

The right answer is to expose a **stable contract** and let clients build against it. URACE maintains the contract. The ecosystem maintains the clients.

**Result:** core runtime stays <15K LOC with no TypeScript CI, no App Store deployments, no container registries owned by the core team.

---

## What URACE Has Built (The Contract Layer)

### `urace-rpc-v1` — Daemon Socket API

**File:** `docs/reference/urace-rpc-v1.md`  
**Implementation:** `urace/_daemon.py`  
**Transport:** TCP `127.0.0.1:7474` (all platforms) + Unix socket on POSIX  
**Protocol:** Newline-delimited JSON (NDJSON)

**Why built:** Replaces the idea of a native VS Code extension. Any editor, shell widget, or monitoring tool can connect to the running daemon via a stable TCP socket without depending on URACE internals. The contract is the socket protocol. URACE never touches editor-specific code.

**What it enables:**
- VS Code plugin: 150-LOC TypeScript client reading the socket
- Neovim/Emacs/JetBrains: language-specific thin clients
- Shell status bar widgets (tmux, starship, etc.)
- Mobile monitoring via SSH tunnel (TCP is reachable over any tunnel)
- CI/CD scripts polling daemon state

**Maintenance cost to URACE:** O(1) — the socket API version (`urace-rpc-v1`) is stable. Adding a new CLI command does not break the socket API unless we explicitly add a new method. Clients that don't use the new method continue working.

---

### `urace-exchange-v2` — Peer Artifact Exchange

**File:** `urace/peer_exchange.py`  
**Schema:** `urace-exchange-v2`

**Why built:** Provides a signed, quarantined artifact exchange protocol over HTTPS/TLS 1.3 with ML-KEM-768 application-layer encryption. Incoming artifacts are never executed — only inspected. This is the foundation for P2P feature delivery.

**What it enables:**
- Any peer node implementing the `exchange.info`, `exchange.offers`, `exchange.assets.catalog`, `exchange.assets.fetch`, `exchange.receive` endpoints can participate in the URACE artifact network
- Third-party exchange implementations (alternative transports, different storage backends) can comply with the schema

**Maintenance cost to URACE:** Schema-versioned — `v3` can coexist with `v2`. Breaking changes require a version bump, not a rewrite.

---

### `urace-work-market-v1` — Distributed Work Market

**File:** `urace/peer_work_market.py`  
**Schema:** `urace-work-market-v1`

**Why built:** Enables distributed feature delivery where peers bid on work requests, escrow locks budget on acceptance, and multi-sig arbitration resolves disputes. This is the economic substrate for ecosystem participation.

**What it enables:**
- Any peer can post a work request via the market schema
- Custom arbitration implementations can plug into the dispute resolution path
- Enterprise tooling can read the append-only audit log to generate compliance reports
- Third-party quality checkers can implement the `WORK_VERIFIED` row type

**Maintenance cost to URACE:** Append-only audit rows — new row kinds can be added without breaking readers of existing kinds.

---

### `urace-aps-v1` — Portable Session Format

**File:** `urace/cli.py` (`urace export --format aps`, `urace import aps`)  
**Schema:** `urace-aps-v1`

**Why built:** Allows session context (conversation turns, state) to be exported and imported across provider switches, machine migrations, or tool handoffs. Prevents vendor lock-in at the session level.

**What it enables:**
- Migrate from one LLM provider to another without losing session context
- Share sessions between team members
- Build session replay tools, auditing tools, session diff tools
- Archive sessions for compliance

**Maintenance cost to URACE:** `turns` array schema is additive — new fields can be added without breaking importers.

---

### `urace-protocol-bindings-v1` — Protocol Catalog

**File:** `urace/protocol_catalog.py`

**Why built:** Documents all the protocol patterns URACE supports (CLI, typed API, MCP stdio, A2A loopback, peer artifacts) and their authority models. This is the master reference for integration builders.

**What it enables:**
- MCP-compatible clients can integrate via the stdio JSON-RPC binding
- A2A-compatible agents can use the loopback subset
- Custom integrations know exactly what URACE supports vs. what it explicitly rejects

---

### Provider Adapter Layer

**File:** `urace/protocol_catalog.py` (adapter list), `urace/cost_model.py` (`PROVIDER_RATE_TABLE`)

**Why built:** URACE is provider-agnostic. The rate table and adapter stubs allow cost modeling and routing decisions across Anthropic, OpenAI, and Mistral without locking into a single provider SDK.

**What it enables:**
- Community adapters for new providers (Gemini, Cohere, local models via Ollama)
- Custom cost models per deployment
- Provider-aware routing policies

---

### Relay Reward Infrastructure

**Files:** `urace/freeform_routing.py` (`track_relay_hop`), `urace/peer_exchange.py` (`issue_relay_credit`, `RELAY_CREDIT_ISSUED`)

**Why built:** Incentivizes relay nodes to participate in routing. Without economic incentives, relay networks collapse into free-rider problems. This makes relay participation profitable.

**What it enables:**
- Third-party relay operators can track their credit earnings
- Relay network analytics tools
- Relay reputation systems built on top of the credit history

---

### Enterprise Audit Chain

**Files:** `urace/peer_exchange.py` (`emit_audit_record`, `verify_audit_chain`), `urace/cli.py` (`urace audit --verify`)

**Why built:** Regulated industries require immutable audit logs with chain-of-custody verification. The SHA-256-chained record format allows independent verification without a blockchain.

**What it enables:**
- Compliance reporting tools reading `audit.jsonl`
- Third-party audit verification without access to URACE internals
- Enterprise integrations that require signed operation logs

---

## What URACE Will NOT Build (Ecosystem Territory)

These items have been deliberately excluded from the core runtime. The reason in each case is the same: they are **separate products** with their own release cycles, security surfaces, and maintenance budgets.

| Item | Why not in core | What enables it |
|------|----------------|-----------------|
| VS Code extension | TypeScript CI, VS Code API versioning, per-command coupling | `urace-rpc-v1` socket |
| JetBrains / Neovim / Emacs plugins | Language-specific, IDE-specific APIs | `urace-rpc-v1` socket |
| Mobile app (iOS/Android) | App Store/Play Store, two OS targets, background process restrictions | TCP socket via SSH tunnel |
| Docker sandbox image | Separate container registry, security patch cycle, `urace-sandbox` scope | `urace export` + published format spec |
| Real-time collaborative editing | CRDT infrastructure, WebSocket server, new failure modes | P2P relay event exchange over existing transport |
| Web browser/visual tasks | Playwright + browser engine = separate runtime | `urace[browser]` extras hook spec (future) |
| Cloud-hosted URACE | Infrastructure ops, billing, multi-tenancy | `urace-rpc-v1` over TCP/TLS; deploy URACE yourself |

**The rule:** if maintaining it requires a separate language, a separate registry, a separate OS target, or a separate security review — it is not a URACE feature. It is an ecosystem product.

---

## Maintenance Cost Analysis

The decisions above were not made because those features have low ROI. VS Code integration has very high ROI. The decisions were made because of **long-run coupling risk**.

| Approach | Maintenance model | What breaks when CLI changes |
|----------|------------------|------------------------------|
| Native VS Code extension | O(commands) — each new command needs extension update | Extension silently falls behind |
| Socket API (`urace-rpc-v1`) | O(1) — socket schema is stable | Nothing — clients that don't use new methods still work |
| `urace serve` HTTP server | O(state fields) — each new field needs template update | Dashboard silently shows stale data |
| `urace report` static HTML | O(1) — template regenerated from current state | Report always reflects current state |

The socket API and static HTML approaches decouple the core runtime from client code entirely. This is why they were chosen.

---

## Internal Modules Under Review

These modules are in core today but have ecosystem-candidate characteristics. No action is taken until coverage analysis confirms usage, but their coupling risk is documented here.

### `tui.py` — freeze investment

**Status:** Keep existing, do not expand.

The TUI is invoked when `urace` runs with no arguments. It is a UI layer that couples to state fields — every new state field is a potential TUI update. It has the same coupling risk as the web dashboard decision.

**Decision:** The existing TUI remains working. No new TUI features will be added to the core runtime. Future investment in terminal UIs should be ecosystem clients built against `urace-rpc-v1`. A terminal dashboard client reading the socket is a 300-LOC community project with zero coupling to URACE internals.

### `analytics.py` — keep in core

**Status:** Legitimate core module — keep.

`analytics.py` is called directly by `cli.py` for `urace export --analytics` and `urace export --format xlsx`. It generates portable CSV/HTML reports from durable state. It is not a UI client — it is a data export utility that is part of the protocol. It has no coupling risk because it reads from state (which is the contract) not from CLI command structure.

**Why not ecosystem:** A data exporter that reads from state has O(state-schema) coupling, not O(commands) coupling. State schema changes are versioned and controlled. This is acceptable core coupling.

---

## Guidance for Ecosystem Builders

### Building against `urace-rpc-v1`

1. Start the daemon: `urace daemon start`
2. Connect to `127.0.0.1:7474` (TCP)
3. Send NDJSON: `{"method": "ping"}\n`
4. Read NDJSON response: `{"schema": "urace-rpc-v1", "pong": true}\n`
5. See `docs/reference/urace-rpc-v1.md` for full method list

Your client will work on Linux, macOS, and Windows without modification. Mobile: SSH tunnel to the host running the daemon, connect to the forwarded port.

### Building against `urace-work-market-v1`

The work market is an append-only log. All row kinds are documented in `urace/peer_work_market.py`. To participate:
- Read the audit log to understand current state
- Emit rows using the documented kind constants
- Never modify or delete rows — the chain is append-only

### Building against `urace-exchange-v2`

Implement the five endpoints: `exchange.info`, `exchange.offers`, `exchange.assets.catalog`, `exchange.assets.fetch`, `exchange.receive`. See `urace/peer_exchange.py` for the full schema.

---

## Contributing Contracts

If you build something on top of URACE and want to propose a new contract (a new RPC method, a new row kind, a new export format), the process is:

1. Implement it in the runtime (§62z: spec follows implementation, not the other way)
2. Add a test for it
3. Document it in `docs/reference/`
4. Submit a PR

Contracts that exist only as documentation with no runtime implementation will not be merged.
