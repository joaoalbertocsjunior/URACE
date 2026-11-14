# P2P Bootstrap Infrastructure

**Status:** Phase A active — LAN discovery available; internet bootstrap peers list empty until first node is registered.

---

## How peers discover each other

URACE uses a three-phase bootstrap strategy. Each phase is additive — LAN always works, internet becomes available as peers register.

### Phase A — LAN (active now)

mDNS/Zeroconf is included in the base install. Peers on the same local network discover each other automatically with no configuration.

```sh
urace init --auto              # enables hybrid network mode, starts LAN discovery
urace exchange network peers   # lists discovered LAN peers
```

### Phase B — Internet bootstrap via peer list (pending first node)

A JSON file at `exchange/bootstrap_peers.json` in the main repo serves as the canonical bootstrap peer list. `urace init --auto` fetches it on first run and adds any listed peers automatically.

To register your node as a bootstrap peer:
1. Run `urace exchange network public-address --json` to get your public address.
2. Submit a PR adding `"https://<your-ip>:<port>"` to `exchange/bootstrap_peers.json`.

Once merged, all future `urace init --auto` runs will discover your node.

### Phase C — DNS seeds (future)

When the network reaches sufficient scale, DNS seed records will provide redundant bootstrap without a single repo dependency. No timeline set.

---

## Current bootstrap peer list

The list is at [`exchange/bootstrap_peers.json`](../../exchange/bootstrap_peers.json). Currently empty — be the first to register.

---

## Share your peer_id

Even before Phase B is live, you can connect to other URACE users directly:

```sh
# Get your peer_id
urace exchange peer identity --json

# Add a known peer manually
urace exchange bootstrap add https://<their-address>
```

Share your peer_id in the URACE community channels so others can connect to you.
