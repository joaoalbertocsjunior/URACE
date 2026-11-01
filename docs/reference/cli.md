# CLI Reference

[← Documentation](../index.md)

All URACE commands in one place.

---

## Core Commands

| Command | Description |
|---------|-------------|
| `urace init` | Initialize a product in the current directory |
| `urace run` | Run one improvement cycle |
| `urace status` | Show product status |
| `urace status --json` | Status as JSON |
| `urace add "goal"` | Add an objective |

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
| `urace exchange peer identity` | Create or show peer identity |
| `urace exchange peer add --certificate FILE` | Pin a peer by certificate |
| `urace exchange peer list` | List all peers |
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

## System Health

| Command | Description |
|---------|-------------|
| `urace doctor` | Check config, state, executor, exchange, capability flags |
| `urace doctor --verbose` | Full diagnostic output |
| `urace doctor --json` | Diagnostics as JSON |

---

## Related

- [Config Reference](config.md) — all config options
- [Controls Guide](../guides/controls.md) — capability controls
- [Exchange Setup](../exchange/setup.md) — exchange configuration
- [AGENTS.md](../../AGENTS.md) — executor and agent onboarding
