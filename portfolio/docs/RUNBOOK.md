# Runbook

Operating Portfolia on the Jetson home server. Commands run from `portfolio/` as `bubbly`. Release design: [ADR 0005](adr/0005-release-strategy.md).

## Environments

| Env | Project | Files | UI / API | Data | Env file |
|---|---|---|---|---|---|
| prod | `portfolio` | `compose.yaml` | :3000 (HTTPS `https://ubuntu-1.tail13e229.ts.net:3443`) / 127.0.0.1:8000 | volumes `portfolio_postgres_data`, `portfolio_redis_data` | `../env/prod.env`; Postgres reads `python/app/.env.docker` |
| staging | `portfolio-staging` | `compose.yaml` + `compose.staging.yaml` | :3100 / 127.0.0.1:8100 | own volumes, demo data | `../env/staging.env` |
| dev | `portfolio-dev` | `compose.dev.yaml` | :3200 / 127.0.0.1:8200 | own volumes | `python/app/.env.docker`, `js/.env.docker` |

Production Postgres keeps the `build:` block its container was created from, so `up` never recreates it; `verify.sh` compares `compose.yaml` with the live container's config hash. Moving it to the official image recreates the container: plan a window, take a dump first.

## Deploy

Images are built once by `.github/workflows/release.yml` and pulled from GHCR: `edge` and `sha-<short>` after CI passes on `master`, `X.Y.Z` and `X.Y` when the release-please PR is merged (tag `vX.Y.Z`). Trivy stops the release on a fixable critical CVE.

```bash
scripts/deploy.sh prod 0.2.0                       # pull, pg_dump, migrate, restart api/app/worker, smoke
scripts/deploy.sh prod 0.3.0 --allow-irreversible  # a release whose migration cannot be rolled back
```

`deploy.sh` pulls the tag, dumps the database to `/mnt/samsung_ufs/backups/portfolio/<env>-<version>-<UTC time>.dump`, runs the `migrate` service, restarts `api`, `app` and `worker` with `--no-deps`, waits for health and runs the smoke checks. It records the good version in `../env/<env>.deployed` and prunes images older than the last three releases. It never creates or recreates Postgres or Redis.

**Rollback** is automatic: a failed start or smoke check redeploys the version in `<env>.deployed` without migrating backwards. That works because migrations are expand/contract: a release only adds; dropping waits for the next release. By hand:

```bash
scripts/deploy.sh prod "$(cat ../env/prod.deployed)"
```

A migration that went wrong: restore the pre-deploy dump (below), then deploy the previous version.

Local images (no GHCR), e.g. before the first push: build `Dockerfile.prod` for both images, then `PORTFOLIO_API_IMAGE=portfolia-api:prod PORTFOLIO_WEB_IMAGE=portfolia-web:prod docker compose --profile migrate run --rm migrate` and `docker compose up -d --no-deps api app worker`. Do not `docker system prune -a` between build and start; an image no container uses is deleted.

## Staging

`scripts/staging-sync.sh` deploys `edge` to `portfolio-staging` when the GHCR digest changes (`../env/staging.digest`) and seeds the demo user when staging has no users. `deploy/portfolia-staging.timer` runs it every 15 minutes.

## Backups and restore

- `scripts/backup.sh prod` writes `daily/prod-YYYYMMDD.dump` (14 kept) and `weekly/prod-YYYY-Www.dump` (8 kept) under `/mnt/samsung_ufs/backups/portfolio/`, custom format. With `../env/backup.env` (see `deploy/backup.env.example`) it also uploads to Nextcloud.
- `scripts/restore.sh staging <dump>` loads a dump into staging. Production needs `--allow-prod`; it stops `api`, `app` and `worker` while it restores.
- `scripts/restore-drill.sh` restores the newest prod daily dump into staging and checks the table count.

Copying the volume of a running Postgres is not a backup.

## Install the timers (root)

```bash
sudo install -d -o bubbly -g bubbly -m 700 /mnt/samsung_ufs/backups/portfolio   # backup.sh and deploy.sh write here
sudo cp deploy/portfolia-*.service deploy/portfolia-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now portfolia-backup.timer portfolia-restore-drill.timer portfolia-staging.timer
systemctl list-timers 'portfolia-*'
```

Backup 03:10 daily, restore drill 04:10 on the 1st, staging sync every 15 minutes. On this host, host-level units belong in an Ansible role (`../../ansible/`); copy them there when they are final.

## Secrets

`../env/prod.env`, `../env/staging.env`, `python/app/.env.docker`, `js/.env.docker` (mode 600, gitignored). `scripts/setup.sh` creates missing ones. Production runs with `ENVIRONMENT=production`, which refuses placeholder secrets and an empty `REDIS_PASSWORD`.

Rotation:
- **JWT key:** change `JWT_SECRET_KEY` in `prod.env`, `docker compose up -d --no-deps api worker`. Everyone signs in again.
- **Redis:** change `REDIS_PASSWORD` in `prod.env`, `docker compose up -d redis api worker` (Redis is a cache; recreating it is safe).
- **Postgres:** take a dump, then `ALTER USER portfolio WITH PASSWORD '…'` in `psql`, put the same value in `prod.env` and `docker compose up -d --no-deps api worker`. Leave `python/app/.env.docker` alone: the Postgres container reads it only at first init, the dev stack shares it, and changing it changes the Postgres config hash.
- **SMTP:** new Brevo key in `EMAIL_HOST_PASSWORD`, restart `api`.

`verify.sh` runs gitleaks over the whole history; `.gitleaksignore` lists findings committed before the scan existed.

## Monitoring

Gatus checks `portfolio-app-1:8080` and `portfolio-api-1:8000/health/` (Postgres and Redis) and the tailnet certificate; alerts go to ntfy. The homepage tile shows container status. Logs: `docker logs --tail 200 portfolio-api-1` (one access line per request with `X-Request-ID`), `portfolio-worker-1`. There is no Sentry.

## Troubleshooting

- **API unhealthy after deploy:** `docker logs portfolio-api-1`. A `RuntimeError: Insecure configuration` lists the secret that is missing or a placeholder.
- **Migration failed:** `docker compose --profile migrate run --rm migrate` prints the Alembic error. `alembic downgrade` on prod is a data-loss decision; restore the dump instead.
- **Signed out after every reload:** the UI was opened over plain http on a tailnet IP, so the browser dropped the `Secure` refresh cookie. Use the HTTPS URL, or set `REFRESH_COOKIE_SECURE=false` (tailnet traffic is already encrypted by WireGuard).
- **Worker unhealthy:** `/tmp/worker-heartbeat` is older than two intervals; read its log.
- **Slow first load:** a cold Redis means Yahoo calls inside the request; the worker refills holdings within one interval.

## Do not

- `docker compose down -v` or delete `portfolio_postgres_data`.
- Publish 5432 or 6379.
- Register a self-hosted GitHub runner on this machine: the repo is public.
- Patch a running container by hand; ship a `fix:` release.
