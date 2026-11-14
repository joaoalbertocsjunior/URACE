# Agent integrations

MCP exposes scoped URACE operations and resources to an executor. A2A lets an
independent agent submit, inspect and cancel finite URACE tasks. Both use the
same typed API, policy authorization, pause checks, jobs, resource accounting and
existing product acceptance mechanisms. Neither adds a second scheduler.

## Optional A2A endpoint

`urace api serve --transport a2a --policy /owner/path/policy.json --port 8765`

No listener starts by default. This command requires `URACE_A2A_TOKEN` in its
launch environment (32..512 token characters). `--token-env NAME` selects another
variable. Provision the secret through the owner's normal service/secret setup;
do not put it in command arguments, policy files, repository files or AGENTS.md.
The bearer secret is removed from delegated worker environments. No existing
credentials or client profiles are modified by installation.

The listener binds only `127.0.0.1`. Use an owner-managed authenticated TLS reverse
proxy/tunnel for remote agents; this command does not expose a public port or
provision remote infrastructure. One endpoint/token represents one scoped policy
identity. Use separate policies/listeners for distinct principals.

A2A protocol version **1.0**, JSON-RPC polling subset:
- Authenticated GET `/.well-known/agent-card.json` describes skills/security.
- POST `/rpc`: `SendMessage`, `GetTask`, `ListTasks`, `CancelTask`.
- Headers: `Authorization: Bearer <secret>`, `A2A-Version: 1.0` and
  `Content-Type: application/json` for POST.
- Streaming, push callbacks, extended cards, freeform inference and multi-turn
  task mutation are unsupported and are not advertised. Unsupported requests
  receive explicit errors. No arbitrary URL discovery or outbound delegation.

Example JSON-RPC request body:

```json
{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"messageId":"unique-stable-message-id","role":"ROLE_USER","parts":[{"data":{"command":"help","params":{}}}]},"configuration":{"returnImmediately":true}}}
```

Use `messageId` unchanged on retries. Different content/context with the same ID
is rejected. `returnImmediately` returns a task to poll; the default waits until
terminal. `GetTask`/`CancelTask` take `{"id":"TASK_ID"}`. `ListTasks` supports
context/status/time filters, 1..100 items/page, opaque cursor pagination and an
explicit `includeArtifacts` option. History is not retained by this adapter.

Discover exact operations/parameter schemas with MCP `urace_operations` or
`urace api commands`; the A2A data part has `command` and optional `params`.
Explicit owner policy grants and ordinary authority rules apply. Read-only is
the default; write jobs require the stable message identity and are rejected
while paused. Job status/resources stay within the selected policy/product.

Each terminal task returns the durable operation receipt as a structured
artifact, including native correlation and nullable usage. A completed operation
is **not** automatic acceptance of an improvement. Existing acceptance tests,
regression gates and product validators remain responsible for that decision.
HTTP client disconnects do not cancel already submitted jobs; server shutdown
cancels its unfinished work. Restart retains receipts without automatic replay.

## Project instructions

[AGENTS.md.example](AGENTS.md.example) is a template, not an active instruction
file. Adopt project-specific source paths and verification commands before use.
Do not overwrite existing instruction symlinks or ignore restrictions implicitly.
AGENTS.md gives stable task guidance; owner policy/configuration remains the
source of capability, resource and lifecycle authority. This installation does
not read or edit protected `.agents/`, `CLAUDE.md` or `AGENTS.md` files.

Protocol reference: https://a2a-protocol.org/latest/specification/
Instruction format: https://agents.md/

## Assessment and comparative value

Every three-hour operational review includes a comprehensive assessment with
source hashes, matching trial/execution identities, per-provider failures,
known/missing native usage, timing percentiles, quality and matched-comparison
reports. A resumed assessment epoch scopes new operational receipts without
resetting trial history, tokens or the original clock. Reports distinguish
historical/incompatible comparisons and current-engine evidence. A refreshed
summary file is never proof of a new executor call.

Transport reliability is distinct from output quality. Confidence intervals
state their independence/representativeness assumptions; repeated synthetic
runs cannot establish real-user reliability. Quality/efficiency comparisons
must preserve acceptance, count failures/repairs/waiting and separate providers.
Assess three-hour health first, then 12–24-hour matched results when enough pairs
exist; retain weekly/monthly long-run checkpoints. These times are estimates,
not evidence thresholds. Missing/low-coverage evidence withholds advantage.

Without users, benchmark evidence can justify bounded engineering utility.
Without real use cases or independently grounded representative tasks, it cannot
establish external relevance. To estimate whether URACE is worthwhile, compare
with standalone AI on the same tasks/tools/models/budgets and require a material
quality/delivery/recovery or time/token advantage after orchestration costs.
Actual user value and market fit remain separate claims needing external use.

## Inspect context, feature verification and comparative readiness

Use the existing grouped interface:

```sh
urace trial status analysis --kind runtime --json
urace trial status analysis --kind product --json
```

`comprehensive_assessment.coverage_and_value_readiness` includes the lossless
product-context inventory, per-context selection/acceptance history, feature/test
source links and sample-gated matched comparisons. It explicitly distinguishes
static preservation, model context, tool availability and unproven global
semantic consistency. This computes reports without inference calls.

Comparisons remain unavailable unless a single provider/requested-effort profile
has sufficient matched cases, required scenario-family coverage and measured
quality, time and tokens. Eligible reports include time/token savings and their
paired percentiles/conditional bootstrap intervals. Failed measured workflows
retain costs and delivery failures. No overall percentile of product worth is
invented; it needs validated value weights and a defined reference population.
Owner qualification receipts are source-bound; stale passing suites are not
silently reused. Static test links are not execution/branch or full live coverage.

Claude retry-exhaustion receipts now preserve bounded diagnostic categories and
a hash of provider error details without retaining their raw text. Missing error
details remain unknown. Retry limits, provider backoff and acceptance checks are
unchanged; this is a provenance correction, not proof the external failure is
resolved.
