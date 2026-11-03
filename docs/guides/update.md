# Runtime Versioning

[← Documentation](../index.md)

The `update` command manages URACE runtime upgrades. You control when to download, review, and apply — nothing is automatic.

---

## The Three-Step Process

URACE updates follow a deliberate three-step workflow:

```
download → explain → apply
```

This ensures you always review what changes before it takes effect.

---

## Step 1: Download

Pull the latest runtime update from the official release URL:

```sh
urace update download
```

This downloads and stages the update locally. Nothing is applied yet.

---

## Step 2: Explain

See a human-readable summary of what changed:

```sh
urace update explain
```

With structured JSON output (for CI/CD or scripting):

```sh
urace update explain --json
```

The explain output shows:
- Which files will change
- What new capabilities are added
- What behaviors are modified
- Any breaking changes

**Review this before applying.** The authority boundary requires your explicit approval.

---

## Step 3: Apply

After reviewing, apply the staged update:

```sh
urace update apply
```

URACE will verify the update's cryptographic signature and integrity before applying. If verification fails, the update is rejected.

---

## Self-Evolution Updates

When the runtime generates a self-improvement proposal (from running `urace run` cycles), the proposal goes through the same download → explain → apply process. Self-generated improvements are never applied without your explicit `urace update apply`.

This is enforced by the authority boundary — see [Authority Boundary](../security/authority-boundary.md).

---

## Rollback

If an applied update causes problems:

```sh
urace update rollback
```

URACE keeps the previous runtime version staged until you explicitly clear it.

---

## Related

- [Authority Boundary](../security/authority-boundary.md) — how self-evolution is governed
- [Products Guide](products.md) — lifecycle context
- [CLI Reference](../reference/cli.md) — full update command options
