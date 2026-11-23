# AGENTS.md — URACE Executor and Agent Onboarding

**Runtime version: 0.9.3** — Read this before issuing any `urace` command.

---

## 1. What URACE Is

URACE is a governed autonomous improvement runtime. It accepts objectives, delegates them to executors (LLMs or automation), gates results through a qualification protocol, and mints tokens on acceptance.

**Your role as executor**: receive a scoped objective → produce a deliverable (code diff, doc, analysis) → submit for qualification. Acceptance = `score_delta > 0`.

**Scope**: executor compute is local. The P2P layer distributes pre-built artifacts, not compute tasks. Remote compute is out of scope.

---

## 2. Authority Boundary — Read Before Acting

URACE enforces an authority boundary from the operator-configured `authority` block.

**Executors must not:**
- Bypass authority checks
- Modify `self_evolution_policy` without explicit operator authorization
- Remove or replace the authority block
- Issue destructive commands without a matching delegated authority category
- Escalate scope beyond what was delegated

**Reserved phrases — trigger hard rejection, never use:**
`override authority`, `bypass authority`, `ignore authority`, `disable authority`, `remove authority`, `skip authority check`

**Authority check outcomes:**
- `AUTONOMOUSLY_AUTHORIZED` — proceed
- `DENIED` — stop; do not retry with modified phrasing
- `REQUIRES_AUTHORITATIVE_DECISION` — pause and surface to operator
- `UNRESOLVED` — treat as DENIED

---

## 3. Machine-Readable Discovery

```sh
urace api commands --json          # full command/param schema
urace status --json                # current runtime state
urace status vitals --json         # resource and quality vitals
urace init --auto --json           # zero-config bootstrap (detects API keys, configures exchange)
```

All commands accept `--json`. XML: `--format xml`.

---

## 4. State Schema

State at `state/state.json` (never write directly — use `urace` commands):

| Field | Description |
|---|---|
| `authority` | Delegated/reserved authority categories |
| `self_evolution_policy` | `{mode: ENABLED\|SUPERVISED\|DISABLED}` |
| `objectives` | Active and closed objectives |
| `evidence` | Executor proposals, search results, etc. |
| `decisions` | APPROVED / DENIED / DEFERRED |
| `operations` | Planned, in-progress, completed |
| `checkpoints` | Accepted increments |

**Gitignored state files — never commit:** `state/state.json`, `exchange/config.json`, `exchange/audit.json`

---

## 5. Core Workflow

```sh
# Read state
urace status --json
urace status goals --json

# Add and run objective
urace goal add --title "Improve X" --success-measure "Y" --json
urace auto --cycles 1 --json

# Submit evidence
urace evidence add --kind executor-proposal --description "..." --json

# Record decision
urace decision record --id <id> --outcome APPROVED --json

# Plan and complete operations
urace plan --json
urace operations add --title "..." --json
urace operations complete --id <id> --json
```

---

## 6. Exchange / P2P

```sh
# Browse (free)
urace search --kind p2p --json
urace network compact search <query> --json

# Publish (earns tokens)
urace network equity grant --feature-id <id> --description "..." --borrow-price-units 100 --json

# Borrow (spends tokens)
urace network equity fill-listing --feature-id <id> --json

# Balance
urace network ledger balance --json
urace network ledger history --json

# Peers
urace network bootstrap list --json
urace network bootstrap add <https://endpoint> --json
urace network network peers --json
urace network network size --json

# Network mode
urace network settings set --network-mode hybrid --json    # hybrid (default), intranet, internet

# Work market
urace network work create --description "..." --budget-units 1000 --mode agora --json
urace network work bid --request-id <id> --price-units 800 --json
urace network work accept --request-id <id> --bid-id <bid> --json

# Market stats
urace network market stats --json

# Asset fetch (authenticated pinned peer, open-use, explicit zero-price only)
urace network network assets [QUERY] --json
urace network network fetch-asset <peer_id> <asset_id> --json   # quarantine only — never auto-applied
```

Remote open-use fetch requires a pinned authenticated peer, public listing, verified seller signature, and artifact ≤ 300 000 bytes. The artifact lands in quarantine — fetch never applies or executes it.

Do not claim P2P is cheaper than executor work without a qualified 30-pair LIVE cohort signed by two independent reviewers via `trial/p2p_cost_claim_review.py`.

---

## 7. Freeform and Derive Routing

```sh
urace derive --json                              # suggest next improvements
urace derive --include-p2p-features --json

urace freeform-text "deploy to staging" --json  # intent classification
urace freeform-text --file brief.txt --json
```

**Cancel detection (zero LLM cost):**
```sh
urace "cancel"       # → {"status": "cancelled", "cancelled": "goal title"}
urace "never mind"   # same; also: abort, forget, scratch that, undo
```

**Clarification loop** — when classifier confidence < 0.8, returns `clarifying_question` in JSON. Re-submit with original text + answer appended. Max 2 turns.

**Security limits:** query capped at 64 KiB; null bytes and blank inputs rejected; known prompt injection patterns stripped.

---

## 8. Daemon and M2M Interface

```sh
urace daemon start --interval-minutes 30 --json
urace daemon stop --json
urace daemon status --json

# Dispatch any command via structured JSON
urace m2m '{"command": "exchange settings set", "params": {"enabled": true}}'
echo '{"command": "status goals"}' | urace m2m --stdin
```

---

## 9. GitHub Integration

```sh
# Connect
urace github connect owner/repo --json
urace github status --json

# Push goals as issues
urace github push-goals --json
urace github push-goals --dry-run --json

# Trigger workflow
urace github trigger-workflow ci.yml --ref main --json
urace github trigger-workflow deploy.yml --inputs '{"env":"prod"}' --json

# Git / gh pass-through (scoped to product root)
urace git status --json
urace git log --oneline -5
urace gh pr list
```

Token: set `URACE_GITHUB_TOKEN` (PAT with `repo` + `workflow` scopes).

---

## 10. Controls and Governance

```sh
urace controls show --json
urace controls set --executor-enabled true --json
urace controls set --compliance-mode true --json
urace controls set --context-mint-enabled true --json
urace configuration self-evolution --mode SUPERVISED --json   # ENABLED | SUPERVISED | DISABLED

urace compliance --json
urace compliance --strict --json    # exit 1 if any domain NON_COMPLIANT (CI gate)
urace compliance --export /tmp/audit.json
```

---

## 11. System Health and Security

```sh
urace doctor --json
urace security audit --json
urace security audit --no-network --json   # offline
urace config show-all --json               # resolved config across all scopes
```

---

## 12. Crypto Wallet (local, gas-free)

```sh
urace crypto wallet init --json
urace crypto wallet show --json
urace crypto wallet sign "payload" --json
urace crypto wallet rotate --json
```

Private key never exposed in logs or return values. Stored at `~/.urace/wallet/key.json` (chmod 600).

---

## 13. Initial Ledger

1 405 built-in free-use features at `exchange/initial_ledger/initial_ledger.jsonl`.
All entries: `borrow_price_units: 0`, `initial_ledger: true`.
Used automatically by `urace derive` and `urace freeform-text`.

Rebuild after adding modules:
```sh
cd runtime && python3 build_initial_ledger.py
```

---

## 14. Qualification Protocol

Executors do not control the qualification gate:

1. Executor produces a deliverable
2. `trial/` harness runs tests, measures quality delta
3. `score_delta > 0` → accepted → tokens minted

```sh
urace qualification list --json
urace qualification replay --evidence-id <id> --json
urace qualification replay --evidence-id <id> --mode full --json   # detect criteria drift
```

Do not attempt to bypass qualification — the authority boundary blocks it.

---

## 15. Product Types

```sh
urace init --type software   # default
urace init --type content
urace init --type media
urace init --type model
urace init --type data
```

URACE improves the production pipeline, not the output artifact.

---

## 16. CI Pipeline Integration

```yaml
# GitHub Actions
- run: python3 -m urace check --json
- run: python3 -m urace auto --cycles 1 --json
```

For MCP stdio agent pipelines, restrict with a policy file:
```sh
urace api serve --policy ci-policy.json
```

`ADMIN` operations (`init`, `fleet`, `govern`, `rules`, `configuration`) are always excluded from bridge sessions — they require a direct CLI call with operator authority.

---

## 17. Machine Interface Contract

| Field | Guarantee |
|---|---|
| `status` | `"ok"`, `"error"`, or command-specific string |
| `error` | Present and non-null on failure |
| `schema_version` | Present on state-modifying outputs |
| Timestamps | ISO 8601 UTC |
| Identifiers | Stable, lowercase-kebab or SHA-256 hex |

Non-zero exit code always accompanies non-`"ok"` status.

---

## 18. What Executors Must Not Do

- Write directly to `state/state.json` — always use `urace` commands
- Delete `exchange/initial_ledger/`
- Document a feature not implemented in the same change (§62z invariant)
- Issue `REQUIRES_AUTHORITATIVE_DECISION` commands without pausing for operator
- Attempt to create supply without a `score_delta > 0` qualification event
- Claim P2P is cheaper than executor work without a qualified live cohort

---

## 19. References

- `docs/index.md` — documentation index
- `docs/users/quick-start.md` — five-minute walkthrough
- `docs/security/authority-boundary.md` — authority model
- `docs/power-users/exchange-overview.md` — P2P exchange
- `docs/economy/tokenomics.md` — token supply and economics
- `CLAUDE.md` — Claude Code maintenance guide (not for executors)
