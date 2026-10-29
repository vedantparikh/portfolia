# Portfolia — development

Product overview: [../README.md](../README.md). Using the app: [../docs/USER_GUIDE.md](../docs/USER_GUIDE.md). Operating production (deploy, rollback, backups): [docs/RUNBOOK.md](docs/RUNBOOK.md). Adding a feature: [CONTRIBUTING.md](CONTRIBUTING.md). Code rules for agents: [CLAUDE.md](CLAUDE.md). Decisions: [docs/adr/](docs/adr/).

Python 3.14 / FastAPI + SQLAlchemy 2.1 (sync) + Postgres 16 + Redis 7, React 19 / React Router 8 / TanStack Query 5 / Vite 8 / Tailwind 4. Everything runs in Docker: the home server's Python is 3.8 and it has no Node.

## First run

```bash
cd portfolio
scripts/setup.sh                                   # env files with generated secrets, shared network
docker compose -f compose.dev.yaml up -d --wait
```

`setup.sh` writes `python/app/.env.docker`, `js/.env.docker`, `../env/prod.env` and `../env/staging.env` (mode 600, gitignored) and never overwrites one. Fill in `EMAIL_*` for verification and password-reset mail (Brevo, `smtp-relay.brevo.com:587`).

| Service | Dev (`compose.dev.yaml`, project `portfolio-dev`) | Prod (`compose.yaml`, project `portfolio`) |
|---|---|---|
| UI `app` | <http://localhost:3200> (Vite, reload) | :3000 (nginx, static build), HTTPS `https://ubuntu-1.tail13e229.ts.net:3443` |
| API `api` | <http://127.0.0.1:8200/docs> | 127.0.0.1:8000 |
| `worker` | prices, FX, watchlist alerts, snapshots every `WORKER_INTERVAL_SECONDS` | same |
| `postgres`, `redis` | not published | not published |

A bare `docker compose` in this directory selects `compose.yaml`, the production file. Always pass `-f compose.dev.yaml` for development. Ports: `PORTFOLIO_UI_PORT`, `PORTFOLIO_API_PORT`.

The dev API runs `alembic upgrade head` before it serves (`start_api.sh`) and exits if that fails. Production migrates as a separate step (`docker compose --profile migrate run --rm migrate`, done by `scripts/deploy.sh`).

## Demo data

User `demo`, password `DemoApp!234` (three USD portfolios over ~3 years with real Yahoo prices, an empty EUR portfolio, a watchlist). Re-seed:

```bash
docker exec portfolio-api-1 python scripts/seed_demo_application.py \
  --base-url http://localhost:8000 --email demo@example.com --username demo --password 'DemoApp!234'
```

`--reset` deletes that user and every portfolio they own first.

## Architecture

```
browser ──► app (nginx :8080 / Vite) ──/api──► api (FastAPI, uvicorn)
                                                 ├─ api/v1/<feature>/router.py   validation, auth, one service call
                                                 ├─ modules/*, core/services/*   flow, queries (repositories in modules/*/repository.py)
                                                 ├─ core/domain/*                pure maths: positions, FX, valuation, returns, benchmark, alerts
                                                 ├─ core/services/market_data/*  the only Yahoo client (cached in Redis)
                                                 └─ Postgres (Alembic) · Redis (JSON cache, reset tokens, rate limits)
worker (same image) ── every 15 min: watchlist prices + alerts, holding prices, previous closes, daily history, FX, performance snapshots
```

- Every number the UI shows comes from `core/domain` (rules: [python/app/core/domain/CLAUDE.md](python/app/core/domain/CLAUDE.md)). The frontend formats, it never computes.
- Errors are `{error:{code,message}, request_id}`. `X-Request-ID` is on every response and in the one access-log line per request.
- Auth: a short-lived access token (`ACCESS_TOKEN_EXPIRE_MINUTES`) held in browser memory; the refresh token is an httpOnly cookie on `/api/v1/auth` ([ADR 0006](docs/adr/0006-refresh-token-cookie.md)).
- Health: `/health/live` (process), `/health/ready` and `/health/` (Postgres and Redis, 503 when down).

### API map

Every route is under `/api/v1` and needs `Authorization: Bearer <access token>` unless noted. Endpoint details and gaps are in the feature reference next to each router.

| Prefix | Feature reference |
|---|---|
| `/auth` (register, login, refresh, forgot/reset password, verify email are public and rate limited) | [auth](python/app/api/v1/auth/CLAUDE.md) |
| `/portfolios` | [portfolios](python/app/api/v1/portfolio/CLAUDE.md) |
| `/portfolios/calculations` | [performance](python/app/api/v1/portfolio_calculations/CLAUDE.md) |
| `/analytics` | [analytics](python/app/api/v1/analytics/CLAUDE.md) |
| `/transactions`, `/transactions/pdf` | [transactions](python/app/api/v1/transactions/CLAUDE.md) |
| `/account-statements` | [statement import](python/app/api/v1/account_statements/CLAUDE.md) |
| `/assets` | [assets](python/app/api/v1/assets/CLAUDE.md) |
| `/watchlists` | [watchlists](python/app/api/v1/watchlist/CLAUDE.md) |
| `/statistical-indicators` | [indicators](python/app/api/v1/statistical_indicators/CLAUDE.md) |
| `/stock` (symbol search: optional auth, 10/hour/IP anonymous), `/market-data` | [market data](python/app/api/v1/market/CLAUDE.md) |
| `/health/*` (public) | above |

Percent fields are percents (`15.0`). Money is decimal. Undefined metrics are `null`. `tests/unit/api_routes.txt` and `openapi_operations.txt` pin every path and operation id, and the frontend types in `js/src/shared/api/generated/schema.ts` are generated from the schema; the gate fails when any of them drift.

### Database

Postgres 16, named volume `postgres_data` (under the Docker data-root on `/mnt/samsung_ufs`). Alembic is the only schema authority; tests use SQLite with `create_all`. Pool defaults: `POOL_SIZE` 20, `MAX_OVERFLOW` 30, `POOL_TIMEOUT` 30, `POOL_RECYCLE` 3600.

| Models (`core/database/models/`) | Role |
|---|---|
| `User`, `UserProfile`, `UserSession` | Accounts, profile, refresh sessions (SHA-256 of the refresh token) |
| `Portfolio`, `PortfolioAsset` | Books, and the position cache rebuilt from transactions |
| `Transaction` | Trades, dividends, transfers. `source_key` makes a re-import skip a row |
| `Asset`, `MarketIndex` | The user's symbols (quote currency, ISIN) |
| `PortfolioPerformanceHistory` | Daily engine snapshot written by the worker |
| `PortfolioAllocation`, `RebalancingEvent`, `PortfolioBenchmark` | Targets, rebalancing records, benchmark names |
| `Watchlist`, `WatchlistItem`, `WatchlistAlert`, `WatchlistPerformance` | Lists, items, fired alerts, one price per item per day |
| `AnalysisConfiguration` | Saved indicator sets |

Price history is not stored; Yahoo history is cached in Redis for 6 hours.

```bash
docker compose -f compose.dev.yaml exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

## Checks

```bash
scripts/verify.sh            # the gate (~6 min): secrets scan, deploy/backup script tests, compose config,
                             # ruff + eslint + tsc, uv.lock, generated API types, pytest + mypy, migration
                             # round-trip, Vitest, Vite build, prod image build/size/non-root
scripts/verify.sh --stack    # + rebuild the dev stack, smoke URLs, Playwright e2e in Chromium
scripts/check_migrations.sh  # throwaway Postgres: upgrade, alembic check, downgrade base, upgrade
```

One backend test file, same environment as the gate (never inside the running `portfolio-api-1`, which is wired to real data):

```bash
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/python/app:/app" -w /app \
  -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/t.db -e PYTHONDONTWRITEBYTECODE=1 \
  portfolio-dev-api python -m pytest tests/unit/test_position_and_returns.py -q -p no:cacheprovider
```

Frontend unit tests (Vitest, jsdom, MSW; `src/**/*.test.*`):

```bash
docker run --rm -v "$PWD/js/src:/app/src:ro" -v "$PWD/js/vite.config.js:/app/vite.config.js:ro" \
  portfolio-dev-app npx vitest run
```

The Playwright smoke test (`js/e2e/`) runs against the dev stack in `verify.sh --stack`, as user `e2e`, which the gate creates.

Lint autofix before committing:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/python/app:/app" -w /app portfolio-dev-api \
  sh -c 'ruff check --fix --no-cache . && ruff format --no-cache .'
docker run --rm -v "$PWD/js/src:/app/src" -v "$PWD/js/eslint.config.js:/app/eslint.config.js:ro" \
  portfolio-dev-app npx eslint src --fix
```

## Layout

```
portfolio/
  compose.yaml  compose.dev.yaml  compose.staging.yaml   prod (images only) / dev / staging overlay
  deploy/                    systemd units: staging sync, nightly backup, monthly restore drill
  docs/RUNBOOK.md  docs/adr/
  scripts/                   setup, verify, deploy, staging-sync, backup, restore, restore-drill (+ their tests)
  js/                        React UI
    src/app/                 router, ProtectedLayout, error boundary
    src/features/<name>/     pages, components, api.ts, queries.ts
    src/shared/              api/client.ts (axios, refresh), api/generated/, auth/tokenStore.ts, ui/
    src/components/          shared widgets (charts, sidebar, search), Financial Concepts
    src/test/  e2e/          Vitest setup + MSW, Playwright
  python/app/                API, worker, Alembic, tests (imports rooted here: `from core...`)
    pyproject.toml uv.lock   the only dependency list
    api/v1/<feature>/        routers, each with a CLAUDE.md
    modules/                 portfolios (holdings), analytics (series, risk, snapshots), auth/assets repositories
    core/domain/             the only portfolio maths
    workers/run.py           the worker loop
```

## Configuration

`python/app/config.py` (pydantic-settings) reads the environment; templates are the `.env.example` files. When you add a key, add it there too (blank if secret).

| Key | Role |
|---|---|
| `ENVIRONMENT` | `development`, `dev`, `local`, `test` skip the secret check. Anything else refuses a placeholder or short `JWT_SECRET_KEY`, a placeholder `POSTGRES_PASSWORD`, an empty `REDIS_PASSWORD` and `ALLOWED_ORIGINS=*` |
| `POSTGRES_*`, `POOL_*` | Database and pool |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `REDIS_TTL_SECONDS` | Cache. Production Redis reads the same `env/prod.env`, so one value protects both |
| `JWT_SECRET_KEY` (`SECRET_KEY` fallback), `JWT_ALGORITHM` | Token signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` (`REFRESH_TOKEN_EXPIRE_MINUTES` overrides) | Lifetimes |
| `REFRESH_COOKIE_SECURE` | Default `true`. Set `false` only when the UI is opened over plain http on a host other than localhost; browsers drop a `Secure` cookie there and a reload signs you out |
| `WORKER_INTERVAL_SECONDS` | Worker period, default 900 |
| `PYTR_EXPORT_PATH`, `PYTR_SYNC_USERS` | Trade Republic sync: the pytr CSV in the shared folder Bachat and "Fetch from Trade Republic" write (prod: `/pytr/account_transactions.csv` from `../../trade-republic/output`, read-write on `api`, read only on `worker`; `PORTFOLIO_PYTR_DIR` overrides) and the usernames that may link a portfolio to it and log in to Trade Republic. Empty path = off |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_FROM` | Verification and reset mail |
| `ALLOWED_ORIGINS` / `FRONTEND_URL` | CORS |
| `API_URL` | Base URL the seed script calls |
| `LOG_LEVEL`, `LOG_DIR`, `LOG_FILE`, `LOG_JSON` | Logging is set up once in `main.py` (console + rotating file, 10 MB × 5). SQL is not echoed |

`TESTING=true` and `TEST_DATABASE_URL` switch pytest onto SQLite; never set them on a running stack.

## Troubleshooting (dev)

- **UI loads, `/api` is 404:** the Vite proxy comes from the bind-mounted `js/vite.config.js`; recreate `app` after changing it.
- **API keeps running old code:** `main.py`, `config.py`, `start_api.py`, `start_api.sh` are single-file mounts, and a tool that replaces the file (ruff format) leaves the container on the old inode. `docker compose -f compose.dev.yaml restart api`.
- **API exits on start:** a failed migration is fatal on purpose; read `docker compose -f compose.dev.yaml logs api`.
- **`network homepage_proxy-network not found`:** `scripts/setup.sh` or `docker network create homepage_proxy-network`.
- **Worker unhealthy:** `/tmp/worker-heartbeat` must be newer than two intervals.
- **Memory:** limits are UI 1 GB, API 2 GB, worker 384 MB, Postgres 1 GB, Redis 256 MB. The host is shared with ~35 containers; prefer shorter requests to higher limits.
- `docker compose down -v` deletes the volumes of the selected project. Never on `portfolio`.
