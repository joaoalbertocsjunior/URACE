# Features: Mint, Borrow, and Trade

[← Documentation](../index.md) · [Token Economics](../economy/tokenomics.md)

Features are atomic, independently deployable software capabilities. Here's how to mint your own to the network, borrow from peers, and trade equity stakes.

---

## Mint a Feature

After building and verifying a capability, grant equity and list it:

```sh
# Grant equity (register you as the creator)
urace network equity grant <feature-id> --creator <your-peer-id>

# List it for sale at a borrow price
urace network equity list-for-sale <feature-id> --bp 5000 --price 80
```

- `--bp` is your equity stake in basis points (5000 = 50% of 10,000)
- `--price` is the borrow price in URACE units. A configured creator reference may impose an estimate-based listing ceiling; it is not a verified executor cost.

When another peer borrows the feature, you earn tokens proportional to your equity stake. The earn amount is computed at fill time by `mint_per_adoption()` — it scales with adoption rank, network size, feature complexity, and current supply pressure. First adopters earn the most; earn decays as saturation is approached. See [Node Rewards](../economy/node-rewards.md#creator-earn--how-the-amount-is-computed) for the full formula.

---

## Browse Available Features

See what peers are offering:

```sh
urace network equity listings
urace network equity listings --feature api-response-feature
```

---

## Borrow a Feature

Define a feature you want:

```sh
urace network feature define my-feature --wanted true
```

Set a rule to allow receiving it from a specific peer:

```sh
urace network rule set <peer_id> my-feature receive --allow true
```

Then borrow it:

```sh
urace network feature borrow <feature-id> --peer <peer_id>
```

Borrowed features arrive in quarantine — they are **never executed automatically**. Review and apply deliberately.

---

## Equity Holdings

See who holds equity in a feature and how much:

```sh
urace network equity holdings <feature-id>
```

---

## Fill a Listing

Buy an equity listing from another peer:

```sh
urace network equity fill-listing <listing-id>
```

This transfers the equity stake and corresponding tokens.

---

## Auto-Trading

URACE can automate equity buying and selling based on your configured thresholds:

```sh
# Run one automated buying pass
urace network equity auto-buy

# Run one automated selling pass
urace network equity auto-sell

# Configure thresholds
urace network equity trade-config set
```

---

## Rate a Feature

After using a borrowed feature, rate it to improve recommendations across the network. Your ratings are combined with your improvement history to surface better suggestions over time.

```sh
# Rate by outcome
urace network feature rate --feature-id <feature-id> --outcome positive
urace network feature rate --feature-id <feature-id> --outcome negative
urace network feature rate --feature-id <feature-id> --outcome neutral

# Rate with an explicit quality score (0.0–1.0)
urace network feature rate --feature-id <feature-id> --outcome positive --score 0.85
```

---

## Get Feature Recommendations

Get a personalized list of features likely to improve your product, based on your ratings and past improvement history:

```sh
urace network feature recommend
urace network feature recommend --limit 10
```

---

## Feature Saturation

Check whether a feature has reached market saturation (most peers already have it):

```sh
urace network compact depletion <feature-id>
```

When saturation is high, the marginal value of selling more equity drops. Use this to time listings.

---

## Rules and Access Control

Control who can send or receive each feature:

```sh
# Allow a peer to send a feature to you
urace network rule set <peer_id> <feature_id> receive --allow true

# Allow yourself to send a feature to a peer
urace network rule set <peer_id> <feature_id> send --allow true

# Export all rules
urace network rule export --file rules.json

# Import rules from backup
urace network rule import --file rules.json
```

---

## Related

- [Exchange Setup](exchange-setup.md) — enable the exchange first
- [Work Market](work-market.md) — commission custom features
- [Reputation](exchange-reputation.md) — token earnings and reputation
- [Price Mechanics](../economy/price-mechanics.md) — pricing rules and guardrails

---
→ [Next: Work Market](work-market.md) — commission specific improvements from peers
