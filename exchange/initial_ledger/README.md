# Exchange Initial Ledger

This directory contains the bootstrap feature catalog shipped with URACE releases.
It is the reference ledger used to seed the P2P network on first run.

## What is this?

`initial_ledger.json` is the authoritative starting state for the P2P audit ledger.
It contains the initial set of feature grants, equity records, and audit rows that
define the baseline feature catalog for the URACE exchange network.

This file is committed to source control so it can be inspected, reviewed, and
included in releases. The runtime network ledger (`exchange/p2p_audit.json`) is
gitignored — it accumulates live network data and is deployment-specific.

## Searching and inspecting

Search the initial ledger (and any accumulated network ledger) via:

```
urace search --kind p2p
exchange compact search
exchange compact search --kind EQUITY_GRANT
exchange compact search feature_id=<feature-id>
```

## Compaction and compression

The ledger supports all standard audit commands:

```
# Compress old rows to local archive
exchange compact compress --older-than-days 30

# Decompress an archive for inspection
exchange compact decompress
exchange compact decompress <archive-id>

# Write a checkpoint for fast P2P bootstrap
exchange compact checkpoint

# Show sync tail (checkpoint + recent rows)
exchange compact sync-tail
```

## Note on gitignore

`exchange/` is gitignored (runtime network data syncs from the P2P network).
This `exchange/initial_ledger/` directory is explicitly excluded from that rule
so it remains part of the repository as a reference artifact.
