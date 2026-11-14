# URACE Runtime

Python 3.11+, no third-party runtime dependencies.

→ [Full UX reference](../docs/reference/ux-surfaces.md) · [5-minute guide](../docs/reference/ux-guide.md)

---

## Run locally (without pip install)

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

Both forms are equivalent. The installed `urace` command and `python3 -m urace` share the same launcher.

---

## Core commands

```sh
urace start
urace stop
urace status [goals|decisions|vitals|blockers|compliance|plan|watch]
urace config show
urace config evolution auto|never
urace config budget set --daily 20 --monthly 200
urace update download /path/to/new/URACE.md
urace update explain
urace update apply
```

---

## Shell (interactive)

```sh
urace                            # open interactive shell
```

Type goals, rules, context, or questions in plain language. Slash shortcuts:

```
/status   /events   /events --follow   /peers   /config   /stop   /exit
```

---

## Connect sources

```sh
urace source add mydb            --kind file     --connect ./data.json
urace source add metrics         --kind csv      --connect ./metrics.csv --direction read
urace source add claude          --kind executor --command claude-code --adapter claude-cli
urace source add                 --kind github   --repo owner/repo
urace source add coverage        --kind metric   --metric-source mydb --metric-path $.coverage
urace source add pass-rate       --kind vital    --numerator passed_tests --denominator total_tests
urace source list
urace source status
urace source enable <id>
urace source disable <id>
urace source remove <id>
urace source remove <id>         --kind metric
urace source remove <id>         --kind vital
```

Kinds: `file` `csv` `json` `sqlite` `api` `connector` `executor` `metric` `vital` `github` `product` `peer`

---

## Goals and context

```sh
urace add context "Customers need CSV export" --source "repository owner"
urace add goal "Deliver CSV export" --success-measure "A user can download a valid CSV" --target product --priority 80
urace goal list [--json]
urace goal cancel OBJECTIVE_ID
urace goal prioritize OBJECTIVE_ID --priority 80
urace goal schedule OBJECTIVE_ID --deadline 2027-02-01T00:00:00+00:00
urace goal pin OBJECTIVE_ID
urace goal defer OBJECTIVE_ID --until 2027-01-01T00:00:00+00:00
urace goal forecast [--json]
```

---

## Executors

```sh
urace executor status
urace executor attach
urace executor attach --id codex-secondary --command /path/to/codex --priority 90 --max-calls-24h 100 --max-calls-30d 1000
urace executor attach --id claude-secondary --adapter claude-cli --command /path/to/claude --priority 90
urace executor retry-policy --id codex-primary --retry-mode automatic --retry-delay-ms 60000 --retry-fallback-seconds 18000
urace executor detach --id codex-secondary
```

---

## P2P / Exchange

```sh
urace exchange node roles                        # show roles
urace exchange node roles --set bootstrap,relay  # restrict to relay+bootstrap only
urace exchange setup-node                        # check NAT, configure roles, print next steps
urace exchange network serve --host 0.0.0.0 --port 7301
urace exchange bootstrap add --address https://<ip>:<port>   # announce to network
```

Verify reachability:

```sh
urace status          # network_mode: internet | intranet | hybrid + peer count
```

Inside the shell:
```
> /peers              # connected peers
> /status             # node roles: relay, bootstrap, consumer, creator
```

For internet-wide discovery: `network_mode: internet` + accumulated peers → your node participates in DHT routing. Other nodes discover peers through yours.

---

## Autonomous mode

```sh
python3 -m urace autonomous --cycles infinity    # persistent, 30s interval
python3 -m urace autonomous --cycles 1           # single cycle
python3 -m urace autonomous --cycles 1 --force-discovery
```

---

## Reports and evaluation

```sh
urace report status [--json]
urace report export --output urace/generated/reports/latest [--xlsx]
urace evaluation show [--json]
urace evaluation set-weight goal_completion 0.4
urace vitals [--json]
urace check [--json]
```

---

## Portfolio (power)

```sh
python3 -m urace portfolio preflight urace/state/portfolio-workflow.json
python3 -m urace portfolio launch urace/state/portfolio-workflow.json
python3 -m urace portfolio auto urace/state/portfolio-workflow.json --cycles 10
python3 -m urace portfolio feedback [--json]
python3 -m urace portfolio status
python3 -m urace portfolio commands
```

---

## Tests

```sh
python3 -m unittest discover -s tests -v
```

---

v0.7.0 · State boundary: `urace/state/` (never committed) · Spec: [`../../URACE.md`](../../URACE.md)
