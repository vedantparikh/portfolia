# Portfolia — development

Product overview and screenshots: [../README.md](../README.md). How to use the app: [../docs/USER_GUIDE.md](../docs/USER_GUIDE.md).

Self-hosted portfolio tracker. Python 3.14 / FastAPI + SQLAlchemy 2.1 + Postgres 16 + Redis, React 19 / Vite 8 / Tailwind 4. Code layout and the rules for changing it are in [CLAUDE.md](CLAUDE.md). Roadmap: [REFACTOR_PLAN.md](REFACTOR_PLAN.md).

## Run

Docker only. The home server has no current Node and its system Python is 3.8.

```bash
cd portfolio
cp python/app/.env.example python/app/.env.docker   # fill in secrets; never commit .env.docker
cp js/.env.example js/.env.docker
docker network create homepage_proxy-network        # once
docker compose -f compose.dev.yaml up -d --wait
```

| Service | Address |
|---|---|
| UI (`app`) | <http://localhost:3200> — host port overridable with `PORTFOLIO_UI_PORT` |
| API | <http://127.0.0.1:8200/docs> — loopback only, `PORTFOLIO_API_PORT` |
| Worker | no host port; watchlist prices and alerts |
| Postgres, Redis | unpublished; `docker compose -f compose.dev.yaml exec postgres psql` |

`compose.yaml` is the production file (project `portfolio`, ports 3000 and 8000). A bare `docker compose up` selects it. Use `compose.dev.yaml` for development so that does not attach to the live database.

`start_frontend.sh` and `setup-docker.sh` are not how this stack is started. `setup-docker.sh` only checks that Docker is installed.

The API container runs `alembic upgrade head` before it serves traffic. Schema changes go through Alembic. The app does not call `create_all`.

## Demo data

A `demo` user is loaded on this server. Username `demo`, password `DemoApp!234`. See the user guide before re-seeding: `--reset` deletes that user.

```bash
docker exec portfolio-api-1 python scripts/seed_demo_application.py \
  --base-url http://localhost:8000 \
  --email demo@example.com --username demo --password 'DemoApp!234'
```

## Checks

From `portfolio/`:

```bash
scripts/verify.sh            # compose config, lint, pytest, migration round-trip, UI build
scripts/verify.sh --stack    # also rebuilds and smoke-tests the stack
scripts/check_migrations.sh  # empty Postgres: upgrade, drift check, downgrade, upgrade
```

One test file, same environment as the gate:

```bash
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD/python/app:/app" -w /app \
  -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/t.db \
  -e PYTHONDONTWRITEBYTECODE=1 portfolio-api \
  python -m pytest tests/unit/test_position_and_returns.py -q -p no:cacheprovider
```

Do not run pytest inside the running `portfolio-api-1`. That process is connected to the stack database.

Lint, before committing:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/python/app:/app" -w /app portfolio-api \
  sh -c 'ruff check --fix --no-cache . && ruff format --no-cache .'
docker run --rm -v "$PWD/js/src:/app/src" -v "$PWD/js/eslint.config.js:/app/eslint.config.js:ro" \
  portfolio-app npx eslint src --fix
```

## Layout

```
portfolio/
  compose.yaml                # production: images only, project portfolio
  compose.dev.yaml            # dev: bind mounts, reload, Vite, project portfolio-dev
  compose.staging.yaml        # staging overlay: ports 3100/8100, own volumes
  docker-compose.yml          # previous live file; prefer the three above
  js/                         # React UI
  python/app/                 # API, worker, Alembic, tests
    api/v1/<feature>/         # routers; each has a CLAUDE.md
    core/domain/              # the only portfolio maths
    core/services/            # DB and Yahoo access
    workers/run.py            # watchlist prices and alerts
  scripts/verify.sh
```

Imports are rooted at `python/app` (`from core...`, `from api.v1...`).

Single-file bind mounts (`main.py`, `config.py`, `start_api.py`) go stale in the container if a tool replaces the file. `docker compose restart api` after editing those. Directory mounts (`core/`, `api/`) are fine.

## Releases

GitHub Actions publishes the production images to GHCR after this workflow is on `master`. A green CI run on `master` pushes `edge` and `sha-<short>`. Merging the release-please PR tags `vX.Y.Z` and pushes `X.Y.Z`, `X.Y` and `sha-<short>`. Both images are linux/arm64, with an SBOM and provenance.

`scripts/deploy.sh prod X.Y.Z` is how the Jetson switches to one of those tags. It backs up Postgres, runs migrations, and restarts the API, worker, and UI. Postgres and Redis containers are left as they are. A failed health check puts the previous version back. Until you run that command, the stack stays on the local `:prod` images.

## Further reading

[STARTUP_GUIDE.md](STARTUP_GUIDE.md), [python/app/docs/](python/app/docs/), and the index in [../docs/README.md](../docs/README.md).
