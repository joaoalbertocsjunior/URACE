# URACE Governance

## Project Roles

| Role | Responsibilities | How to Become |
|------|-----------------|---------------|
| **Maintainer** | Merge PRs, cut releases, set direction | Nominated by existing Maintainers after sustained contribution |
| **Committer** | Review and approve PRs | Nominated after 5+ merged contributions |
| **Contributor** | Open issues, submit PRs | Open to anyone |

Current Maintainers: see [MAINTAINERS](MAINTAINERS) file.

## Decision Making

- **Routine changes** (bug fixes, docs, minor features): any Maintainer may merge after one Committer approval.
- **Significant changes** (new subsystems, protocol changes, breaking API changes): require two Maintainer approvals and a 72-hour review window.
- **Governance changes**: require a majority vote of active Maintainers (>50%) and a 7-day comment period on the PR.

Decisions are made in public via GitHub pull requests and issues. No binding decisions in private channels.

## Contribution Requirements

All contributions must carry a Developer Certificate of Origin (DCO) sign-off:

```
git commit -s -m "your message"
```

By signing off you certify that you have the right to submit the contribution under the project license (MIT). See [https://developercertificate.org](https://developercertificate.org).

## Releases

- Releases follow [Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
- Version is the single source of truth in `runtime/pyproject.toml`.
- A signed Git tag `vX.Y.Z` on `main` triggers automated publish to PyPI, npm, and downstream packaging.
- Release notes are generated from the commit log.

## Code of Conduct

This project follows the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Report violations to the maintainers via the security contact in [SECURITY.md](SECURITY.md).

## License

MIT. All contributions are accepted under the same license.

## Linux Foundation Alignment

This project is designed for compatibility with LF AI & Data Foundation sandbox criteria:
- DCO sign-off enforced
- MIT license
- Public governance
- No single-vendor control over protocol or quality signal
