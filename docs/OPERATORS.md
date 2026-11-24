# ⚠️ OPERATORS — Action Required

## 1. Before First Node Goes Live (KEY SETUP)
- Generate release keypair: `urace p2p keygen --out ~/.urace/release_key.hex`
- Paste pub_hex into evolution_guard.py RELEASE_AUTHORITY_KEYS (currently has a dev-only test key)
- REQUIRED_SIGNATURES = 1 (raise to 2+ once you have a second key)
- P2P_UPDATE_BUNDLE_URL = "" — set to your GitHub Releases URL once repo is created
  Example: https://github.com/your-org/urace/releases/latest/download/p2p-bundle.json
- These constants live in urace/runtime/urace/evolution_guard.py (PROTECTED_FILES — pipeline cannot change them)

## 2. Issuing an Update
Full workflow:
  urace p2p build-update --key ~/.urace/release_key.hex --log-rekor --anchor-ots
  # → urace-update-bundle.json, logged to Rekor transparency log, anchored to Bitcoin via OTS
  # Host the bundle at P2P_UPDATE_BUNDLE_URL (GitHub Releases, etc.)
  urace p2p publish-update --bundle urace-update-bundle.json --key ~/.urace/release_key.hex \
    --url https://github.com/your-org/urace/releases/latest/download/p2p-bundle.json
  # Nodes detect the update within 60 min OR immediately when ≥2 peers seen on new version

## 3. product_files Change — Snapshot Reset Required
When product_files in config.json changes, delete state/stable/ on each live instance so a
fresh product snapshot is written on the next cycle:
  rm -rf /path/to/installation/state/stable/
  # urace will rebuild it automatically on next cycle start

## 4. Multi-Sig Threshold
- Currently REQUIRED_SIGNATURES = 1 (single key)
- Add a second key: run `urace p2p keygen`, add pub_hex to RELEASE_AUTHORITY_KEYS tuple
- Then raise REQUIRED_SIGNATURES = 2 for M-of-N security
- Never store private keys in the repo

## 5. Network Size Adaptive Thresholds
- Peer consensus trigger for update checks adapts to network size (default floor: 2 peers)
- Override: set p2p.consensus_trigger_min_peers in config.json
