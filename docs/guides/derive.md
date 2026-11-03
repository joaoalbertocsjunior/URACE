# Derive: Architectural Pattern Extraction

[← Documentation](../index.md)

The `derive` command reads your product spec and extracts architectural patterns, mechanisms, schemas, protocols, and contracts. Use it to understand what your system has and suggest what it needs next.

---

## Basic Usage

Run with no arguments to extract all construct kinds:

```sh
urace derive
```

URACE reads your product spec, identifies architectural constructs, and outputs them grouped by kind.

---

## Filter by Construct Kind

Limit output to specific construct IDs:

```sh
urace derive --constructs AP0,AP1
```

Construct IDs are shown in previous derive output. Common kinds include:
- `AP` — Architectural Patterns
- `M` — Mechanisms
- `S` — Schemas
- `P` — Protocols
- `C` — Contracts

---

## Save Derived Constructs

Persist the results so they can be referenced in future cycles:

```sh
urace derive --save
```

Saved constructs become part of the context ledger and are available to `urace search`.

---

## Refresh Saved Constructs

Re-derive everything and update saved results:

```sh
urace derive --refresh
```

Use this after significant changes to your product spec.

---

## Freeform Derive

You can provide unstructured text describing what you need. URACE resolves what it can against existing constructs and routes the remainder through freeform processing:

```sh
urace derive "my system needs transaction rollback and retry logic"
```

This is useful when you know what you want but haven't yet expressed it in formal spec terms.

Combined with a specific construct filter:

```sh
urace derive --constructs AP0 "add circuit breaker to the API layer"
```

---

## Example Output

```
AP0: Request/Response Pattern
  - HTTP REST endpoints over TLS
  - Input validation at boundary
  - Structured error responses

M1: Retry Mechanism
  - Exponential backoff (base 2, max 30s)
  - Jitter: ±10% of delay
  - Max attempts: 5

S0: User Session Schema
  - session_id: UUID
  - created_at: ISO 8601
  - expires_at: ISO 8601
```

---

## Related

- [Products Guide](products.md) — run cycles after deriving constructs
- [Search Guide](search.md) — search saved derivations
- [Concepts](../getting-started/concepts.md) — what the lifecycle looks like
