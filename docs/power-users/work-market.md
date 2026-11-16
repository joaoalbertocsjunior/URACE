# Work Market

[← Documentation](../index.md) · [Token Economics](../economy/tokenomics.md)

The work market lets you commission specific improvements from peers, with payment held in escrow until delivery is verified.

---

## How It Works

1. You create a work request describing what you need and set a budget
2. Peers submit bids
3. You accept the best bid — tokens move to escrow
4. The peer delivers the work
5. You verify delivery — escrow releases to the peer

If delivery is rejected or abandoned, tokens return to you.

---

## Create a Work Request

**Agora mode** (default — any peer can bid):

```sh
urace network work create "Add retry logic to API client" --budget 100 --complexity 0.4
# or explicitly:
urace network work create "Add retry logic to API client" --budget 100 --mode agora
```

**Cohort mode** (only high-reputation peers can bid):

```sh
urace network work create "Security audit" --budget 500 \
  --mode cohort --cohort-reputation-floor 75
```

- `--budget` is the maximum token amount you'll pay
- `--complexity` is a 0–1 score; high-complexity work can be automatically decomposed
- `--mode agora|cohort` selects the market mode (default: agora)
- `--cohort-reputation-floor N` rejects bids from peers with reputation < N (cohort mode only)

---

## List Open Requests and Bids

```sh
urace network work list --state OPEN
```

States: `OPEN`, `ACCEPTED`, `DELIVERED`, `VERIFIED`, `REJECTED`

---

## Accept a Bid

```sh
urace network work accept <request_id> --bidder <peer_id>
```

This moves the agreed token amount to escrow. The peer is now obligated to deliver.

---

## Verify Delivery

When the peer delivers:

```sh
# Approve delivery — tokens release to peer
urace network work verify <request_id> --approve true

# Reject delivery — tokens return to you
urace network work verify <request_id> --approve false
```

---

## Decompose High-Complexity Work

For large requests (complexity > 0.7), URACE can break the work into smaller tasks automatically. Each subtask gets its own escrow and verification step:

```sh
urace network work decompose "Large refactor" --budget 1000 --complexity 0.9
```

Decomposition requires the `--decompress-enabled` control to be on:

```sh
urace controls set --decompress-enabled true
```

---

## Bid on Work (as a Peer)

When you receive work requests from peers:

```sh
# List incoming requests
urace network work list --incoming

# Submit a bid
urace network work bid <request_id> --price 80 --eta-days 3
```

---

## Escrow Security

Tokens held in escrow are not spendable by either party. They are released only when:
- The requester approves delivery, or
- The deadline passes and neither party acts (dispute resolution returns to requester)

All escrow events are recorded in the P2P audit trail.

---

## Related

- [Features](exchange-features.md) — mint and borrow features directly
- [Reputation](exchange-reputation.md) — delivery record affects your reputation score
- [Network](exchange-network.md) — peer discovery to find workers
- [Tokenomics](../economy/tokenomics.md) — token supply and earn paths

---
→ [Next: Exchange Reputation](exchange-reputation.md) — token earnings, ledger, and leaderboard
