# 0005 Trunk, GHCR images, pull-based deploys

**Context.** One developer, a public repo, a home server that must not run code from pull requests.

**Decision.**
- Trunk-based; short branches merge by squash after the `verify` check (`scripts/verify.sh --stack` on `ubuntu-24.04-arm`).
- Conventional Commits drive release-please (SemVer, `CHANGELOG.md`).
- Images are built once in GitHub Actions and pushed to GHCR: `edge` + `sha-<short>` from `master`, `X.Y.Z` + `X.Y` on a release tag, with SBOM, provenance and a Trivy gate on critical CVEs.
- The Jetson pulls: staging follows `edge` by timer, production is `scripts/deploy.sh prod X.Y.Z` (dump, migrate, restart, smoke, automatic rollback). No self-hosted runner, no SSH from GitHub.
- Migrations are expand/contract so rollback is an image swap.

**Consequences.** A few seconds of downtime per deploy is accepted. Blue/green is possible later with two app stacks. Runbook: `docs/RUNBOOK.md`.
