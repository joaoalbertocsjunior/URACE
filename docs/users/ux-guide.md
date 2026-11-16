# URACE — Daily Use

[← Documentation](../index.md)

## Install

```bash
# one-liner (Linux / macOS / WSL):
curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh

# pip:
pip install urace

# npm:
npm install -g urace-cli

# Homebrew:
brew install urace

# conda:
conda install -c conda-forge urace
```

## Update

```bash
curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh
pip install --upgrade urace
npm install -g urace-cli@latest
brew upgrade urace
conda update -c conda-forge urace
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

## The 5 commands

Everything you need for daily use:

| Command | What it does |
|---------|-------------|
| `urace` | Open shell (your main workspace) |
| `urace start` | Boot daemon + join P2P network |
| `urace stop` | Shutdown |
| `urace status` | See everything: health, goals, decisions, activity |
| `urace reload` | Hot-reload config.json without restart |

---

## Inside the shell

Type naturally. URACE understands goals, rules, context, and questions.
The input layer is robust to common variations:

```
> ship v2 by end of month with zero regressions
> always write tests for new functions
> why did you change the README?
> what blocked progress today?
> show me recent decisions
> run now
> what's my P2P peer count?

# URACE understands common typos and shorthand automatically:
> Status           → opens status view
> RELOAD           → reloads config
> statis           → runs status (typo corrected)
> sto              → stop (shorthand)
> status/goals     → status goals
> statusnetwork    → status network
> show me my goals → status goals
> recent decisions → status decisions
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
urace network node roles --set bootstrap,relay
urace network setup-node   # checks NAT reachability, prints next steps
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

## Status output

`urace status` shows a structured overview:

```
urace 0.9.0 — ONBOARDING
lifecycle:  ONBOARDING      health: BLOCKED  blocking: 1  warnings: 4
network:    mode=hybrid  roles=consumer  peers=0  tunnel=down
executor:   enabled=False  providers=none  calls_24h=0
goals:      active=0  pending=0  blocked=0  auto=False
config:     effort=medium  self_evolution=NECESSARY_ONLY  capability_envelope=not set

BLOCKING  (1 total, 1 unique):
  [onboard-config-incomplete] Config missing required fields  ×1
    → add missing fields to config.json, then: urace reload

WARNINGS (4 total, 2 kinds):
  [citizen-base-violation] ×3  e.g. evidence record missing CitizenBase fields
  [onboard-capability-envelope-missing] ×1  e.g. Config.capability_envelope is absent
  → urace status --verbose  for full list
```

Subjects for focused views:

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

Use `--verbose` to see all gap details, `--json` for machine-readable output.

---

## Config

Edit `~/.urace/config.json`, then apply without restarting:

```bash
urace reload
```

Inside the shell:
```
> /config                   # show all config
> /config p2p.network_mode internet   # set a dotted key
```

For the full config namespace (advanced): `urace config --help`

---

## Going deeper

Everything above covers normal daily use. When you're ready for more:

---

### Power namespaces

Not needed for daily use. All accessible via `urace <namespace> --help`:

| Namespace | What it covers |
|-----------|---------------|
| `urace network` | P2P network internals, peers, equity market, distributed work |
| `urace product` | Multi-product management, fleet, isolated work sessions |
| `urace state` | State compaction, restore, amend, rollback |
| `urace source` | External data connectors and credentials |
| `urace crypto` | Local wallet, signing, key rotation |
| `urace api` | Machine interface: MCP stdio, A2A HTTP, scripting |

### Full reference

Complete documentation of all ~237 internal argparse paths + 73 SD NLP routes, every flag, every schema:

→ [`ux-surfaces.md`](../power-users/ux-surfaces.md) — full UX surface reference (all interfaces)

### Machine interface

For CI pipelines, scripts, and agent integrations that bypass the shell:

```bash
urace api call --command "status" --json
urace api serve --transport stdio     # MCP server for Claude, VS Code, etc.
urace api serve --transport a2a       # HTTP loopback for custom integrations
```

Full M2M reference: [`agent-integrations.md`](../power-users/agent-integrations.md)

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

*Full reference: [ux-surfaces.md](../power-users/ux-surfaces.md) · Power users: `urace <namespace> --help`*

---
→ [Next: CLI Reference](cli.md) — all commands in one place
