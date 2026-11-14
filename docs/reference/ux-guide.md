# URACE — Get Running in 5 Minutes

## Install

```bash
pip install urace
```

---

## Start

```bash
urace start
```

URACE initialises, starts its improvement daemon, and joins the P2P network automatically.
No configuration needed.

---

## Tell it what you want

```bash
urace
```

This opens the shell — your main workspace. Type in plain language:

```
urace [daemon:running·internet·P2P:7301]> improve test coverage and reduce build time
→ Goal added: improve test coverage and reduce build time

urace [daemon:running·internet·P2P:7301]> never modify database migrations without a review
→ Rule added (prohibition): never modify database migrations without a review

urace [daemon:running·internet·P2P:7301]> we're building a SaaS payment platform on Python
→ Context added: we're building a SaaS payment platform on Python
```

URACE echoes back what it understood before acting. You always know what happened.

---

## That's it

URACE is now running, improving your product autonomously, and participating in the P2P
network. Check back any time:

```bash
urace status        # see what's happening
urace              # open shell and ask anything
```

---

## The 7 commands

Everything you need for daily use:

| Command | What it does |
|---------|-------------|
| `urace` | Open shell (your main workspace) |
| `urace start` | Boot daemon + join P2P network |
| `urace stop` | Shutdown |
| `urace status` | See everything: health, goals, decisions, activity |
| `urace config` | Change settings |
| `urace update` | Apply spec updates |
| `urace source` | Connect external sources (data, executors, metrics, github) |

---

## Connect external sources

`urace source add --kind <kind>` connects anything external:

```bash
urace source add mydb    --kind file     --connect ./data.json
urace source add metrics --kind csv      --connect ./metrics.csv --direction read
urace source add claude  --kind executor --command claude-code --adapter claude-cli
urace source add         --kind github   --repo owner/repo
urace source add coverage --kind metric  --metric-source mydb --metric-path $.coverage
urace source add pass-rate --kind vital  --numerator passed_tests --denominator total_tests
urace source list
urace source status
```

Kinds: `file` `csv` `json` `sqlite` `api` `connector` `executor` `metric` `vital` `github` `product` `peer`

---

## Inside the shell

Type naturally. URACE understands goals, rules, context, and questions:

```
> ship v2 by end of month with zero regressions
> always write tests for new functions
> why did you change the README?
> what blocked progress today?
> show me recent decisions
> run now
> what's my P2P peer count?
```

Slash shortcuts for quick actions:

| Shortcut | Does |
|----------|------|
| `/status` | Daemon status + node roles |
| `/events` | Recent activity stream |
| `/events --follow` | Live activity tail |
| `/peers` | Connected peers (anonymised) |
| `/config` | Get/set config key |
| `/stop` | Stop daemon |
| `/exit` | Exit shell |

---

## P2P Network

`urace start` handles everything automatically — NAT traversal, peer discovery, relay setup.

```bash
urace status        # peer count + network_mode: internet | intranet | hybrid
```

Inside the shell:

```
> /peers            # connected peers
> /status           # node status including roles (relay, bootstrap, consumer, creator)
```

To restrict your node to relay/bootstrap only:

```bash
urace exchange node roles --set bootstrap,relay
urace exchange setup-node   # checks NAT reachability, prints next steps
```

---

## Daily workflow

```bash
urace start                        # boot
urace                              # open shell
> [goals, rules, context]          # tell it what you want
> /events --follow                 # watch it work
> /status                          # check in
urace stop                         # done
```

First time only — no goals exist yet. The shell will prompt:

```
No goals set. What would you like to improve?
> ...
```

---

## Status subjects

`urace status` takes an optional subject for focused views:

```bash
urace status                # full runtime overview
urace status goals          # goal progress
urace status decisions      # recent decisions
urace status vitals         # credit, efficiency, health metrics
urace status blockers       # what's blocking progress
urace status compliance     # compliance posture
urace status plan           # current improvement plan
urace status watch          # live improvement activity
```

---

## Config

```bash
urace config show           # see all current settings
urace config evolution auto # let URACE self-improve when necessary (default)
urace config evolution never # lock self-improvement off
urace config budget set --daily 20 --monthly 200  # executor call limits
urace config controls show  # capability flags
```

Inside the shell:
```
> /config                   # show all config
> /config p2p.network_mode internet   # set a dotted key
```

---

## Going deeper

Everything above covers normal daily use. When you're ready for more:

---

### Power namespaces

Not needed for daily use. All accessible via `urace <namespace> --help`:

| Namespace | What it covers |
|-----------|---------------|
| `urace exchange` | P2P network internals, peers, equity market, distributed work |
| `urace product` | Multi-product management, fleet, isolated work sessions |
| `urace state` | State compaction, restore, amend, rollback |
| `urace source` | External data connectors and credentials |
| `urace crypto` | Local wallet, signing, key rotation |
| `urace api` | Machine interface: MCP stdio, A2A HTTP, scripting |

### Full reference

Complete documentation of all ~334 command paths, every flag, every schema:

→ [`ux-surfaces.md`](ux-surfaces.md) — full UX surface reference (all interfaces)

### Machine interface

For CI pipelines, scripts, and agent integrations that bypass the shell:

```bash
urace api call --command "status" --json
urace api serve --transport stdio     # MCP server for Claude, VS Code, etc.
urace api serve --transport a2a       # HTTP loopback for custom integrations
```

Full M2M reference: [`agent-integrations.md`](agent-integrations.md)

---

## Troubleshooting

```
urace start fails         → urace config show   (check state_path is writable)
No peers connecting       → urace status        (check network_mode is not "intranet")
Daemon not running        → urace start         (re-run; daemon exits on clean stop)
Not sure what happened    → urace status        (always the right first step)
```

For anything else — open the shell and ask:

```
> what's wrong?
> why isn't this working?
```

---

*Full reference: [ux-surfaces.md](ux-surfaces.md) · Power users: `urace <namespace> --help`*
