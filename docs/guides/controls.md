# Capability Controls

[← Documentation](../index.md)

URACE lets you enable or disable each capability independently, per product. This is useful for dry-run testing, gradual rollout, or locking down specific features.

---

## Show Current Controls

```sh
urace controls show
```

With JSON output:

```sh
urace controls show --json
```

---

## Set Controls

```sh
urace controls set [flags]
```

### All Available Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--executor-enabled` | bool | false | Allow the executor to run operations |
| `--freeform-enabled` | bool | true | Enable freeform text routing |
| `--p2p-mint-enabled` | bool | false | Allow minting features to the P2P network |
| `--p2p-sell-enabled` | bool | false | Allow listing features for sale |
| `--p2p-borrow-enabled` | bool | false | Allow borrowing features from peers |
| `--compress-enabled` | bool | false | Enable ledger compaction |
| `--decompress-enabled` | bool | false | Enable ledger decompression |
| `--machine-interface-enabled` | bool | false | Enable machine-readable (JSON) output interfaces |
| `--context-mint-enabled` | bool | false | Enable context minting globally |
| `--context-mint-objectives` | bool | false | Allow objectives to be minted as context |
| `--context-mint-evidence` | bool | false | Allow evidence records to be minted as context |
| `--context-mint-decisions` | bool | false | Allow decision records to be minted as context |
| `--context-mint-operations` | bool | false | Allow operation records to be minted as context |
| `--context-mint-checkpoints` | bool | false | Allow checkpoints to be minted as context |
| `--compliance-mode` | bool | false | Enable stricter audit logging and governance enforcement |

**Note:** Every `controls set` invocation writes a `config-capability-change` evidence record to the audit trail.

### Context Minting Hierarchy

`context-mint-enabled` is the **master gate**. All per-kind flags are ignored if the master gate is `false`.

```
context-mint-enabled: false  →  no context can be minted (all per-kind flags irrelevant)
context-mint-enabled: true   →  per-kind flags determine which data types are allowed
  context-mint-objectives: true  →  objectives can be included in equity grants
  context-mint-evidence: true    →  evidence records can be included
  ...
```

To enable objectives as mintable context:
```sh
urace controls set --context-mint-enabled true --context-mint-objectives true
```

Authority-protected fields (`authority`, `self_evolution_policy`, `config`) can never be minted regardless of flags.

---

## Common Patterns

**Disable executor for review-only mode:**

```sh
urace controls set --executor-enabled false
```

**Enable the full P2P stack:**

```sh
urace controls set --p2p-mint-enabled true --p2p-sell-enabled true --p2p-borrow-enabled true
```

**Enable machine interface for CI/CD pipelines:**

```sh
urace controls set --machine-interface-enabled true
urace status --json
```

**Disable freeform routing (strict command-only mode):**

```sh
urace controls set --freeform-enabled false
```

---

## Compliance Mode

When compliance mode is on, every state-modifying command requires an evidence record and peer role checks are enforced on exchange operations. Use this for regulated environments or audit-sensitive deployments.

```sh
# Enable compliance mode
urace controls set --compliance-mode true

# Disable compliance mode
urace controls set --compliance-mode false
```

### Compliance Posture Inspection

Inspect per-domain compliance status and history:

```sh
urace compliance --json                        # all domains + recent records
urace compliance --domain authority --json     # single domain
urace compliance --history 20 --json           # last 20 records
urace compliance --export /tmp/audit.json      # export all records as JSON
urace compliance --export /tmp/audit.jsonl     # export as JSONL (one record per line)
urace compliance --since 2025-01-01 --json     # filter by date range
urace compliance --strict --json               # exit 1 if any domain NON_COMPLIANT
```

The `--strict` flag is designed for CI pipelines: exit code 1 means non-compliant, 0 means pass. JSON output includes `strict_pass: bool` for scripting.

### Security Audit

Run a full security audit at any time (includes optional GitHub release integrity check):

```sh
urace security audit --json                    # full audit including GitHub release check
urace security audit --no-network --json       # offline mode: skip GitHub release check
```

Checks: wallet key present, consensus threshold ≥ 3, compliance mode status, circuit breaker health, exchange certificate, GitHub release asset match. Overall `PASS` only if no `WARN` checks.

---

## Exchange-Level Controls

Exchange capabilities have their own settings managed separately:

```sh
urace exchange settings set --enabled true --network true --advertise true
urace exchange settings show
```

See [Exchange Setup](../exchange/setup.md) for exchange-specific controls.

---

## Related

- [Products Guide](products.md) — lifecycle context for when to use controls
- [Exchange Setup](../exchange/setup.md) — exchange-level enable/disable
- [CLI Reference](../reference/cli.md) — full command reference
