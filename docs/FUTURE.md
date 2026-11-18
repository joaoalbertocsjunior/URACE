# Future Work

Items that are intentionally deferred. Each entry has a trigger condition — do not implement until that condition is met.

---

## Web Interface

### Wallet — Full EVM Settlement
**Trigger:** Polygon mainnet launch.  
The `exchange/token_contract.json` stub is complete. The web UI already ships a greyed-out placeholder screen. Activate when the EVM settlement layer is live and `crypto_wallet.py` has mainnet keys.

### Full Mid-Cycle Graceful Stop
**Trigger:** Runtime SIGTERM handler upgraded.  
Currently `urace stop` sends SIGTERM which terminates mid-cycle operations immediately. The upgrade requires the signal handler in `_daemon.py` to wait for the current `cli.main(["auto", "--cycles", "1"])` call to complete before exiting, then save state. Until then the web UI shows a warning banner when a cycle is active.

### Rule Editing via Web UI
**Trigger:** Phase 4 ships and the governance layer is stable in production.  
Read-only rule and compliance views arrive in Phase 3. Editing requires confidence that the web auth boundary is sufficient to gate governance mutations.

### Multi-User Auth
**Trigger:** URACE deployed as a shared service (not localhost).  
The current single-token model is correct for local operator use. Replace with per-user sessions only when the deployment model changes.

---

## Infrastructure

### JS Build Pipeline
**Trigger:** Never, unless HTMX + SSE proves insufficient for a specific Phase 3+ requirement.  
Webpack/Vite adds ops burden with no benefit for the current feature set.

### Mobile Layout
**Trigger:** Evidence of operator use on mobile.  
URACE is an operator tool. Responsive polish is not a priority until usage data says otherwise.
