# URACE Governance

## Project Roles

| Role | Responsibilities | How to Become |
|------|-----------------|---------------|
| **Maintainer** | Merge PRs, cut releases, set direction | Nominated by existing Maintainers after sustained contribution |
| **Committer** | Review and approve PRs | Nominated after 5+ merged contributions |
| **Contributor** | Open issues, submit PRs | Open to anyone |

Current Maintainers: see [MAINTAINERS](MAINTAINERS) file.

## Bootstrap Period

URACE is currently in a **bootstrap period**: the founding maintainer (`joaoalbertocsjunior`) holds sole merge rights until a second independent Maintainer is confirmed. During this period:

- All decisions still follow the rules below, but quorum is waived where it requires more than one Maintainer.
- The founding maintainer has no special override authority beyond what the governance rules grant to any Maintainer.
- The bootstrap period ends when two Maintainers are listed in the [MAINTAINERS](MAINTAINERS) file and at least one has merged a non-trivial PR independently.

This is a time-bounded transitional state, not permanent single-vendor control.

## Decision Making

- **Routine changes** (bug fixes, docs, minor features): any Maintainer may merge after one Committer approval.
- **Significant changes** (new subsystems, protocol changes, breaking API changes): require two Maintainer approvals and a 72-hour review window.
- **Spec changes (§62z)**: the URACE specification (`URACE.md`) may only change in the same commit that ships the corresponding runtime implementation. Spec-only PRs that lack a runtime counterpart are automatically rejected regardless of approval count.
- **Governance changes**: require a majority vote of active Maintainers (>50%) and a 7-day comment period on the PR.

Decisions are made in public via GitHub pull requests and issues. No binding decisions in private channels.

## Contribution Requirements

All contributions must carry a Developer Certificate of Origin (DCO) sign-off:

```
git commit -s -m "your message"
```

By signing off you certify that you have the right to submit the contribution under the applicable project license (Apache 2.0 for code, CSL 1.0 for the specification). See [https://developercertificate.org](https://developercertificate.org).

## Releases

- Releases follow [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
- Version is the single source of truth in `runtime/pyproject.toml`.
- A signed Git tag `vX.Y.Z` on `main` triggers automated publish to PyPI, npm, and downstream packaging.
- Release notes are generated from the commit log.

## Code of Conduct

This project follows the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Report violations to the maintainers via the security contact in [SECURITY.md](SECURITY.md).

## License

Dual-license:
- **Code** (`runtime/`, tooling): [Apache 2.0](LICENSES/Apache-2.0.txt)
- **Specification** (`URACE.md`): [Community Specification License 1.0](LICENSES/CSL-1.0.txt)

The CSL 1.0 governs the specification text and its implementability terms. Its purpose is to allow anyone to implement the URACE specification royalty-free while ensuring the specification itself remains a stable, community-governed standard — consistent with Linux Foundation project norms for open specifications.

Code contributions are accepted under Apache 2.0. Specification contributions are accepted under CSL 1.0.

## Maintainer Transition Path

When the community is ready to move beyond the bootstrap period:

1. A candidate Maintainer opens a PR adding themselves to `MAINTAINERS`.
2. The PR requires approval from the founding maintainer plus a 72-hour public comment period.
3. Once two independent Maintainers exist, merge rights transition to the full quorum model above.
4. If the founding maintainer becomes inactive (no merge or response within 90 days), any two Committers may jointly nominate a replacement Maintainer via a PR that remains open for 14 days.

## Linux Foundation Alignment

This project is designed for compatibility with LF AI & Data Foundation sandbox criteria:
- DCO sign-off enforced (automated; Dependabot bot commits exempt)
- Apache 2.0 (code) + CSL 1.0 (spec) — both LF-approved licenses
- Public governance with documented bootstrap period and transition path
- No single-vendor control over protocol or quality signal
- §62z spec invariant enforced: specification text cannot advance ahead of a shipping runtime implementation
