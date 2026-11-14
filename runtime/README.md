# URACE

**Autonomous improvement. P2P feature market. Token rewards for every contribution.**

Type a goal — URACE executes, verifies, and checkpoints. Borrow proven features from peers instead
of building from scratch. Mint yours and earn when others borrow them. Run a node and earn for
every delivery, relay, or block you seal.

Open-source, community-governed.

→ **[Full documentation: github.com/joaoalbertocsjunior/URACE](https://github.com/joaoalbertocsjunior/URACE)**

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

→ [5-minute guide](https://github.com/joaoalbertocsjunior/URACE/blob/main/docs/reference/ux-guide.md) · [Full reference](https://github.com/joaoalbertocsjunior/URACE/blob/main/docs/reference/ux-surfaces.md)

---

## Run from source (without pip install)

Python 3.11+, no third-party runtime dependencies.

```sh
cd /path/to/project
pip install -e runtime           # installs `urace` command from local source
urace start
```

Or without installing:

```sh
cd /path/to/project/runtime
python3 -m urace start
python3 -m urace status
```

---

## Connect sources

```sh
urace source add mydb            --kind file     --connect ./data.json
urace source add claude          --kind executor --command claude-code --adapter claude-cli
urace source add                 --kind github   --repo owner/repo
urace source add coverage        --kind metric   --metric-source mydb --metric-path $.coverage
urace source add pass-rate       --kind vital    --numerator passed_tests --denominator total_tests
urace source list
```

Kinds: `file` `csv` `json` `sqlite` `api` `connector` `executor` `metric` `vital` `github` `product` `peer`

---

## P2P / Exchange

```sh
urace exchange node roles --set bootstrap,relay  # restrict to relay+bootstrap only
urace exchange setup-node                        # check NAT, configure roles, print next steps
urace exchange bootstrap add --address https://<ip>:7301
```

```sh
urace status          # network_mode: internet | intranet | hybrid + peer count
```

---

## Tests

```sh
python3 -m unittest discover -s tests -v
```

---

v0.7.0 · Code: [Apache 2.0](https://github.com/joaoalbertocsjunior/URACE/blob/main/LICENSES/Apache-2.0.txt) · Spec: [CSL 1.0](https://github.com/joaoalbertocsjunior/URACE/blob/main/LICENSES/CSL-1.0.txt) · Copyright 2006–2026 Joao Alberto Cambauva dos Santos Junior
