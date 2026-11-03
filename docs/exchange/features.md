# Features: Mint, Borrow, and Trade

[← Documentation](../index.md)

Features are atomic, independently deployable software capabilities. Here's how to mint your own to the network, borrow from peers, and trade equity stakes.

---

## Mint a Feature

After building and verifying a capability, grant equity and list it:

```sh
# Grant equity (register you as the creator)
urace exchange equity grant <feature-id> --creator <your-peer-id>

# List it for sale at a borrow price
urace exchange equity list-for-sale <feature-id> --bp 5000 --price 80
```

- `--bp` is your equity stake in basis points (5000 = 50% of 10,000)
- `--price` is the borrow price in tokens — must be ≤ executor reference price

When another peer borrows the feature, you earn tokens proportional to your equity stake.

---

## Browse Available Features

See what peers are offering:

```sh
urace exchange equity listings
urace exchange equity listings --feature api-response-feature
```

---

## Borrow a Feature

Define a feature you want:

```sh
urace exchange feature define my-feature --wanted true
```

Set a rule to allow receiving it from a specific peer:

```sh
urace exchange rule set <peer_id> my-feature receive --allow true
```

Then borrow it:

```sh
urace exchange feature borrow <feature-id> --peer <peer_id>
```

Borrowed features arrive in quarantine — they are **never executed automatically**. Review and apply deliberately.

---

## Equity Holdings

See who holds equity in a feature and how much:

```sh
urace exchange equity holdings <feature-id>
```

---

## Fill a Listing

Buy an equity listing from another peer:

```sh
urace exchange equity fill-listing <listing-id>
```

This transfers the equity stake and corresponding tokens.

---

## Auto-Trading

URACE can automate equity buying and selling based on your configured thresholds:

```sh
# Run one automated buying pass
urace exchange equity auto-buy

# Run one automated selling pass
urace exchange equity auto-sell

# Configure thresholds
urace exchange equity trade-config set
```

---

## Feature Saturation

Check whether a feature has reached market saturation (most peers already have it):

```sh
urace exchange compact depletion <feature-id>
```

When saturation is high, the marginal value of selling more equity drops. Use this to time listings.

---

## Rules and Access Control

Control who can send or receive each feature:

```sh
# Allow a peer to send a feature to you
urace exchange rule set <peer_id> <feature_id> receive --allow true

# Allow yourself to send a feature to a peer
urace exchange rule set <peer_id> <feature_id> send --allow true

# Export all rules
urace exchange rule export --file rules.json

# Import rules from backup
urace exchange rule import --file rules.json
```

---

## Related

- [Exchange Setup](setup.md) — enable the exchange first
- [Work Market](work-market.md) — commission custom features
- [Reputation](reputation.md) — token earnings and reputation
- [Price Mechanics](../economics/price-mechanics.md) — pricing rules and guardrails
