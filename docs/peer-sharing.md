# Peer improvement exchange

Sharing, networking and LAN advertising start disabled. Merely importing URACE or inspecting status creates no identity, listener or model request. Peer selection uses local rules and observations without an executor call.

Use `product exchange` for this product's sharing. `product list` still lists ordinary owner products; improvement workers are controlled separately under `product improvements`.

- `status` shows permissions, features, peer pseudonyms and aggregate events.
- `settings show` / `settings set --enabled true` opt in. Enable `--network true` separately for transfers. Disabling sharing also disables networking and advertising. `--auto-select false` disables the optional metadata selection worker.
- `peer identity` displays the public exchange certificate after opt-in. Exchange certificates through a trusted channel. `peer add --certificate FILE --endpoint https://HOST:PORT` pins a peer; discovery never grants trust.
- `feature define FEATURE --wanted true --offered true --depends-on OTHER --wants RETURN_FEATURE` declares a full feature definition. Omit dependency/return flags only when none are required. Advertising a feature still needs permission for the particular recipient.
- `rule set PEER FEATURE send|receive --allow true|false` grants or denies one direction for that peer and feature. All dependencies need permission. The default is deny.
- `peer block PEER` overrides all permissions. Unblocking clears its grants, requiring deliberate new grants. Blocking prevents new admissions and queued qualification/incorporation; already admitted in-flight transfers cannot be recalled; it cannot retrieve copies already sent or blindly remove installed code.
- `bundle prepare PEER FEATURE --file SOURCE --reviewed` creates a signed, recipient-bound outgoing artifact after explicit content review. Inspect the exact source first. It does not send it.
- `bundle send DIGEST` transfers it to that peer's quarantine. `bundle import --file BUNDLE` supports offline import. A confirmed transfer is not acceptance or actual use.
- `bundle inspect DIGEST` exposes the exact content and provenance. `bundle review DIGEST approved-for-evaluation|rejected|blocked --note TEXT` records the owner's decision.
- `bundle evaluate DIGEST` queues an approved `runtime-source-edits-v1` helper patch for the existing supervisor. It never executes downloaded code directly. The local scope, frozen authority, held-out checks, full regression, required gain, and drained deployment transaction all still apply. Other artifact types remain available for inspection and deliberate local work; they are not silently incorporated.
- `rank --want FEATURE` explains current candidate peers and temporary exclusions. Default needs come from wanted features. Fresh offers and reciprocal terms establish potential relevance, not proven utility. Qualified local outcomes and observed delivery records are separate from peer claims.
- `network refresh --limit 1` checks a bounded number of pinned peers' offers. Backoff is finite; stale or nonmatching peers are reconsidered. Refresh order favors peers least recently checked so successful early peers cannot monopolize exploration.
- `network discover --seconds 3` uses optional standard DNS-SD, installed through the `peer-discovery` package extra. Results are untrusted candidates. Manual HTTPS endpoints work without this extra. LAN multicast does not solve public Internet rendezvous, NAT or relay requirements.
- `network serve --host 127.0.0.1 --port 8766` runs an explicit foreground mutual-TLS artifact listener. It also runs one bounded offer-refresh worker while auto-selection is enabled. There is no listener autostart and no second trial supervisor. Advertising additionally requires `--advertise true`, the discovery extra and an explicit local interface address.
- `audit --detail --limit 50 --offset 0 --peer-id PEER --feature-id FEATURE` offers filtered detail; omit `--detail` for aggregate feedback.

Offered, exported, sent, received, reviewed, qualified, applied and actually used are distinct. Actual invocation/use is not inferred from installation. Native model use by these local selection and transport operations is zero. Remote production costs remain unknown. Local transfer budgets and request limits include attempted operations; a timeout is unconfirmed delivery, not success.

Pseudonymous certificates and local audit chains provide attribution and corruption detection. They do not guarantee anonymity, equal utility, global reputation, resistance to multiple identities, or immutable history against the local owner. Addresses, network timing, content and public advertisements can correlate participants. Content review and declared dependencies cannot guarantee detection of every secret or hidden dependency.

No barter transaction waits for another transaction to finish or demands first delivery. Recommendations create no automatic obligation. This prevents a protocol-level reciprocal wait, but cannot guarantee interested peers, connectivity, useful contributions or a live community. This is an opt-in collaboration mechanism with fairness controls, not a proven fair marketplace or an absolutely optimal network.
