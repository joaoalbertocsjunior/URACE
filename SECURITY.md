# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | Yes       |
| < 0.3   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private vulnerability reporting:
1. Go to [https://github.com/joaoalbertocsjunior/URACE/security/advisories/new](https://github.com/joaoalbertocsjunior/URACE/security/advisories/new)
2. Fill in the advisory form.
3. Maintainers will acknowledge within 48 hours.

Alternatively, email the maintainers directly (see MAINTAINERS file).

## Disclosure Policy

- Maintainers will confirm the issue and assess severity within 5 business days.
- A fix will be prepared in a private fork.
- A coordinated disclosure date will be agreed with the reporter (typically 90 days from report, shorter for critical issues).
- A CVE will be requested if applicable.
- The fix and advisory will be published simultaneously.

## Scope

In scope:
- Arbitrary code execution via executor adapters
- P2P peer identity forgery or spoofing
- Ledger tampering (append-only invariant bypass)
- Authority boundary escapes (executor applying changes without user approval)
- Wallet key exposure
- Token economy manipulation (double-mint, credit forgery)

Out of scope:
- Vulnerabilities in executor tools that URACE calls (report upstream)
- Social engineering attacks
- Physical access attacks

## Security Architecture

Key properties maintained by the runtime:

| Property | Mechanism |
|----------|-----------|
| Authority boundary | Executor cannot apply changes without explicit `urace update apply` |
| Ledger integrity | Append-only JSONL; no entry is modified or removed after write |
| Wallet isolation | `~/.urace/wallet/key.json` chmod 600; private key never returned in output |
| P2P identity | secp256k1 keypair; peer certificates pinned before trust is granted |
| Quarantine model | Executor output staged, never auto-applied to production state |
