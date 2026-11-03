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
| `urace status` | Show product status |
| `urace status --json` | Status as JSON |
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
| `urace exchange equity auto-buy` | Run automated buying pass |
| `urace exchange equity auto-sell` | Run automated selling pass |
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
| `urace security audit` | Run a full security audit: checks key hygiene, permission boundaries, peer trust levels, compliance state |
| `urace security audit --json` | Audit output as JSON |

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

## Always-Mandatory URACE Concerns

These apply to every change in every session:

| # | Concern | Rule |
|---|---------|------|
| 1–12 | Core runtime | Derive, M2M, freeform, docs, spec, ledger, version, P2P economics, abuse prevention, tests, OS agnosticism, command surface |
| 13–20 | Governance | AGENTS.md, authority boundaries, zero-conf path, config schema, backward compat, security, quality gate invariants, self-evolution |
| 21 | KPIs | Every quality/economic decision enforces a measurable threshold |
| 22 | ROI signal | Users see estimated value before committing to major actions |
| 23 | Automation | Everything automatable is automated with the best default; `--auto` available |
| 24 | Power-user config | Every auto-behavior has a fine-grained override flag |
| 25 | Industry standards | Protocols and formats from established standards bodies |
| 26 | Battle-proven techniques | No experimental patterns in production code paths |

---

## Related

- [Config Reference](config.md) — all config options
- [Controls Guide](../guides/controls.md) — capability controls
- [Exchange Setup](../exchange/setup.md) — exchange configuration
- [AGENTS.md](../../AGENTS.md) — executor and agent onboarding
