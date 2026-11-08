# AGENTS.md — URACE Executor and Agent Onboarding

**Runtime version: 0.5.0**

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
│   │   ├── cli_parser.py          ← canonical argparse grammar
│   │   ├── data_cli.py            ← isolated data-source command handlers
│   │   ├── exchange_cli.py        ← exchange/P2P CLI verbs
│   │   ├── _common.py             ← state load/save, invariant enforcement
│   │   ├── authority.py           ← authority boundary resolution
│   │   ├── peer_exchange.py       ← P2P exchange (Exchange class, audit)
│   │   ├── freeform_routing.py    ← freeform intent routing
│   │   ├── p2p_matching.py        ← post-classification intent-to-asset ranking
│   │   ├── local_feature_sources.py ← verify initial-ledger source bindings
│   │   └── ...
│   └── tests/                     ← acceptance suite split by feature into test_*.py modules
├── trial/                         ← qualification harness (separate process)
│   ├── p2p_local_feature_assets.py ← package/verify source-grounded local feature assets
│   ├── p2p_cost_claim_review.py   ← verify two pinned reviews for one live cohort claim
├── exchange/
│   ├── initial_ledger/
│   │   ├── initial_ledger.jsonl   ← 1,392 built-in free-use P2P features
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
urace exchange network assets [QUERY] --json  # discover authenticated pinned-peer assets; paid asks are discovery-only
urace exchange network fetch-asset <peer_id> <asset_id> --json  # fetch an explicitly selected open-use asset into quarantine
```

Remote open-use fetch requires a pinned authenticated peer, a public listing, an explicit zero-price open-use license, an allowed local receive rule, a verified seller signature and digest, and an artifact no larger than 300,000 bytes. The artifact is quarantined; fetch never applies or executes it. The seller verifies the buyer-signed quarantine receipt, records and signs an acknowledgement bound to the bundle, asset, artifact, receipt and seller audit event, and handles exact receipt replays idempotently while rejecting conflicting receipts. The buyer verifies and stores that attestation, so pair evidence does not require reading the remote seller's local files. This is cryptographic integrity and seller attestation under pinned-key assumptions, not global consensus or a guarantee against compromised keys/endpoints. Paid remote asks are informational only because cross-peer purchase settlement is not implemented. Do not claim that a P2P ask or reputation credit is cheaper than executor work without qualified paired evidence. A claim is cohort-specific and requires a source-custodian signature binding the source-corpus digest and exact frozen task manifest, plus a complete 30-pair LIVE study with six pairs per family, both arms accepted in every pair, P2P value no lower in every pair, complete comparable USD costs, zero URACE units paid, an allowed provider billing basis, and a paired 95% bootstrap upper bound below zero. It remains unqualified until two distinct reviewers pinned in the frozen plan sign the exact cohort and summary using `trial/p2p_cost_claim_review.py` and attest to full evidence review, workload-provenance review, and independence. These signatures provide accountable attestations, not automatic proof that signers are honest. Synthetic and unspecified evidence can never qualify a savings claim; no cohort proves a universal executor price ceiling.

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
- `escrow.active_escrows`: count of open/accepted work escrow requests
- `escrow.escrow_capable_peers_estimate`: unblocked pinned peers (upper bound; actual capability requires balance + rules)
- `escrow.pending_settlement_units`: tokens locked in accepted-but-not-released escrows

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

Freeform routing searches reachable pinned-peer catalogs before executor classification when P2P context is enabled. It only suggests assets by default. `urace freeform-text "<intent>" --p2p-asset <asset_id> --json` explicitly fetches a currently advertised open-use asset into quarantine and skips executor classification; it does not apply or execute the asset. `--ledger-context never` disables this route. Transfer, integration, validation, and any residual executor work remain costs even when the license usage price is zero.

**Security limits:**
- Query capped at 4,096 bytes
- Null bytes rejected
- Known prompt injection patterns stripped before routing
- PII detected and warned before any minting

---

## 9. Daemon and M2M Interface

### Foreground Daemon

Run improvement cycles continuously without a service manager:

```sh
urace daemon start --interval-minutes 30 --json    # foreground loop, Ctrl+C to stop
urace daemon start --max-cycles 5 --json           # stop after 5 cycles
urace daemon status --json                          # check PID file
urace daemon stop --json                            # send SIGTERM to running daemon
```

Returns on start: `{"status":"started","pid":N,"interval_minutes":30,"max_cycles":"infinity"}`
Returns on stop: `{"status":"stopped","pid":N}`

### Unified M2M Entry Point

Dispatch any command via structured JSON — useful for orchestration agents and CI:

```sh
urace m2m '{"command": "exchange settings set", "params": {"enabled": true}}'
echo '{"command": "status goals"}' | urace m2m --stdin
```

The `command` field is split on spaces and dispatched through the normal CLI. `--json` is appended automatically. All existing `--json` outputs are returned verbatim.

### Bandwidth and Compression Settings

```sh
urace exchange settings set --bandwidth-profile low --compress-wire true  # low-bandwidth peer
urace exchange settings set --bandwidth-profile high                       # high-bandwidth peer
urace exchange settings set --transfer-chunk-size 16384                   # explicit override
```

Profiles: `auto` (4 KB chunks), `low` (1 KB + optional gzip), `high` (64 KB chunks).

### GitHub Repository Integration

Connect URACE to a GitHub repository for issue sync, workflow dispatch, and security audit:

```sh
urace github connect owner/repo --json                        # save repo connection
urace github status --json                                    # check connection + repo info
urace github push-goals --json                               # push open objectives as issues
urace github push-goals --dry-run --json                     # preview, no issues created
urace github trigger-workflow ci.yml --ref main --json       # trigger workflow dispatch
urace github trigger-workflow deploy.yml --inputs '{"env":"prod"}' --json
```

Token: set `URACE_GITHUB_TOKEN` to a PAT with `repo` + `workflow` scopes. Token env var is configurable:
```sh
urace github connect owner/repo --token-env MY_GH_TOKEN --json
```

### Git and GitHub CLI Pass-through

```sh
urace git status --json                         # git status of product root, JSON output
urace git log --oneline -5                      # git log pass-through
urace git diff HEAD~1                           # diff pass-through
urace gh pr list                                # requires gh CLI installed
urace gh issue create --title "feat: X"        # create issue via gh
```

`urace git` and `urace gh` are scoped to the product root (`ROOT`). Both support `--json` to wrap stdout/stderr/returncode in JSON.

---

## 10. Controls and Governance

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

### Compliance Posture Inspection

```sh
urace compliance --json                           # all domains summary + recent records
urace compliance --domain authority --json        # single domain
urace compliance --history 20 --json              # last 20 records
urace compliance --export /tmp/audit.json         # export all records as JSON
urace compliance --export /tmp/audit.jsonl        # export as JSONL (one record per line)
urace compliance --since 2025-01-01 --json        # filter by date range
urace compliance --strict --json                  # exit 1 if any domain NON_COMPLIANT (CI gate)
```

`--strict` is designed for CI: exit code 1 = non-compliant, 0 = pass. JSON includes `strict_pass: bool`.

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

The initial ledger (`exchange/initial_ledger/initial_ledger.jsonl`) contains **1,392 built-in free-use features** covering every atomic runtime, trial, CLI, and P2P capability. Where tags map exactly to local runtime modules, entries also pin source paths, byte counts and SHA-256 hashes; these metadata identify local implementations but do not themselves make a source bundle downloadable or qualify its quality.

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

### P2P-first versus direct-executor paired comparison

The two arms for evaluating “cheaper than executor” are:

1. `direct_executor`: solve the frozen task from scratch with the pinned executor/model/effort profile.
2. `p2p_borrow` (P2P-first): discover a relevant asset, receive an eligible open-use artifact into quarantine, integrate and validate it, then use executor calls for remaining work as needed. Paid remote assets are not fetchable until cross-peer settlement is implemented.

Both arms use the same frozen task and independent acceptance/value rubric, with counterbalanced order. The plan embeds exact task and rubric text, verifies their hashes, and pins one provider/model/client/native-effort profile. The evaluator signs pass/fail and normalized value score [0,1] for each arm. Count all provider-native usage. A signed paired cost receipt must cover both arms under one declared provider billing basis, with non-provider costs measured under the frozen methodology. Report provider tokens, USD components, URACE reputation units, discovery/fetch/transfer, integration, validation, and residual executor work separately. Record failures; do not drop them. URACE units stay unconverted unless a dated, independently verifiable rate is pinned. Zero-price assets or lower provider-token use alone do not establish lower total cost. `trial/p2p_study_plan.py` freezes a counterbalanced 30-pair plan (six per family); `trial/p2p_pair_protocol.py` verifies collected evidence; `trial/p2p_study_runner.py` coordinates a configured live study. `trial/p2p_synthetic_cohort.py` exercises 30 synthetic tasks and real localhost mutual-TLS P2P catalog/fetch/quarantine/ack flow with no provider calls. Its results validate the pipeline only and cannot support economic claims.

Do not state that URACE/P2P is cheaper than executor work as an established result. It is a design objective to evaluate. Peer work-market escrow floors, reputation balances, P2P asks, and configured executor-call estimates are not a common cost unit. `network_hire` routing based on credit pressure is a resource-routing heuristic, not proof of savings. No live P2P-first paired cohort has qualified yet.

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

Run a full security audit (local checks + optional GitHub release integrity):

```sh
urace security audit --json              # full audit including GitHub release check
urace security audit --no-network --json # offline mode: skip GitHub release check
```

Checks:
- `wallet_present` — wallet key exists (`~/.urace/wallet/key.json`)
- `consensus_threshold` — min peers ≥ 3 for consensus decisions
- `compliance_mode` — compliance mode enabled/disabled
- `circuit_breaker` — all executor providers healthy
- `peer_certificate` — exchange identity certificate present
- `github_release_asset` — local VERSION matches a published GitHub release (network; skipped with `--no-network`)

Returns `{"status":"PASS"|"WARN","checks":[...],"pass_count":N,"warn_count":N}`. Each check: `{"check":"name","status":"OK"|"WARN"|"INFO","detail":"..."}`. Overall PASS only if no WARN checks.

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

## 26. CI and Team Pipeline Integration

URACE does not require a native CI adapter. The CLI and MCP stdio transport cover all synchronous CI use cases directly.

### CLI steps (GitHub Actions, Jenkins, CircleCI, etc.)

```yaml
# GitHub Actions example
- name: Check URACE health
  run: python3 -m urace check --json

- name: Classify and route operator input
  run: python3 -m urace classify "implement feature X" --json

- name: Run autonomous cycle (non-interactive)
  run: python3 -m urace auto --cycles 1 --json
```

No server process, no webhook, no extra dependencies — just the installed runtime.

### MCP stdio (agent-driven pipelines)

For pipelines that drive URACE through an MCP client, start the stdio server with a **scoped policy file** that restricts which commands the CI token may call:

```json
// ci-policy.json
{
  "project_id": "my-product-ci",
  "executor_id": "ci-runner",
  "read_only": false,
  "commands": ["check", "vitals", "product switch", "classify"]
}
```

```sh
urace api serve --policy ci-policy.json
```

The `commands` list is an allowlist — anything not listed is blocked. `ADMIN` operations (`init`, `fleet`, `govern`, `rules`, `configuration`, etc.) are always excluded from bridge sessions regardless of the policy file; they require a direct CLI call with operator authority.

### What is not supported

- **Webhook push triggers** (GitHub webhook → autonomous cycle) — not implemented; would require a running internet-reachable daemon with HMAC replay protection.
- **Remote ADMIN over MCP/A2A** — by design; use a direct CLI call with appropriate authority instead.

---

## 27. Related References

- `docs/index.md` — documentation index
- `docs/getting-started/quick-start.md` — five-minute walkthrough
- `docs/security/authority-boundary.md` — authority model details
- `docs/exchange/overview.md` — P2P exchange overview
- `docs/economics/tokenomics.md` — token supply and economics
- `CLAUDE.md` — Claude Code operator instructions (not for executors)
