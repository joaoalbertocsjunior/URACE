# AGENTS.md — URACE Executor and Agent Onboarding

This document is the authoritative onboarding reference for any automated agent, AI executor, or programmatic client operating on a URACE runtime. Read this before issuing any `urace` command.

---

## 1. What URACE Is

URACE is a runtime for **governed autonomous improvement**. It accepts objectives, runs executors (LLMs or other automation) to produce changes, and gates those changes through a qualification protocol before accepting them. Every accepted change earns a reputation token on a P2P ledger.

**Executor role**: You are a contractor. You receive a well-scoped objective, produce a deliverable (code diff, document, analysis), and submit it for qualification. URACE measures whether the deliverable improved the product score. Acceptance = score_delta > 0.

---

## 2. Authority Boundary (read before acting)

URACE enforces an authority boundary derived from the operator-configured `authority` block. **Executors must not attempt to:**

- Bypass authority checks (`override authority`, `bypass authority`, `ignore authority`)
- Modify `self_evolution_policy` without explicit operator authorization
- Remove or replace the authority block
- Issue destructive commands without a matching delegated authority category
- Escalate scope beyond what was delegated for the current objective

**Reserved phrases that trigger rejection** (do not use these in commands):
`override authority`, `bypass authority`, `ignore authority`, `disable authority`, `remove authority`, `skip authority check`

**Authority check outcome values**:
- `AUTONOMOUSLY_AUTHORIZED` — proceed
- `DENIED` — stop; do not retry with modified phrasing
- `REQUIRES_AUTHORITATIVE_DECISION` — pause and surface to operator
- `UNRESOLVED` — treat as DENIED

---

## 3. Machine-Readable Discovery

Before issuing commands, query the machine API:

```sh
urace api commands --json          # full command/param schema
urace status --json                # current runtime state
urace status vitals --json         # resource and quality vitals
urace commands --json              # installed commands by concern
```

All commands accept `--json` for structured output. XML is available via `--format xml`.

---

## 4. File and Directory Structure

```
URACE/urace/
├── AGENTS.md                      ← this file
├── CLAUDE.md                      ← Claude Code operator instructions
├── docs/                          ← documentation (see docs/index.md)
├── runtime/
│   ├── build_initial_ledger.py    ← regenerate exchange/initial_ledger/ after module changes
│   ├── urace/                     ← runtime Python package
│   │   ├── cli.py                 ← top-level CLI entrypoint
│   │   ├── exchange_cli.py        ← exchange/P2P CLI verbs
│   │   ├── _common.py             ← state load/save, invariant enforcement
│   │   ├── authority.py           ← authority boundary resolution
│   │   ├── peer_exchange.py       ← P2P exchange (Exchange class, audit)
│   │   ├── freeform_routing.py    ← freeform intent routing
│   │   └── ...
│   └── tests/                     ← acceptance test suite
├── trial/                         ← qualification harness (separate process)
├── exchange/
│   ├── initial_ledger/
│   │   ├── initial_ledger.json    ← 1,343 built-in free-use P2P features
│   │   └── README.md
│   └── (live data — gitignored)
├── products/                      ← product snapshots (gitignored live data)
└── docs/
```

**State files** (never commit these; they are gitignored):
- `state/state.json` — runtime state (objectives, evidence, decisions, operations)
- `exchange/config.json` — P2P exchange settings
- `exchange/audit.json` — P2P audit chain

---

## 5. State Schema

The state document at `state/state.json` (path configurable via `state_path`) contains:

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | int | Schema version (≥ 1) |
| `state_version` | int | Incremented on every save |
| `authority` | dict | Delegated/reserved authority categories |
| `self_evolution_policy` | dict | `{mode: ENABLED\|SUPERVISED\|DISABLED}` |
| `objectives` | list | Active and closed objectives |
| `evidence` | list | Evidence records (executor proposals, search results, etc.) |
| `decisions` | list | Decision records (APPROVED/DENIED/DEFERRED) |
| `operations` | list | Operation records (planned, in-progress, completed) |
| `checkpoints` | list | Checkpoint records |
| `blockers` | list | Blocker records |
| `resource_calls` | list | Resource usage records |

**Invariants enforced on every save** (in `_common.py`):
- `schema_version >= 1`
- If `self_evolution_policy` is present: must be `{mode: <valid>}`
- If `authority` is present: must be non-empty

---

## 6. Core Workflow

### 6.1 Read Current State

```sh
urace status --json
urace status vitals --json
urace status goals --json
urace status resources --json
```

### 6.2 Work on an Objective

```sh
# List active objectives
urace status goals --json

# Start work on a specific objective
urace auto --cycles 1 --json

# Or manually: add a goal, run executor, check result
urace goal add --title "Improve X" --success-measure "Y" --json
urace executor run --objective-id <id> --json
```

### 6.3 Submit Evidence

```sh
urace evidence add --kind executor-proposal --description "..." --json
urace evidence add --kind search-result --source "..." --json
```

### 6.4 Record Decisions

```sh
urace decision record --id <id> --outcome APPROVED --json
urace decision assess <id> --forecast '{"expected_value": 0.8}' --json
```

### 6.5 Plan and Execute Operations

```sh
urace plan --json                   # generate plan for active objectives
urace operations add --title "..." --json
urace operations complete --id <id> --json
```

---

## 7. Exchange / P2P Commands

All exchange commands are under `urace exchange` or the `exchange` prefix.

### Feature Browsing (no cost)

```sh
urace search --kind p2p --json                    # search P2P ledger
urace exchange compact search <query> --json      # search with compressed archives
```

### Publishing Features (earns tokens)

```sh
urace exchange equity grant --feature-id <id> --description "..." \
  --borrow-price-units 100 --json
```

### Borrowing Features (spends tokens)

```sh
urace exchange equity fill-listing --feature-id <id> --json
```

### Balance and History

```sh
urace exchange ledger balance --json
urace exchange ledger history --json
```

### Network Stats (anonymized)

```sh
urace exchange network peers --json   # anonymized SHA-256 peer hashes
urace exchange network size --json    # heuristic DHT estimate
```

### Supply Calibration

```sh
# Baseline (1 Mbps consumer) — expect verdict=OK
urace exchange ledger supply-calc --peers 1000 --ledger-mb 50

# Large network (10 Mbps enterprise) — expect UNDERSUPPLIED → raise BASE_CAP_UNITS
urace exchange ledger supply-calc --peers 10000 --bandwidth-kbps 10000 --ledger-mb 500 --sync-secs 60
```

**Constants (credit_ledger.py):**
- `BASE_CAP_UNITS = 50 * UNIT` — governance per-peer balance cap; epoch-adjustable
- `PHYSICS_CAP_UNITS_PER_PEER = 41 * UNIT` — supply pressure ceiling at baseline 1 Mbps infra
- `CHAIN_SCALE = 10^10` — multiply internal base units by this for EVM 18-decimal on-chain representation

```python
from urace.credit_ledger import to_chain_units, from_chain_units, UNIT
on_chain = to_chain_units(UNIT)       # 1 token → 10^18 (EVM 18-decimal)
internal = from_chain_units(on_chain) # 10^18 → 10^8
```

### Work Market

```sh
urace exchange work create --description "..." --budget-units 1000 --mode agora --json
urace exchange work create --description "..." --budget-units 1000 \
  --mode cohort --cohort-reputation-floor 50 --json
urace exchange work bid --request-id <id> --price-units 800 --json
urace exchange work accept --request-id <id> --bid-id <bid> --json
```

---

## 8. Derive and Freeform Routing

### Derive (structured recommendation)

```sh
urace derive --json                           # suggest next improvements
urace derive --include-p2p-features --json   # include matching P2P features
```

### Freeform Text (intent classification)

```sh
urace freeform-text "deploy to staging" --json
urace freeform-text --file path/to/brief.txt --json
urace freeform-text --path ./docs/ --json
```

**Security limits:**
- Query capped at 4,096 bytes
- Null bytes rejected
- Known prompt injection patterns stripped before routing
- PII detected and warned before any minting

---

## 9. Controls and Governance

### Read Current Controls

```sh
urace controls show --json
```

### Set Controls

```sh
urace controls set --executor-enabled true --json
urace controls set --context-mint-enabled true --json

# Per-kind context minting (all default False)
urace controls set --context-mint-objectives true --json
urace controls set --context-mint-evidence true --json
urace controls set --context-mint-decisions true --json
urace controls set --context-mint-operations true --json
urace controls set --context-mint-checkpoints true --json
```

Every `controls set` writes a `config-capability-change` evidence record.

### Self-Evolution Policy

```sh
urace configuration self-evolution --mode SUPERVISED --json
```

Modes: `ENABLED` (autonomous), `SUPERVISED` (human-in-loop), `DISABLED`.

---

## 10. System Health

```sh
urace doctor --json
```

Checks: config integrity, state schema, executor availability, exchange identity, capability_flags, P2P health.

---

## 11. Auto Buy/Sell Presets

```sh
urace exchange trade-config show-presets --json       # list available presets
urace exchange trade-config set --preset conservative --json
urace exchange trade-config set --preset balanced --json
urace exchange trade-config set --preset aggressive --json
urace exchange trade-config set --auto-tune --json    # derive from network conditions
```

Presets: `conservative` (low risk, low ROI), `balanced` (default), `aggressive` (high volume, higher risk).

---

## 12. Compaction

```sh
urace compact --json                 # compress context to free space
urace decompact --json               # restore from compressed snapshot
urace exchange compact compress --json
urace exchange compact decompress --json
urace exchange compact search <query> --json  # searches live + archives
```

---

## 13. P2P Initial Ledger

The initial ledger (`exchange/initial_ledger/initial_ledger.json`) contains **1,343 built-in free-use features** covering every atomic runtime, trial, CLI, and P2P capability.

- All features: `borrow_price_units: 0`, `owner: null`, `initial_ledger: true`
- Automatically used by `urace derive` and `urace freeform-text` as routing context
- Searchable via `urace search --kind p2p`

Rebuild after adding modules:
```sh
cd runtime && python3 build_initial_ledger.py
```

---

## 14. Qualification Protocol

Executors do not control the qualification gate. The gate runs in the `trial/` harness:

1. Executor produces a deliverable (code diff, document, plan)
2. `trial/` runs tests, measures quality delta
3. `score_delta > 0` → accepted → tokens minted
4. Accepted changes are committed to the portfolio

**Do not attempt to bypass qualification** (the authority boundary blocks this).

---

## 15. Token Settlement

Tokens are reputation scores in a closed network by default. Mainnet settlement is disabled until explicitly enabled:

```sh
urace exchange settings set --token-settlement true   # explicit opt-in
urace exchange ledger transfer <peer_id> <amount_units> --yes
```

**CRYPTO_PENDING_FEATURES**: `token_settlement`, `cross_chain_transfer` — await blockchain connector integration.

---

## 16. Machine Interface Contract

All `--json` outputs follow these contracts:

| Field | Guarantee |
|-------|-----------|
| `status` | `"ok"`, `"error"`, or command-specific status string |
| `error` | Present and non-null on failure |
| `schema_version` | Present on state-modifying outputs |
| Timestamps | ISO 8601 UTC |
| Identifiers | Stable, lowercase-kebab or SHA-256 hex |

**Error handling**: A non-zero exit code always accompanies a non-`"ok"` status. Parse `error` field for machine-readable failure reason.

---

## 17. What Executors Must Not Do

- Write directly to `state/state.json` (always use `urace` commands)
- Delete `exchange/initial_ledger/` (committed reference data)
- Modify `urace.md` spec without a corresponding runtime implementation (§62z invariant)
- Issue commands that require `REQUIRES_AUTHORITATIVE_DECISION` authority without pausing
- Attempt to create supply without a `score_delta > 0` qualification event

---

## 18. Related References

- `docs/index.md` — documentation index
- `docs/getting-started/quick-start.md` — five-minute walkthrough
- `docs/security/authority-boundary.md` — authority model details
- `docs/exchange/overview.md` — P2P exchange overview
- `docs/economics/tokenomics.md` — token supply and economics
- `CLAUDE.md` — Claude Code operator instructions (not for executors)
