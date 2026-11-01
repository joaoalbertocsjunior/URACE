# Search: Context Ledger and P2P Audit

[← Documentation](../index.md)

URACE records everything — objectives, operations, evidence, decisions, and P2P activity — in a context ledger. The `search` command gives you full-text search over that history with filtering by kind, time, and source.

---

## Search the Context Ledger

```sh
urace search "query"
```

### Filter by Kind

```sh
urace search "latency" --kind objectives
urace search "retry" --kind operations
urace search "error spike" --kind evidence
urace search "architecture" --kind decisions
```

Supported kinds: `objectives`, `operations`, `evidence`, `decisions`

### Filter by Time

```sh
urace search "checkout" --since 2026-01-01
```

`--since` accepts ISO 8601 date strings.

### Limit Results

```sh
urace search "api" --limit 10
```

---

## Full Example

Find all evidence of latency improvements in the past month:

```sh
urace search "latency" --kind evidence --since 2026-10-01 --limit 25
```

---

## Search Compacted Ledger (P2P Audit)

The compacted ledger stores P2P activity — feature mints, borrows, trades, and network events. Use `urace compact search` to query it:

```sh
urace compact search "query"
```

### Filter by Kind, Peer, or Feature

```sh
urace compact search "mint" --kind feature_mint
urace compact search "borrow" --peer <peer_id>
urace compact search "latency" --feature api-response-feature
```

### Limit Results

```sh
urace compact search "equity" --limit 20
```

---

## View Compacted Ledger Summary

```sh
urace compact show
urace compact show --json
```

This shows aggregate stats: total entries, P2P activity counts, feature inventory, token flows.

---

## Traceability and Auditability

Every operation, decision, and P2P event is recorded with a timestamp, source, and outcome. The ledger is append-only — nothing is deleted. You can always trace why a decision was made or when a feature was borrowed.

For P2P network-level audit (consensus events, peer connections, bundle transfers):

```sh
urace exchange network-audit list
urace exchange network-audit list --kind bundle_transfer --peer <peer_id>
```

---

## Related

- [Products Guide](products.md) — what gets recorded during a cycle
- [Network Guide](../exchange/network.md) — P2P audit events
- [CLI Reference](../reference/cli.md) — full search options
