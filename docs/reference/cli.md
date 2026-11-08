# CLI Reference

[← Documentation](../index.md)

All URACE commands in one place.

---

## Core Commands

| Command | Description |
|---------|-------------|
| `urace init` | Initialize a product in the current directory |
| `urace init --auto` | Zero-conf init: detect API keys, configure executor, create P2P identity, run health check |
| `urace init --ready` | Discover installed CLI clients and complete onboarding |
| `urace init --type software\|content\|media\|model\|data` | Initialize with a specific product type (sets metric suggestions and executor context hints) |
| `urace run` | Run one improvement cycle |
| `urace auto` | Run autonomous improvement cycles continuously |
| `urace status` | Show product status |
| `urace status --json` | Status as JSON |
| `urace check` | Inspect runtime state; fail on integrity issues |
| `urace vitals` | Show progress, credit usage, efficiency, and lifecycle health |
| `urace add "goal" [--scope pipeline\|quality_gate\|exchange\|runtime\|output] [--relates-to ID,ID]` | Add an objective with optional scope and cross-references |

---

## Inspect

| Command | Description |
|---------|-------------|
| `urace inspect --goals` | List all objectives |
| `urace inspect --plans` | List all plans |
| `urace inspect --operations` | List recent operations |

---

## Derive

| Command | Description |
|---------|-------------|
| `urace derive` | Extract all architectural constructs |
| `urace derive --constructs AP0,AP1` | Extract specific constructs |
| `urace derive --save` | Save derived constructs to ledger |
| `urace derive --refresh` | Re-derive and update saved constructs |
| `urace derive "freeform text"` | Freeform derive input |

---

## Search

| Command | Description |
|---------|-------------|
| `urace search "query"` | Full-text search of context ledger |
| `urace search "q" --kind objectives\|operations\|evidence\|decisions` | Filter by kind |
| `urace search "q" --kind p2p` | Search P2P audit ledger (features, credits, peers) |
| `urace search "q" --scope pipeline\|quality_gate\|exchange\|runtime\|output` | Filter by pipeline scope |
| `urace search "q" --since ISO` | Filter by date (ISO 8601) |
| `urace search "q" --limit N` | Limit results |

---

## Compact

| Command | Description |
|---------|-------------|
| `urace compact show` | Show compacted ledger summary |
| `urace compact show --json` | Summary as JSON |
| `urace compact search "query"` | Search compacted ledger (includes archives) |
| `urace compact search "q" --kind K` | Filter by kind |
| `urace compact search "q" --peer P` | Filter by peer |
| `urace compact search "q" --feature F` | Filter by feature |
| `urace compact search "q" --limit N` | Limit results |
| `urace exchange compact compress` | Compress context ledger to archive |
| `urace exchange compact decompress` | Restore from compressed archive |
| `urace exchange compact search "q"` | Search live + compressed archives |
| `urace exchange compact checkpoint` | Write ledger checkpoint + seal a PoQ block (tamper-evidence + O(tail) balance lookup) |
| `urace exchange compact balance-fast <peer_id>` | O(tail) credit balance using latest sealed block snapshot |
| `urace exchange bundle fetch-artifact <bundle_id>` | Show artifact sha256/size for a bundle |
| `urace exchange bundle fetch-artifact <bundle_id> --out <path>` | Write artifact bytes to file (any type/size) |

---

## Content

| Command | Description |
|---------|-------------|
| `urace content ref --path FILE` | Register a binary asset by SHA-256 hash (video, model weights, data files) |
| `urace content list` | List all registered content references |
| `urace content show <id>` | Show a content reference by ID or SHA-256 prefix |

---

## Controls

| Command | Description |
|---------|-------------|
| `urace controls show` | Show capability controls |
| `urace controls show --json` | Controls as JSON |
| `urace controls set --executor-enabled bool` | Enable/disable executor |
| `urace controls set --freeform-enabled bool` | Enable/disable freeform routing |
| `urace controls set --p2p-mint-enabled bool` | Enable/disable P2P minting |
| `urace controls set --p2p-sell-enabled bool` | Enable/disable P2P selling |
| `urace controls set --p2p-borrow-enabled bool` | Enable/disable P2P borrowing |
| `urace controls set --compress-enabled bool` | Enable/disable ledger compaction |
| `urace controls set --decompress-enabled bool` | Enable/disable ledger decompression |
| `urace controls set --machine-interface-enabled bool` | Enable/disable machine JSON interface |
| `urace controls set --context-mint-enabled bool` | Enable/disable context minting globally |
| `urace controls set --context-mint-objectives bool` | Allow minting objectives as context |
| `urace controls set --context-mint-evidence bool` | Allow minting evidence as context |
| `urace controls set --context-mint-decisions bool` | Allow minting decisions as context |
| `urace controls set --context-mint-operations bool` | Allow minting operations as context |
| `urace controls set --context-mint-checkpoints bool` | Allow minting checkpoints as context |
| `urace controls set --compliance-mode true\|false` | Enable/disable compliance mode (enforces stricter audit and governance rules) |

---

## Update

| Command | Description |
|---------|-------------|
| `urace update download` | Download latest runtime update |
| `urace update explain` | Explain staged update in plain language |
| `urace update explain --json` | Explain as JSON |
| `urace update apply` | Apply staged update |
| `urace update rollback` | Roll back to previous version |

---

## Exchange: Settings and Identity

| Command | Description |
|---------|-------------|
| `urace exchange settings show` | Show exchange settings |
| `urace exchange settings set --enabled bool` | Enable/disable exchange |
| `urace exchange settings set --network bool` | Enable/disable P2P networking |
| `urace exchange settings set --advertise bool` | Enable/disable LAN advertising |
| `urace exchange settings set --token-settlement bool` | Enable/disable token transfers |
| `urace exchange settings set --network-mode intranet\|internet\|hybrid` | Set network reach mode (see [Network Mode](../exchange/overview.md#network-mode)) |
| `urace exchange settings set --internet-gateway <peer-id>` | Set the internet-gateway peer for hybrid mode |
| `urace exchange settings set --consensus-min-threshold N` | Minimum peers required for consensus decisions |
| `urace exchange settings set --baseline-grant-tokens N` | Override baseline token grant per new peer |
| `urace exchange settings set --compress-wire bool` | Enable gzip compression on P2P wire transfers |
| `urace exchange settings set --bandwidth-profile auto\|low\|high` | Set bandwidth profile (auto=4 KB chunks, low=1 KB, high=64 KB) |
| `urace exchange settings set --transfer-chunk-size N` | Override transfer chunk size in bytes (512–131072; 0=use profile) |
| `urace exchange peer identity` | Create or show peer identity |
| `urace exchange peer add --certificate FILE` | Pin a peer by certificate |
| `urace exchange peer list` | List all peers |
| `urace exchange peer role <peer_id>` | Show the role assigned to a peer |
| `urace exchange peer role <peer_id> --set admin\|operator\|readonly` | Assign a role to a peer |
| `urace exchange peer block <id>` | Block a peer |
| `urace exchange peer unblock <id>` | Unblock a peer |
| `urace exchange peer rotate <old_id> --new-certificate FILE` | Rotate identity |

---

## Exchange: Network

| Command | Description |
|---------|-------------|
| `urace exchange network discover` | Discover peers |
| `urace exchange network probe <peer_id>` | Probe a peer's offerings |
| `urace exchange network refresh` | Refresh offers from pinned peers |
| `urace exchange network assets [QUERY]` | Search authenticated catalogs from pinned peers; paid asks are discovery-only |
| `urace exchange network fetch-asset <peer_id> <asset_id>` | Fetch an explicitly open-use asset into quarantine; never executes it |
| `urace exchange network serve` | Start P2P listener |
| `urace exchange network consensus-status` | View consensus state |
| `urace exchange network disconnect [--duration-minutes N]` | Pause networking |
| `urace exchange network peers [--limit N]` | List anonymized peer hashes (SHA-256 prefix) |
| `urace exchange network size` | Heuristic network size estimate (DHT gossip) |
| `urace exchange network public-address` | Resolve your public IP and port via STUN |
| `urace exchange network public-address --stun-host HOST --stun-port PORT` | Use a custom STUN server |
| `urace exchange network port-to-internet` | Analyze intranet features/reputation and guide migration to hybrid/internet mode |
| `urace exchange network port-to-internet --auto` | Auto-select high-quality features and switch to hybrid mode (smart defaults) |
| `urace exchange network port-to-internet --dry-run` | Analysis only — show what would be ported, no changes |
| `urace exchange network port-to-internet --features F1,F2` | Port specific features by ID |
| `urace exchange network port-to-internet --min-kpi-score 0.7` | Raise quality threshold for auto-selection |
| `urace exchange network-audit list [--kind K] [--peer P]` | View network audit events |

---

## Exchange: Equity and Features

| Command | Description |
|---------|-------------|
| `urace exchange equity grant <feature> --creator <peer_id>` | Grant equity to creator |
| `urace exchange equity list-for-sale <feature> --bp N --price N` | List equity for sale |
| `urace exchange equity listings [--feature F]` | Browse open listings |
| `urace exchange equity fill-listing <id>` | Buy a listing |
| `urace exchange equity holdings <feature>` | Show equity holdings |
| `urace exchange equity register-replica <feature>` | Register self as delivery replica holder (earns delivery fees) |
| `urace exchange equity auto-buy` | Run automated buying pass (bypasses adoption gate for new features) |
| `urace exchange equity auto-sell` | Run automated selling pass (emits replication offers for single-holder features) |
| `urace exchange equity trade-config set [--roi-preference F]` | Configure auto-trade thresholds |
| `urace exchange equity trade-config set --preset conservative\|balanced\|aggressive` | Apply preset config |
| `urace exchange equity trade-config set --auto-tune` | Derive config from network conditions |
| `urace exchange equity trade-config show-presets` | List available presets |
| `urace exchange compact depletion <feature_id>` | Check feature saturation |
| `urace exchange feature define <name> --wanted bool` | Define a wanted feature |
| `urace exchange feature borrow <feature_id> --peer <peer_id>` | Borrow a feature |
| `urace exchange feature rate --feature-id ID --outcome positive\|negative\|neutral` | Rate a borrowed or built feature by outcome |
| `urace exchange feature rate --feature-id ID --outcome positive --score F` | Rate with an explicit quality score (0.0–1.0) |
| `urace exchange feature recommend [--limit N]` | Get personalized feature recommendations based on your ratings and history |

---

## Exchange: Ledger and Reputation

| Command | Description |
|---------|-------------|
| `urace exchange ledger summary` | Show token balance |
| `urace exchange ledger transfer <peer_id> <amount>` | Transfer tokens |
| `urace exchange ledger supply-calc [--peers N] [--ledger-mb N]` | Calculate network supply |
| `urace exchange reputation show <peer_id>` | Show reputation breakdown |
| `urace exchange reputation leaderboard` | Top peers by reputation |
| `urace exchange reputation history <peer_id> --days N` | Reputation trend |

---

## Exchange: Work Market

| Command | Description |
|---------|-------------|
| `urace exchange work create "desc" --budget N --complexity F` | Create work request (agora mode) |
| `urace exchange work create "desc" --budget N --mode cohort --cohort-reputation-floor N` | Create cohort work request |
| `urace exchange work list [--state STATE]` | List requests and bids |
| `urace exchange work accept <request_id> --bidder <peer_id>` | Accept a bid |
| `urace exchange work verify <request_id> --approve bool` | Verify delivery |
| `urace exchange work decompose "desc" --budget N --complexity F` | Decompose complex work |
| `urace exchange work bid <request_id> --price N --eta-days N` | Submit a bid |

---

## Exchange: Rules

| Command | Description |
|---------|-------------|
| `urace exchange rule set <peer_id> <feature_id> send\|receive --allow bool` | Set access rule |
| `urace exchange rule export --file FILE` | Export all rules |
| `urace exchange rule import --file FILE` | Import rules from file |

---

## Products

| Command | Description |
|---------|-------------|
| `urace product list` | List registered products |
| `urace product register --github URL` | Register a GitHub repo as a product (clones locally) |
| `urace product register --github URL --clone-to DIR` | Clone to a specific directory |
| `urace product register --type software\|content\|media\|model\|data <name>` | Register a non-GitHub product with an explicit type |
| `urace product git status` | Git status of a registered product |
| `urace product git log` | Git log for a registered product |
| `urace product git diff` | Git diff for a registered product |
| `urace configuration github-workflow --repo owner/repo --output PATH` | Generate a GitHub Actions workflow for CI |

---

## Exchange: Bootstrap Peers

| Command | Description |
|---------|-------------|
| `urace exchange bootstrap add --address ADDR` | Add a bootstrap peer address |
| `urace exchange bootstrap list` | List configured bootstrap peers |
| `urace exchange bootstrap remove --address ADDR` | Remove a bootstrap peer |

---

## Exchange: Market Stats

| Command | Description |
|---------|-------------|
| `urace exchange market stats` | Live token velocity, mints/burns, supply, network health |
| `urace exchange market stats --window-hours N` | Set lookback window (default: 24h) |
| `urace exchange market stats --json` | Output as JSON (includes `velocity.trend` and `velocity.trend_delta_pct`) |
| `urace exchange market stats --json` (escrow fields) | Includes `escrow.active_escrows`, `escrow.pending_settlement_units`, `escrow.escrow_capable_peers_estimate` |

---

## Qualification

| Command | Description |
|---------|-------------|
| `urace qualification list` | List all qualification records |
| `urace qualification list --kind K` | Filter by kind |
| `urace qualification list --limit N` | Limit results |
| `urace qualification replay --evidence-id ID` | Replay qualification (heuristic estimate) |
| `urace qualification replay --evidence-id ID --mode full` | Full replay: uses stored evaluation weights, detects criteria drift |

---

## Crypto Wallet

| Command | Description |
|---------|-------------|
| `urace crypto wallet init` | Generate a new local secp256k1 keypair (gas-free, no RPC) |
| `urace crypto wallet init --overwrite` | Overwrite existing wallet |
| `urace crypto wallet show` | Show wallet address and public key |
| `urace crypto wallet sign "payload"` | Sign a payload with your private key |
| `urace crypto wallet rotate [--backup-dir DIR]` | Generate a new keypair, re-sign pending records, back up the old key |

The wallet is stored at `~/.urace/wallet/key.json` (chmod 600). Private key is never returned in command output.

---

## Fleet

| Command | Description |
|---------|-------------|
| `urace fleet status` | Show fleet status |
| `urace fleet list` | List fleet members |
| `urace fleet capacity` | Show per-member executor pool availability and aggregate capacity |
| `urace fleet config-push --config-key KEY --config-value VALUE` | Push a config key/value to all fleet members |
| `urace fleet config-push --config-key KEY --config-value VALUE --json` | Push with JSON output |

---

## Executor

| Command | Description |
|---------|-------------|
| `urace executor status` | Show executor health |
| `urace executor circuit-breaker` | Show circuit breaker status for all providers |
| `urace executor circuit-breaker --cb-action reset --cb-provider ID` | Reset circuit breaker for a provider |
| `adapter: script` | Arbitrary CLI tool — stdin prompt, JSON stdout |
| `adapter: http` | POST to REST endpoint, JSON response (supports Retry-After) |
| `adapter: mcp` | MCP stdio JSONRPC 2024-11-05 (initialize + tools/call) |
| `adapter: claude-cli` | Anthropic Claude CLI (auto-configured from `ANTHROPIC_API_KEY`) |
| `adapter: codex-cli` | OpenAI Codex CLI (auto-configured from `OPENAI_API_KEY`) |

Configure providers in `executor.providers` in your config. → [Executor setup](../getting-started/quick-start.md#2-initialize-your-product)

---

## Config

| Command | Description |
|---------|-------------|
| `urace config show-all` | Show all resolved configuration values across all scopes |
| `urace config show-all --json` | Output as JSON |

---

## Security

| Command | Description |
|---------|-------------|
| `urace security audit` | Run a full security audit: wallet, consensus threshold, compliance mode, circuit breaker, exchange certificate, GitHub release integrity |
| `urace security audit --json` | Audit output as JSON |
| `urace security audit --no-network` | Skip GitHub release check (offline mode) |

---

## Compliance

| Command | Description |
|---------|-------------|
| `urace compliance` | Show compliance posture per domain (authority, intent, schema, constraint, governance) |
| `urace compliance --domain DOMAIN` | Filter to a single domain |
| `urace compliance --history N` | Show last N records (default 10) |
| `urace compliance --export FILE` | Export all compliance records to FILE (.json or .jsonl) |
| `urace compliance --since ISO_DATE` | Filter records at or after date (ISO 8601) |
| `urace compliance --until ISO_DATE` | Filter records up to date |
| `urace compliance --strict` | Exit non-zero if any domain is NON_COMPLIANT (CI enforcement) |
| `urace compliance --json` | Output as JSON |

---

## Daemon

| Command | Description |
|---------|-------------|
| `urace daemon start` | Start foreground improvement daemon (loops `urace auto`; Ctrl+C to stop) |
| `urace daemon start --interval-minutes N` | Set cycle interval in minutes (default 30; minimum 1) |
| `urace daemon start --max-cycles N` | Stop after N cycles (0 = run forever) |
| `urace daemon status` | Check if a daemon is running for this product |
| `urace daemon stop` | Send stop signal to a running daemon |

---

## M2M Interface

| Command | Description |
|---------|-------------|
| `urace m2m '{"command":"exchange settings set","params":{"enabled":true}}'` | Dispatch any command via structured JSON body |
| `urace m2m --stdin` | Read JSON body from stdin |

All commands support `--json` for M2M-friendly output. The M2M interface passes through to the standard command surface with `--json` appended automatically.

---

## GitHub Integration

| Command | Description |
|---------|-------------|
| `urace github status` | Show GitHub connection status and repo info |
| `urace github connect owner/repo` | Connect URACE to a GitHub repository |
| `urace github connect owner/repo --token-env ENV` | Specify env var holding GitHub token (default: `URACE_GITHUB_TOKEN`) |
| `urace github push-goals` | Push current objectives as GitHub issues |
| `urace github push-goals --dry-run` | Preview without creating issues |
| `urace github trigger-workflow ci.yml` | Trigger a GitHub Actions workflow dispatch |
| `urace github trigger-workflow ci.yml --ref branch` | Trigger on a specific branch |
| `urace github trigger-workflow ci.yml --inputs '{"key":"val"}'` | Pass workflow inputs |

Set `URACE_GITHUB_TOKEN` to a GitHub personal access token with `repo` + `workflow` scopes.

---

## Git and GitHub CLI Pass-through

| Command | Description |
|---------|-------------|
| `urace git <args>` | Run any `git` command scoped to the current product root |
| `urace git status` | Git status of product root |
| `urace git log --oneline -10` | Git log for product |
| `urace gh <args>` | Run any `gh` CLI command (requires `gh` installed) |
| `urace gh pr list` | List open pull requests via GitHub CLI |
| `urace gh issue create --title "..."` | Create GitHub issue via `gh` |

---

## System Health

| Command | Description |
|---------|-------------|
| `urace doctor` | Check config, state, executor, exchange, capability flags |
| `urace doctor --verbose` | Full diagnostic output |
| `urace doctor --json` | Diagnostics as JSON |

---

## Usage Analytics

| Command | Description |
|---------|-------------|
| `urace usage patterns` | Show top commands by frequency, token breakdown, goal success rates, and freeform cache hit rate |
| `urace usage patterns --json` | Output as JSON (includes `freeform_stats.cache_hit_rate`) |
| `urace usage patterns --limit N` | Limit result rows (default 20) |

---

## Freeform Queries

| Command | Description |
|---------|-------------|
| `urace "any question or instruction"` | Classify freeform input and rank local and reachable P2P assets before executor implementation |
| `urace freeform-text "query"` | Explicit freeform dispatch with synonym expansion |
| `urace freeform-text "query" --p2p-asset <asset_id>` | Explicitly fetch a selected open-use network asset into quarantine and skip executor classification |

Freeform routing uses semantic synonym expansion — "visualization" matches "chart", "llm" matches "model". Enable or disable:

```sh
urace controls set --freeform-enabled true
```

---

## API Server (A2A / M2M)

| Command | Description |
|---------|-------------|
| `urace api serve --transport a2a --port 8765` | Start an A2A JSON-RPC endpoint on `127.0.0.1` |
| `urace api serve --transport a2a --policy /path/policy.json` | Scope the endpoint to a policy file |
| `urace api commands` | List all commands with parameter schemas (machine-readable) |

Requires `URACE_A2A_TOKEN` in the launch environment. Use an owner-managed TLS reverse proxy for remote access.

→ [Agent Integrations](../agent-integrations.md) for full A2A and MCP reference.

---

## Auto — Autonomous Loop

| Command | Description |
|---------|-------------|
| `urace auto` | Run autonomous improvement cycles until stopped |
| `urace auto --cycles N` | Stop after N cycles |
| `urace auto --cycles infinity` | Run indefinitely |
| `urace auto --interval SECS` | Pause N seconds between cycles |
| `urace auto --force-discovery` | Force a discovery pass before each cycle |
| `urace auto --dry-run` | Simulate cycles without committing changes |
| `urace auto --quiet` | Suppress per-cycle output |

`urace autonomous` is an alias for `urace auto`. For background scheduling use `urace daemon start`.

---

## Check and Vitals

| Command | Description |
|---------|-------------|
| `urace check` | Inspect runtime state; fail on integrity issues |
| `urace check --fail-on BLOCKING\|WARNING\|INFO` | Exit non-zero at a given severity |
| `urace check --migration-dry-run` | Simulate any pending schema migration |
| `urace check --query TEXT` | Filter output by query string |
| `urace vitals` | Show progress, credit usage, efficiency, and lifecycle health |
| `urace vitals --since DATE` | Filter vitals to a time range |
| `urace vitals --until DATE` | Upper bound of time range (ISO 8601) |
| `urace vitals --limit N` | Limit result rows |
| `urace vitals --fail-on BLOCKING\|WARNING\|INFO` | Exit non-zero at a given severity |

---

## Watch

| Command | Description |
|---------|-------------|
| `urace watch` | Observe runtime improvement cycles and deployment evidence |
| `urace watch events` | Stream lifecycle events |
| `urace watch dashboard` | Live improvement dashboard |
| `urace watch guard` | Monitor quality gate results |
| `urace watch report` | Streaming report mode |
| `urace watch --follow` | Tail new events continuously (alias: `-f`) |
| `urace watch --limit N` | Cap the number of events shown |

---

## Onboard

| Command | Description |
|---------|-------------|
| `urace onboard` | Show Product Onboard Phase status |
| `urace onboard status` | Detailed onboard phase inspection |

---

## Goal Management

| Command | Description |
|---------|-------------|
| `urace goal list` | List goals with optional status filter |
| `urace goal list --status active\|pending\|blocked\|resolved\|cancelled\|all` | Filter by lifecycle status |
| `urace goal inspect ID` | Full detail on a single goal |
| `urace goal forecast ID` | Show estimated completion based on current velocity |
| `urace goal prioritize ID --priority N` | Set numeric priority |
| `urace goal prioritize ID --floor N --ceiling N` | Set priority bounds |
| `urace goal schedule ID --deadline DATE` | Set a deadline |
| `urace goal schedule ID --not-before DATE` | Set earliest start date |
| `urace goal schedule ID --clear-deadline` | Remove deadline |
| `urace goal schedule ID --estimate-min-hours F --estimate-max-hours F --estimate-confidence low\|medium\|high` | Add effort estimate |
| `urace goal pin ID` | Pin goal (persist across resets) |
| `urace goal unpin ID` | Unpin goal |
| `urace goal defer ID --until DATE` | Defer goal until a date |
| `urace goal resume ID` | Resume a deferred goal |
| `urace goal resolve-update ID` | Mark a pending update resolution |
| `urace goal disable ID` | Disable a goal without deleting it |
| `urace goal cancel ID` | Cancel a goal |
| `urace goal delete ID` | Permanently delete a goal |

All `goal` subcommands accept `--json` for machine-readable output.

---

## Governance

| Command | Description |
|---------|-------------|
| `urace intent add "STATEMENT"` | Add a DIRECTIVE rule (durable operator intent) |
| `urace intent list` | List all intent rules |
| `urace intent list --scope product\|runtime\|all` | Filter by scope |
| `urace intent supersede ID` | Mark an intent rule as superseded |
| `urace intent deactivate ID` | Deactivate an intent rule |
| `urace intent rollback ID` | Revert to the previous version of an intent rule |
| `urace constraint add "STATEMENT"` | Add a PROHIBITION rule |
| `urace constraint add "STATEMENT" --allow` | Add a PERMISSION rule instead |
| `urace constraint list` | List all constraints |
| `urace constraint deactivate ID` | Deactivate a constraint |
| `urace policy list` | List autonomy policy settings |
| `urace policy set NAME VALUE` | Queue an autonomy policy change (self-evolution, external-metrics, analytics-export) |
| `urace budget show` | Show current executor call limits |
| `urace budget set --daily N` | Set daily executor call budget |
| `urace budget set --monthly N` | Set monthly executor call budget |
| `urace evaluation show` | Show evaluator weights and thresholds |
| `urace evaluation set-weight COMPONENT VALUE` | Adjust an evaluator weight |
| `urace evaluation set-minimum COMPONENT VALUE` | Set a minimum threshold |
| `urace govern clear GAP_ID` | Operator clearance for a blocked gate condition |
| `urace govern list-gates` | List active operator gate conditions |

---

## Evidence and Blockers

| Command | Description |
|---------|-------------|
| `urace add evidence --kind KIND --summary TEXT` | Queue an operator-provided evidence record |
| `urace add evidence --kind KIND --summary TEXT --source ID --detail TEXT` | Evidence with source reference and detail |
| `urace evidence list` | Query the evidence log |
| `urace evidence list --kind KIND` | Filter by evidence kind |
| `urace evidence list --since DATE --until DATE` | Filter by date range |
| `urace evidence list --limit N` | Limit results |
| `urace blocker list` | List active blockers |
| `urace blocker list --resolved` | Include resolved blockers |
| `urace blocker list --scope SCOPE` | Filter by scope |
| `urace blocker resolve ID --note TEXT` | Resolve a blocker with an optional note |

---

## Decisions, Reasoning, and Integrity

| Command | Description |
|---------|-------------|
| `urace decision list` | List decision records |
| `urace decision list --stale` | Show stale decisions |
| `urace decision list --scope SCOPE --limit N` | Filter by scope |
| `urace decision inspect ID` | Full detail on a single decision |
| `urace decision assess ID --forecast JSON` | Re-assess a decision with a new forecast |
| `urace why ID` | Traverse the reasoning chain behind a decision |
| `urace why ID --depth N` | Limit traversal depth |
| `urace explain ID` | Synthesize a human-readable explanation of a decision |
| `urace integrity-signal list` | List IntegritySignal records |
| `urace integrity-signal list --severity BLOCKING\|WARNING\|INFO` | Filter by severity |
| `urace integrity-signal list --type TYPE` | Filter by signal type |
| `urace integrity-signal list --resolved` | Include resolved signals |

---

## Tracing, Schema, and CRC

| Command | Description |
|---------|-------------|
| `urace trace list` | Query the lifecycle trace log |
| `urace trace list --kind CYCLE\|OPERATION\|DECISION\|TRANSITION\|GAP\|ONBOARD\|SWITCH\|FLEET` | Filter by trace kind |
| `urace trace list --since DATE --until DATE --limit N --offset N` | Date range and pagination |
| `urace trace list --cycle-id ID` | Filter to a specific cycle |
| `urace trace inspect ID` | Full detail on a trace record |
| `urace crc show` | Show the CognitiveResumeContext for the current product |
| `urace crc show --product ID` | Show CRC for a specific product |
| `urace crc show --product all` | Show CRCs for all products |
| `urace crc regenerate` | Regenerate the CRC from current state |
| `urace schema list` | List the output schema registry |
| `urace schema inspect NAME` | Inspect a registered output schema |
| `urace schema export --target output-schemas\|bundles\|all` | Export schemas |

---

## Feedback and Resource

| Command | Description |
|---------|-------------|
| `urace feedback list` | List outcome feedback records |
| `urace feedback list --limit N --offset N` | Paginate results |
| `urace feedback submit ID --signal POSITIVE\|NEGATIVE\|NEUTRAL` | Submit outcome feedback on a decision |
| `urace feedback submit ID --signal POSITIVE --detail TEXT --evidence ID` | Feedback with detail and evidence link |
| `urace feedback submit --input-json PATH` | Submit feedback from a JSON file |
| `urace resource status` | Show per-product resource usage and ROI |
| `urace resource report` | Detailed resource report with date filters |
| `urace resource report --since DATE --until DATE --limit N` | Filter report range |

---

## State Management

| Command | Description |
|---------|-------------|
| `urace amend EVENT_ID --notice TEXT` | Apply an in-place amendment to an archived record (§62f) |
| `urace amend EVENT_ID --notice TEXT --kind PROVENANCE_REVISED\|SUPERSEDED\|CUSTOM` | Specify amendment kind |
| `urace amend EVENT_ID --notice TEXT --target RECORD_ID` | Target a specific record within the event |
| `urace reset` | Reset URACE state to clean defaults |
| `urace reset --release-clean` | Flush all personal data and queues |
| `urace reset --yes` | Skip confirmation prompt |
| `urace rollback` | Restore product files from the last accepted stable snapshot |
| `urace rollback --dry-run` | Show what would be restored without applying |

---

## Report

| Command | Description |
|---------|-------------|
| `urace report status` | Export a portable analytics report |
| `urace report export --output PATH` | Write report to a file |
| `urace report export --output PATH --xlsx` | Export as XLSX spreadsheet |

---

## Features Registry

| Command | Description |
|---------|-------------|
| `urace features list` | List runtime feature status |
| `urace features summary` | Aggregated feature summary |
| `urace features candidates` | List candidate features for the next cycle |
| `urace features filter --status STATUS --tag TAG` | Filter by status or tag |
| `urace features show FEATURE_ID` | Full detail on a single feature |

---

## Classify

| Command | Description |
|---------|-------------|
| `urace classify TEXT` | Classify freeform text into matching command candidates |
| `urace classify TEXT --confirm` | Confirm and execute the top match |
| `urace classify TEXT --selection N` | Select the Nth candidate |
| `urace classify --file PATH` | Classify text read from a file |
| `urace classify TEXT --ledger-context auto\|always\|never` | Control ledger context injection |

Primarily used by freeform routing internally; useful for debugging command resolution.

---

## API — Full Interface

| Command | Description |
|---------|-------------|
| `urace api serve --transport a2a --port 8765` | Start A2A JSON-RPC endpoint on `127.0.0.1` |
| `urace api serve --transport a2a --policy FILE --port N` | Scope endpoint to policy file |
| `urace api serve --transport stdio` | MCP stdio JSONRPC 2024-11-05 transport |
| `urace api call --command CMD --params JSON` | Execute a single command via the API surface |
| `urace api batch --input-json PATH` | Execute a batch of commands from a JSON file |
| `urace api batch --input-json PATH --continue-on-error` | Continue batch on individual errors |
| `urace api commands` | List all commands with parameter schemas |
| `urace api watch --follow` | Stream lifecycle events via the API surface |
| `urace api watch --kinds LIST --since ISO8601` | Filter event stream |
| `urace api version` | Show API surface version |
| `urace api protocols` | List supported transport protocols |

Requires `URACE_A2A_TOKEN` for A2A transport. Use `--token-env VAR` to select a different env variable.

→ [Agent Integrations](../agent-integrations.md) for full A2A and MCP reference.

---

## Related

- [Config Reference](config.md) — all config options
- [Controls Guide](../guides/controls.md) — capability controls
- [Exchange Setup](../exchange/setup.md) — exchange configuration
- [AGENTS.md](../../AGENTS.md) — executor and agent onboarding
