# URACE

**Autonomous improvement. P2P feature market. Token rewards for every contribution.**

Type a goal — URACE executes, verifies, and checkpoints. Borrow proven features from peers instead
of building from scratch. Mint yours and earn when others borrow them. Run a node and earn for
every delivery, relay, or block you seal.

Open-source, community-governed.

---

## Install

```sh
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

```sh
export ANTHROPIC_API_KEY=...  # or OPENAI_API_KEY
urace start                   # boot daemon, wire executor, join P2P
```

## Update

```sh
# one-liner (re-run installer):
curl -fsSL https://raw.githubusercontent.com/joaoalbertocsjunior/URACE/main/install.sh | sh

# pip:
pip install --upgrade urace

# npm:
npm install -g urace-cli@latest

# Homebrew:
brew upgrade urace

# conda:
conda update -c conda-forge urace
```

---

## Daily use

```sh
urace start                      # boot
urace                            # open shell — type goals, rules, context, questions
urace status                     # see health, goals, decisions, activity
urace stop                       # shutdown
```

Inside the shell:

```
> improve test coverage and reduce build time
→ Goal added

> never modify database migrations without a review
→ Rule added (prohibition)

> /events --follow               # live activity tail
> /status                        # daemon + network status
```

---

## Core commands

| Command | What it does |
|---------|-------------|
| `urace start` | Boot daemon + join P2P network |
| `urace` | Open shell (your main workspace) |
| `urace status` | Health, goals, decisions, activity |
| `urace source add --kind <kind>` | Connect data, executors, metrics, github, peers |
| `urace config` | Change settings |
| `urace update` | Apply spec updates |
| `urace stop` | Shutdown |

---

## Full documentation

→ [github.com/joaoalbertocsjunior/URACE](https://github.com/joaoalbertocsjunior/URACE)

---

v0.7.0 · Code: [Apache 2.0](https://github.com/joaoalbertocsjunior/URACE/blob/main/LICENSES/Apache-2.0.txt) · Spec: [CSL 1.0](https://github.com/joaoalbertocsjunior/URACE/blob/main/LICENSES/CSL-1.0.txt) · Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
