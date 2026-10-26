# Production deployment

There is no production image and no deploy script yet. What runs on the home server is the **dev** compose file: source bind-mounted into the containers, the API reloads, the UI is the Vite dev server, and `DEBUG` comes from `.env.docker`.

Do not follow older copies of this checklist. They described Sentry, port 8080, a published Postgres, and `create_all` on startup. None of that is how the app works.

## What is true today

- Compose project name: `portfolio`.
- UI published on port 3000 (`PORTFOLIO_UI_PORT`). API published on `127.0.0.1:8000` only.
- Postgres and Redis are on the private compose network. No host ports.
- Memory limits and log rotation are set on every service.
- Secrets live in `python/app/.env.docker` and `js/.env.docker`. They are gitignored. Templates are the `.env.example` files.
- On start, `python/app/start_api.sh` waits for Postgres and Redis, runs `alembic upgrade head`, then starts the API. A migration failure stops the container.
- `config.py` refuses placeholder `SECRET_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, or an empty `REDIS_PASSWORD` when `ENVIRONMENT` is not development, dev, local, or test.
- The UI container joins `homepage_proxy-network`. Gatus checks it there, and checks API `/health/` on the portfolio network. Tailnet HTTPS is `https://ubuntu-1.tail13e229.ts.net:3443` via `tailscale serve` to port 3000.
- `scripts/backup.sh` dumps this database. The timer unit is `deploy/portfolia-backup.timer`. It is not installed by pulling the repo.

## Do not

- `docker compose down -v`, or delete the `postgres_data` volume, once the database has anything you care about.
- Publish 5432 or 6379.
- Point the UI at a public origin without replacing the dev server. The image that is running is not a static build behind nginx.
- Add a self-hosted GitHub Actions runner on this machine. The git repo is public.

## Planned, not available

Phase R in [REFACTOR_PLAN.md](REFACTOR_PLAN.md) is the intended production shape. Images, compose files, GHCR tags, `scripts/deploy.sh`, staging, and `scripts/backup.sh` are in the repo. An HTTPS name on the tailnet is still R.7.
