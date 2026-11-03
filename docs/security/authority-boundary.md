# Authority Boundary

[← Documentation](../index.md)

URACE can improve itself — but only with your approval. The authority boundary separates what the runtime can do autonomously from what requires explicit human authorization.

---

## The Core Rule

> The runtime cannot apply any change to itself without the owner explicitly running `urace update apply`.

No self-improvement is ever automatic. The runtime proposes; you decide.

---

## The Self-Evolution Workflow

When the runtime generates an improvement proposal (through `urace run` cycles):

1. The proposal is staged locally — not applied
2. You review it with `urace update explain`
3. You explicitly apply it with `urace update apply`

```sh
urace update download    # fetch staged proposal
urace update explain     # read the diff in plain language
urace update explain --json  # structured output for CI
urace update apply       # apply after review
```

If you don't run `urace update apply`, nothing changes. Ever.

---

## Protected Files

Certain files are protected by the authority boundary and cannot be modified by the runtime, even with `urace update apply`:

- Runtime governance and boundary enforcement code
- Cryptographic keypair files
- Per-product state and ledger data
- Owner-configured access control rules

The runtime knows which files are protected and will not include them in any self-improvement proposal. Proposals that attempt to modify protected files are rejected before staging.

---

## P2P Authority Boundary

The authority boundary also applies to P2P-sourced features:

- Borrowed features arrive in **quarantine**
- They are never executed or applied automatically
- You review and apply them deliberately

Even if a peer sends malicious code, the quarantine model ensures it cannot affect your system without your action.

---

## What the Runtime Can Do Autonomously

Within a single `urace run` cycle, the executor can:
- Analyze your product and propose operations
- Execute approved operations (if `--executor-enabled true`)
- Record outcomes in the context ledger
- Update token balance on quality gate pass

What it cannot do without your action:
- Modify itself
- Apply borrowed features
- Transfer tokens
- Change access control rules
- Modify protected files

---

## Related

- [Update Guide](../guides/update.md) — the full update workflow
- [Peer Security](peer-security.md) — quarantine model for borrowed features
- [Security Overview](overview.md) — all security guarantees
