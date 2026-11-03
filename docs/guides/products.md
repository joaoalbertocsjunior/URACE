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

## Products Beyond Software

URACE's improvement model is not limited to code. Any product with measurable quality metrics can be registered — including content pipelines, AI-generated media, ML models, and data pipelines.

**Any pipeline qualifies** — URACE is product-agnostic at its boundary: it improves the *pipeline* that produces the output, not the output itself.

| Product | Types | Example metrics | Executor path |
|---------|-------|-----------------|---------------|
| Game | `software`, `media` | FPS, retention, bug count | Build/test pipeline via `script` adapter |
| Book | `content` | Readability score, chapter completion, editor rating | Style checker or writing API via `http` adapter |
| Scientific paper | `data`, `model` | Accuracy, reproducibility, citation score | Experiment runner via `script` adapter |
| Mobile app | `software` | Crash rate, load time, store rating | CI pipeline via `script` adapter |

URACE's scope is the **production pipeline**, not the output files themselves:
- For AI-generated video: URACE improves the prompt engineering, generation parameters, and post-processing pipeline that produces the video
- For ML models: URACE improves training scripts, hyperparameters, and evaluation pipelines
- For data products: URACE improves ingestion, transformation, and quality validation pipelines

Quality is measured by **score_delta** — any metric the user defines. For content products, useful metrics include: engagement rate, technical quality scores (SSIM, PSNR), A/B test results, or any pipeline-level KPI.

To register a non-software product:

```sh
urace init --type media
urace product register --type content MyContentPipeline
urace product register --type model MyModelTrainer
urace product register --type data MyDataPipeline
```

Available types: `software` (default), `content`, `media`, `model`, `data`

The `--type` flag sets default metric suggestions and provides executor context hints so improvement cycles are better targeted.

---

## Attach a GitHub Repository as a Product

Any public or private GitHub repo can be registered as a URACE product. URACE clones it locally, tracks it like any other product, and can run improvement cycles on it.

### Register

```sh
# Register a GitHub repo (clones into ./products/<repo-name>)
urace product register --github https://github.com/owner/repo

# Clone to a specific directory
urace product register --github https://github.com/owner/repo --clone-to ./my-dir
```

URACE does not modify the remote repository. All operations are local.

### Browse and Inspect

```sh
# List registered products
urace product list

# Show git status and recent changes
urace product git status
urace product git log
urace product git diff
```

### GitHub Workflow Integration

You can configure URACE to emit a GitHub Actions workflow file that runs improvement cycles in CI:

```sh
urace configuration github-workflow --repo owner/repo --output .github/workflows/urace.yml
```

The generated workflow calls `urace run` on each push and reports quality deltas back to the PR.

---

## Related

- [Controls](controls.md) — enable/disable capabilities
- [Derive](derive.md) — extract architectural patterns
- [Search](search.md) — search the context ledger
- [Quick Start](../getting-started/quick-start.md)
