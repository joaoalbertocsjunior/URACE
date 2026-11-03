# AGENTS.md — URACE Executor and Agent Onboarding

**Runtime version: 0.2.0**

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
│   │   ├── initial_ledger.json    ← 1,356 built-in free-use P2P features
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

### Bootstrap Peers (first-peer discovery)

```sh
urace exchange bootstrap list --json             # list configured bootstrap endpoints
urace exchange bootstrap add <https://endpoint> --json   # add a bootstrap peer (https:// required)
urace exchange bootstrap remove <https://endpoint> --json
```

Bootstrap peers are contacted during exchange init when no DHT neighbors are known yet. Stored in `exchange/policy.json`.

### Network Stats (anonymized)

```sh
urace exchange network peers --json   # anonymized SHA-256 peer hashes
urace exchange network size --json    # heuristic DHT estimate
```

### Market Stats (token velocity + supply health)

```sh
urace exchange market stats --json                   # 24h window (default)
urace exchange market stats --window-hours 48 --json # 48h window
```

`urace exchange ...` is the top-level shorthand — `urace product exchange ...` also resolves but is the internal path.

Returns:
- `velocity`: mint/burn/equity/work events in window
- `velocity.trend`: direction of velocity change (`up`, `down`, `stable`)
- `velocity.trend_delta_pct`: % change in velocity vs. the previous equivalent window
- `supply`: total peers with balance, total ledger events, baseline grant
- `features`: total/revenue/free count, `revenue_fraction: 0.65`
- `network`: pinned peers, exchange enabled/network mode

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

### Feature Rating and Recommendation

Rate a feature after using it to improve recommendation quality across the network:

```sh
# Rate a feature by outcome
urace exchange feature rate --feature-id <id> --outcome positive --json
urace exchange feature rate --feature-id <id> --outcome negative --json
urace exchange feature rate --feature-id <id> --outcome neutral --json

# Rate with an explicit quality score (0.0–1.0)
urace exchange feature rate --feature-id <id> --outcome positive --score 0.85 --json
```

Get personalized recommendations based on your ratings and improvement history:

```sh
urace exchange feature recommend --json          # top recommendations (default limit)
urace exchange feature recommend --limit 5 --json
```

### Network Mode and Public Address

Three modes control how the exchange reaches other peers:

```sh
urace exchange settings set --network-mode intranet  # LAN-only, no internet
urace exchange settings set --network-mode internet  # DHT + bootstrap peers
urace exchange settings set --network-mode hybrid    # LAN + optional internet gateway (default)

# In hybrid mode, designate an internet-facing gateway peer
urace exchange settings set --internet-gateway <peer-id> --json
```

Resolve your public IP/port via STUN (needed when transitioning from intranet to internet):

```sh
urace exchange network public-address --json
urace exchange network public-address --stun-host stun.example.com --stun-port 3478 --json
```

### Peer Roles

Roles control what a peer may do on your node (admin > operator > readonly):

```sh
urace exchange peer role <peer_id> --json                    # show current role
urace exchange peer role <peer_id> --set admin --json        # grant admin
urace exchange peer role <peer_id> --set operator --json     # grant operator
urace exchange peer role <peer_id> --set readonly --json     # restrict to read-only
```

### Exchange Settings (governance parameters)

```sh
# Minimum peers required for consensus decisions
urace exchange settings set --consensus-min-threshold 3 --json

# Override baseline token grant per new peer (affects supply calibration)
urace exchange settings set --baseline-grant-tokens 500 --json
```

### Work Market

```sh
urace exchange work create --description "..." --budget-units 1000 --mode agora --json
urace exchange work create --description "..." --budget-units 1000 \
  --mode cohort --cohort-reputation-floor 50 --json
urace exchange work bid --request-id <id> --price-units 800 --json
urace exchange work accept --request-id <id> --bid-id <bid> --json
```

### GitHub-Attached Products

Register a GitHub repo as a product and run git operations through URACE:

```sh
# Register (clone is optional)
urace product register myapp --github owner/repo --clone-to /path/to/clone --json
urace product register myapp --github owner/repo --json   # register without cloning

# Git operations (safe allowlist: status pull fetch push commit log diff branch tag stash)
urace product git myapp status --json
urace product git myapp pull --json
urace product git myapp log --oneline -5 --json
urace product git myapp commit -m "msg" --json
```

Configure automatic git operations for improvement cycles:

```sh
urace configuration github-workflow --auto-pull true --json       # pull before cycles (default: true)
urace configuration github-workflow --auto-commit false --json    # don't auto-commit (default: false)
urace configuration github-workflow --auto-push false --json      # don't auto-push (default: false)
urace configuration github-workflow --branch-strategy current --json
urace configuration github-workflow --commit-message-template "feat: URACE cycle {cycle_id}" --json
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

### Compliance Mode

When compliance mode is enabled, stricter audit logging and governance rules apply — all state-modifying commands require an evidence record and peer role checks are enforced.

```sh
urace controls set --compliance-mode true --json   # enable
urace controls set --compliance-mode false --json  # disable
```

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

The initial ledger (`exchange/initial_ledger/initial_ledger.jsonl`) contains **1,356 built-in free-use features** covering every atomic runtime, trial, CLI, and P2P capability.

Format: JSONL — line 1 is a header (`{"schema":..., "feature_count":N}`), subsequent lines are one feature per JSON object. Enables streaming reads and line-addressable verification.

- All features: `borrow_price_units: 0`, `owner: null`, `initial_ledger: true`, `domain: "software"`, `artifact_discovery: {"kind": "runtime_bundle", "peer_exchange": true}`
- Automatically used by `urace derive` and `urace freeform-text` as routing context
- Searchable via `urace search --kind p2p`
- `revenue_feature_fraction: 0.65` — 35% of features are free/decayed (consume infra, no token flow)

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

## 15. Crypto Wallet (local keypair, gas-free)

All wallet operations are local CPU — no RPC calls, no gas fees, no on-chain broadcast.

```sh
# Generate a new secp256k1 keypair (stored at ~/.urace/wallet/key.json, chmod 600)
urace crypto wallet init --json

# Show address and public key (private key never exposed)
urace crypto wallet show --json

# Sign an arbitrary payload (returns DER signature + sha256 digest)
urace crypto wallet sign "payload string" --json

# Custom wallet directory
urace crypto wallet init --wallet-dir /secure/path --json
urace crypto wallet sign "data" --wallet-dir /secure/path --json

# Rotate key: generates a new keypair, re-signs pending records, backs up the old key
urace crypto wallet rotate --json
urace crypto wallet rotate --backup-dir /secure/backup --json
```

**EVM address compatibility**: Install `pysha3` for mainnet-compatible keccak256 addresses (`pip install pysha3`). Without it, addresses use FIPS SHA3-256 (structurally identical, not EVM-compatible).

**What is NOT implemented** (future broadcast layer):
- `eth_sendRawTransaction` / RPC broadcast
- Gas estimation
- Nonce management
- On-chain contract calls

---

## 16. Token Settlement


Tokens are reputation scores in a closed network by default. Mainnet settlement is disabled until explicitly enabled:

```sh
urace exchange settings set --token-settlement true   # explicit opt-in
urace exchange ledger transfer <peer_id> <amount_units> --yes
```

**CRYPTO_PENDING_FEATURES**: `token_settlement`, `cross_chain_transfer` — await blockchain connector integration.

---

## 17. Machine Interface Contract

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

## 18. Qualification Replay (audit verification — deterministic)

Replay stored evidence/decision pairs. Two modes:
- `--mode estimate` (default): heuristic score from proposal size
- `--mode full`: uses stored `evaluation_system` weights to detect **criteria drift** — whether scoring criteria changed since the original decision

```sh
urace qualification list --json
urace qualification list --kind executor-proposal --json
urace qualification replay --evidence-id <id> --json
urace qualification replay --evidence-id <id> --mode full --json
```

`--mode full` returns additional fields:
- `evaluation_weights_current` — current weights from config
- `evaluation_weights_at_qualification` — weights at the time of original decision (if stored)
- `criteria_drift` — `true` if weights changed; `null` if unknown; `false` if deterministically reproducible

Replay stored evidence/decision pairs to verify qualification integrity without re-running the full trial.

```sh
# List all evidence eligible for replay
urace qualification list --json
urace qualification list --kind executor-proposal --json

# Replay a specific evidence record
urace qualification replay --evidence-id <id> --json
```

Returns:
- `integrity`: `verified` | `no_stored_hash` | `mismatch`
- `stored_score_delta`: score from the original decision
- `replayed_score_estimate`: re-computed score from stored proposal
- `score_match`: bool — whether replayed estimate agrees with stored
- `decision_outcomes`: list of linked decision outcomes (APPROVED/DENIED)

Gas-free, CPU-local — reads only from `state/state.json`.

---

## 19. Fleet Capacity Dashboard

```sh
urace fleet capacity --json
```

Returns per-member executor pool health and fleet-wide parallel throughput:
- `parallel_capacity` — number of fleet members with at least one available provider
- `total_calls_remaining_24h` — total remaining call budget across all available providers
- `bottleneck_members` — members with no available provider (blocking parallel execution)
- `members[].available_providers` — count of available providers per member

### Fleet Config Push

Push a config key/value to all fleet members in a single command:

```sh
urace fleet config-push --config-key <key> --config-value <value> --json
```

Useful for propagating network mode changes, threshold adjustments, or compliance settings across a team fleet without per-member SSH. The command reports per-member success/failure.

---

## 20. Executor Circuit Breaker

Surfaces and controls the executor failure state tracked in `executor_pool_state`.

```sh
# Show per-provider failure counts, cooldowns, trip status
urace executor circuit-breaker --json

# Reset a tripped provider (clears failures + cooldowns)
urace executor circuit-breaker --cb-action reset --cb-provider <provider_id> --json
```

A provider is "tripped" when `failures >= trip_threshold` (default: 5). Tripped providers enter
a 30-minute open-circuit cooldown (`circuit_breaker_cooldown_seconds`). Configure thresholds:

```sh
# In urace configuration (executor section of config.json):
# "circuit_breaker_trip_threshold": 5      # consecutive failures before trip
# "circuit_breaker_cooldown_seconds": 1800 # open-circuit duration
```

---

## 21. Config Inspection

Show all resolved configuration values across all scopes (defaults, config.json, env overrides):

```sh
urace config show-all --json
```

Use this to verify the active configuration before running improvement cycles, especially after a `fleet config-push` or manual config edit. The output includes the source of each value (default / file / env).

---

## 21b. Security Audit

Run a full local security audit without connecting to any external service:

```sh
urace security audit --json
```

Checks:
- Wallet key permissions (`~/.urace/wallet/key.json` must be chmod 600)
- Peer certificate pinning hygiene
- Authority boundary integrity
- Compliance mode status
- Capability flag anomalies (e.g., minting enabled without identity)
- Audit trail completeness for state-modifying commands

Returns a `findings[]` array — each finding has `severity` (`info` / `warning` / `critical`) and a `remediation` hint. Exit code is non-zero if any `critical` finding exists.

---

## 21c. Product Types

URACE improvement cycles work on any pipeline with measurable quality metrics, not only software:

```sh
urace init --type software   # default
urace init --type content    # content production pipeline
urace init --type media      # AI-generated media pipeline
urace init --type model      # ML training/evaluation pipeline
urace init --type data       # data ingestion/transformation pipeline

urace product register --type content MyContentPipeline
urace product register --type model   MyModelTrainer
urace product register --type data    MyDataPipeline
```

`--type` sets executor context hints and default metric suggestions. URACE's scope is always the **production pipeline** (scripts, parameters, evaluation harness), not the output artifacts themselves.

URACE is product-agnostic. Any product with a measurable pipeline qualifies:
- **Game**: `--type software --type media` — metrics: FPS, retention, bug count
- **Book**: `--type content` — metrics: readability score, chapter completion, editor feedback
- **Scientific pipeline**: `--type data --type model` — metrics: accuracy, completeness, freshness

The executor improves the pipeline that produces the product, never the output artifact directly.

---

## 21e. Zero-Config Init

```sh
urace init --auto --json    # detect API keys, scaffold state, configure exchange, verify health
urace init --ready          # full bootstrap (discovers installed CLI clients, confirms onboarding)
urace init                  # minimal state init only
```

`--auto` steps:
1. Creates state if not exists
2. Detects `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` → auto-configures executor providers
3. Ensures P2P exchange identity exists
4. Applies sensible defaults (`auto_goals: true`, `effort: medium`)
5. Runs doctor health check
6. Returns `next_command: "urace auto"` when ready

---

## 22. What Executors Must Not Do

- Write directly to `state/state.json` (always use `urace` commands)
- Delete `exchange/initial_ledger/` (committed reference data)
- Modify `urace.md` spec without a corresponding runtime implementation (§62z invariant)
- Issue commands that require `REQUIRES_AUTHORITATIVE_DECISION` authority without pausing
- Attempt to create supply without a `score_delta > 0` qualification event

---

## 23. Usage Analytics

Agents can inspect aggregate runtime usage patterns without modifying state:

```sh
urace usage patterns --json          # top commands, token breakdown, goal success rates
urace usage patterns --limit 10      # limit to top 10 entries per category
```

Output keys:
- `top_commands` — list of `{kind, count}` sorted by frequency
- `token_breakdown` — `{freeform_tokens, executor_tokens}`
- `goal_outcomes` — list of `{goal, success_rate, total}` for operations

---

## 24. Goose and OpenSandbox Integration

URACE is compatible with [Goose](https://block.github.io/goose/) and OpenSandbox agent runtimes.

### Goose

Goose can drive URACE improvement cycles directly via shell tool calls:

```yaml
# goose session — example task
- tool: shell
  command: urace status --json
- tool: shell
  command: urace auto --json
- tool: shell
  command: urace usage patterns --json
```

Goose should treat `urace api commands --json` as its schema source and respect `REQUIRES_AUTHORITATIVE_DECISION` responses by pausing and surfacing to the operator.

### OpenSandbox

OpenSandbox agents can call URACE via its MCP server:

```sh
urace exchange network serve --host 127.0.0.1 --port 8443
```

The MCP endpoint exposes the same JSON-schema-validated API. OpenSandbox agents must set `--json` on all calls and parse the `status` field before proceeding. Authority boundary rules (§2) apply equally to OpenSandbox-originated commands.

---

## 25. Intranet → Internet Migration

When a user is ready to expose intranet features to the public P2P network, agents can trigger analysis and migration. Use `--auto` for zero-friction or guide interactively:

```sh
# Zero-conf: analyze + apply smart defaults (min-kpi-score 0.5, min-ratings 2, mode hybrid)
urace exchange network port-to-internet --auto --json

# Dry-run: analysis only, no changes made
urace exchange network port-to-internet --dry-run --json

# Power-user: explicit feature selection and raised quality threshold
urace exchange network port-to-internet --features feat-abc,feat-def --min-kpi-score 0.7 --json
```

Response fields: `public_address`, `features_to_port` (with `kpi_score`, `positive`, `negative`), `features_skipped`, `recommended_mode`, `steps`, `status`.

---

## 26. Related References

- `docs/index.md` — documentation index
- `docs/getting-started/quick-start.md` — five-minute walkthrough
- `docs/security/authority-boundary.md` — authority model details
- `docs/exchange/overview.md` — P2P exchange overview
- `docs/economics/tokenomics.md` — token supply and economics
- `CLAUDE.md` — Claude Code operator instructions (not for executors)
