# Product Lifecycle

[← Documentation](../index.md)

Here's how to manage your product through URACE's full lifecycle: adding goals, running cycles, inspecting progress, and checking status.

---

## Initialize a Product

```sh
urace init
```

Run this once inside your project directory. URACE creates a local state directory and registers the product.

---

## Add Objectives

Objectives are what you want to achieve. Add them in plain language:

```sh
urace add "Improve checkout conversion by 20%"
urace add "Reduce P99 API latency below 200ms"
urace add "Eliminate top 5 error categories in logs"
```

Objectives are stored in the context ledger and drive plan generation.

---

## Run an Improvement Cycle

```sh
urace run
```

Each run:
1. Selects the best next operation from the current plan
2. Executes it via the configured executor
3. Measures the quality delta
4. Records evidence in the context ledger
5. Earns tokens if the quality gate passes

Run repeatedly to accumulate improvements:

```sh
# Run until a goal is met or a limit is reached
urace run
urace run
urace run
```

---

## Check Status

```sh
urace status
```

With JSON output:

```sh
urace status --json
```

Status shows: active objectives, current plan state, recent operations, token balance, and quality score trend.

---

## Inspect Goals and Plans

```sh
# List all goals
urace inspect --goals

# List all plans
urace inspect --plans

# List recent operations
urace inspect --operations
```

---

## Search Your History

The context ledger stores all objectives, operations, evidence, and decisions. Search it:

```sh
urace search "latency"
urace search "checkout" --kind objectives
urace search "error" --kind evidence --since 2026-01-01 --limit 20
```

See [Search Guide](search.md) for full options.

---

## Manage Capabilities

Enable or disable per-product capabilities:

```sh
# Disable the executor (dry-run mode)
urace controls set --executor-enabled false

# Re-enable freeform routing
urace controls set --freeform-enabled true

# Show current controls
urace controls show
```

See [Controls Guide](controls.md) for all options.

---

## Related

- [Controls](controls.md) — enable/disable capabilities
- [Derive](derive.md) — extract architectural patterns
- [Search](search.md) — search the context ledger
- [Quick Start](../getting-started/quick-start.md)
