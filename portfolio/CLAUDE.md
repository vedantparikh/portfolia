# Portfolia

Self-hosted investment-portfolio tracker (holdings, P&L, TWR/XIRR, risk metrics, watchlists, broker-PDF import). Python 3.14 / FastAPI + SQLAlchemy 2.1 (sync) + Postgres 16 + Redis + pandas 3 / polars 2 / yfinance 1 backend (`python/app`); React 19 + React Router 8 + Vite 8 + Tailwind 4 frontend (`js`, Node 22). No Sentry/telemetry.

Git root is the parent dir (`../`: `.github/workflows/{ci,release}.yml`, `.pre-commit-config.yaml`, `.gitleaksignore`). Developer README: `README.md`. Adding features: `CONTRIBUTING.md`. Operations: `docs/RUNBOOK.md`. Decisions: `docs/adr/`. Refactor record and progress log: `REFACTOR_PLAN.md`.

## Host: shared NVIDIA Jetson AGX Xavier (prod server)
- arm64, JetPack 5.1.6/CUDA 11.4, 30 GB unified RAM, ~35 other containers (immich, jellyfin, ollama use the GPU). The Docker data-root is `/mnt/samsung_ufs/docker_data`, and eMMC `/` is nearly full.
- Host `python3` is 3.8 and there is no host `node`. **Everything runs through Docker.**
- Never touch other projects' containers, networks or volumes. Portfolio only publishes UI :3000 and API on 127.0.0.1:8000. DB/Redis stay unpublished.
- No GPU in portfolio images by default. GPU work goes through shared `ollama` or an opt-in `gpu` profile with a CPU fallback (plan §1b).

## Quick commands (cwd `portfolio/`)
```
scripts/setup.sh             # first run on a host: env files with generated secrets, shared network
scripts/verify.sh            # the gate: gitleaks, script tests, compose config, ruff/eslint/tsc, uv.lock, API types, pytest+mypy, migrations, vitest, vite build, prod images (~6 min)
scripts/check_migrations.sh  # throwaway Postgres: upgrade from empty, `alembic check` (drift), downgrade base, upgrade
scripts/verify.sh --stack    # + dev project portfolio-dev on :3200/:8200 and the Playwright e2e (does not touch the live portfolio project)
docker compose -f compose.dev.yaml up -d --wait  # dev → UI :3200, API 127.0.0.1:8200
docker compose -f compose.dev.yaml logs -f api
docker compose -f compose.dev.yaml logs -f worker   # background jobs (watchlist prices + alerts, every WORKER_INTERVAL_SECONDS)
```
Single test file (same env as the gate):
```
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/python/app:/app" -w /app -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/t.db \
  -e PYTHONDONTWRITEBYTECODE=1 portfolio-dev-api python -m pytest tests/unit/test_position_and_returns.py -q -p no:cacheprovider
docker run --rm -v "$PWD/js/src:/app/src:ro" -v "$PWD/js/vite.config.js:/app/vite.config.js:ro" portfolio-dev-app npx vitest run
```
Lint is part of the gate, and both linters must report 0. Autofix before committing:
```
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/python/app:/app" -w /app portfolio-dev-api sh -c 'ruff check --fix --no-cache . && ruff format --no-cache .'
docker run --rm -v "$PWD/js/src:/app/src" -v "$PWD/js/eslint.config.js:/app/eslint.config.js:ro" portfolio-dev-app npx eslint src --fix
```
Never run pytest inside the running `portfolio-api-1`, which is wired to the stack's Postgres.

## Architecture & patterns
- **Imports are rooted at `python/app`**: `from core.services...`, `from api.v1...`. Never `app.core...`.
- **Backend layers:** `api/v1/<feature>/router.py` → `core/services/<x>_service.py` (class takes `db: Session` in `__init__`) → `core/database/models/*` (`Mapped[]` columns). Prices and cash amounts are `Numeric(20, 8)`. Datetimes are timezone-aware. Percent and ratio columns stay narrower. Pydantic schemas live in `core/schemas/<feature>.py`. Holdings are `modules/portfolios`, series/risk/snapshots `modules/analytics`; analytics, assets and auth queries are in `modules/*/repository.py`. New code puts queries in a repository or service, never in a router, and never commits (the request commits).
- **Router mounting** is `create_app()` in `main.py`, which includes `api/v1/router.py`. Each router owns its prefix under `/api/v1` and one tag. A failed import stops startup. Watch route order: literal paths go before `/{id}`.
- **Auth:** `Depends(get_current_active_user)` from `core/auth/dependencies.py`. Every resource must be scoped by `user_id`. A portfolio route uses `get_owned_portfolio` (active portfolio belonging to the current user, otherwise 404). Access tokens are signed with PyJWT and kept in browser memory only. The refresh token is the httpOnly cookie `portfolia_refresh` (`Secure`, `SameSite=Strict`, path `/api/v1/auth`; ADR 0006); `/auth/refresh` reads only the cookie. `user_sessions.refresh_token` stores its SHA-256. Login checks a fixed bcrypt hash when the username does not exist.
- **Database session:** `get_db` is one unit of work per request: it commits when the request succeeds and rolls back when it raises. Endpoints that use it are plain `def`, so FastAPI runs them in a threadpool. A route stays `async def` only when it awaits I/O.
- **Health:** `/health/live` is 200 when the process is serving and does not check dependencies. `/health/ready` and `/health/` check Postgres and Redis, return 503 when either is down, and use a real UTC timestamp. The body is the check result (`status`, `database`, `redis`), not the error envelope, so Gatus can keep calling `/health/`. Compose healthchecks still call `/health/`.
- **Errors:** expected failures raise `DomainError` / `NotFoundError` from `core/errors.py` (both subclass ValueError; `OversellError` and `MissingPriceError` are DomainErrors). Their message is written for the user. Every failed response is `{error:{code,message}, request_id}` from `core/error_handlers.py` (validation errors also include `details`). `RequestContextMiddleware` sets `X-Request-ID` and logs one access line (method, path, status, duration). Logging is configured once, in `main.py`. SQLAlchemy does not echo SQL. An unhandled exception is logged and returned as `internal_error` / "Something went wrong". Routers that still catch an exception use `public_message(e, "fixed text")` for the `HTTPException` detail. The UI reads the message with `apiErrorMessage`. `tests/unit/test_error_messages.py` guards both the envelope and leaked exception text. NotFoundError → 404, other DomainError → 400.
- **FX:** an asset may be quoted in another currency than its portfolio. `core/domain/fx.py` scales `GBp`/`ILA` and converts closes and live prices with Yahoo's daily pair (`MarketDataService.get_fx_rates`, same 6h cache as history). Cash (`transaction.currency`, `total_amount`) converts only when it is not already the portfolio currency — a Trade Republic EUR amount on a USD listing is left as euros. A missing rate raises `MissingFxError` and the chart shows it. Manual create stores the listing currency for that cash unless the request (or the listing) is already the portfolio currency. `/portfolios/statistics/overview` still returns `totals[]` per portfolio currency and does not add EUR and USD portfolios together.
- **Financial math lives in `core/domain/`** (pure, no DB/network, golden-tested in `tests/unit/test_domain_engine.py` and `tests/unit/test_fx.py`): `positions.py` (split-adjusted trades in today's share units, FIFO lots with fees, `day_change`), `fx.py` (quote currency → portfolio currency), `valuation.py` (`daily_series`: value, FIFO cost basis, net invested and flows per trading day; a close older than 5 sessions stays in the value and sets `stale_price`; a held asset without a price raises `MissingPriceError`, never valued at cost), `returns.py` (TWR, XIRR, risk, `period_summary`, the one `RISK_FREE_RATE`), `benchmark.py` (`shadow_series`: the portfolio's own flows invested in a benchmark). Services only load data and call these: `PortfolioCalculationService.get_portfolio_series` converts then (memoised per request) feeds the series/performance/risk endpoints; `PortfolioService._holding_rows` converts the live price and feeds holdings, summary, overview and allocation. Never add another copy of a metric. Percent units are 15.0, not 0.15. The frontend displays backend values and never computes them.
- **Market data** goes only through `core/services/market_data_service.py`. Yahoo is `YahooMarketDataProvider` (4 at a time, two retries with backoff). Batch cache writes use one Redis pipeline. Symbol search is `GET /stock/symbols`; `search_listings` and `get_daily_ranges` serve the ISIN resolver from that same search. Valuation uses `get_daily_history` (closes split-adjusted but *not* dividend-adjusted, plus split and dividend events, cached 6h); dividends count only via DIVIDEND transactions. Tests mock the provider and never hit the network.
- **Schema:** Alembic is the only schema authority; the app never calls `create_all` (tests do, on SQLite). `start_api.sh` runs `alembic upgrade head` before the API starts and aborts on failure. Baseline = `alembic/versions/e97c82868ff5_baseline.py` (rewritten in place from the old no-op, so existing dev DBs stamped at it are already correct). A model change needs a migration: autogenerate it against a throwaway Postgres (pattern in `scripts/check_migrations.sh`), review it, drop any new Postgres enum types in `downgrade()`, and keep it expand/contract: additive in release N, destructive in N+1. The gate fails on model/migration drift.
- **Frontend:** pages and components are in `js/src/features/<feature>/` (shared widgets in `components/`, primitives such as `Modal` in `shared/ui/`). HTTP goes through `shared/api/client.ts` (axios, single-flight refresh) and each feature's `api.ts`; types come from `shared/api/generated/schema.ts`. Data is read with TanStack Query hooks in `features/<feature>/queries.ts`; writes invalidate their keys. Auth state is in `contexts/AuthContext.jsx`, the access token in `shared/auth/tokenStore.ts`. Errors are shown with `react-hot-toast`; formatting goes through `utils/formatters.jsx` (ESLint rejects `.toFixed(` and literal `$` amounts).
- **Config:** `config.py` `settings`, fed by compose `env_file` (dev `python/app/.env.docker`, `js/.env.docker`; prod and staging `../env/{prod,staging}.env`). Python deps: `python/app/pyproject.toml` + `uv.lock` only. These are gitignored secrets: never print or commit them. When you add a key, also add it to the matching `.env.example`.
- **Compose:** `compose.yaml` is production (project `portfolio`, UI :3000, API loopback :8000; `app`, `api`, `worker`, `migrate` are images only: `portfolia-{web,api}:prod` unless `PORTFOLIO_WEB_IMAGE` / `PORTFOLIO_API_IMAGE` point at GHCR). Its Postgres keeps the `build:` block the live container was created from and reads `python/app/.env.docker`; `verify.sh` fails if its config hash differs from the live container's. Redis and the app services read `../env/prod.env`. `compose.dev.yaml` is dev and CI (project `portfolio-dev`, bind mounts, reload, Vite, :3200/:8200). `compose.staging.yaml` overlays production as `portfolio-staging` (:3100/:8100, own volumes, `../env/staging.env`). A bare `docker compose` here selects `compose.yaml`.
- **Release and operations** (details in `docs/RUNBOOK.md`): `release.yml` publishes `ghcr.io/<owner>/portfolia-{api,web}` (`edge` + `sha-<short>` after CI on master, `X.Y.Z` + `X.Y` on a `v*` tag; Trivy fails on a fixable critical CVE). `scripts/deploy.sh prod X.Y.Z` dumps, migrates, restarts api/app/worker with `--no-deps`, smoke-tests and rolls back to `env/prod.deployed`; it never recreates Postgres or Redis. `scripts/staging-sync.sh` follows `edge`. `scripts/backup.sh` (14 daily, 8 weekly in `/mnt/samsung_ufs/backups/portfolio/`), `restore.sh`, `restore-drill.sh`. Timers in `deploy/` are installed by hand (root). Gatus checks `portfolio-app-1:8080` and `portfolio-api-1:8000/health/`. HTTPS is `https://ubuntu-1.tail13e229.ts.net:3443` (`tailscale serve` → :3000); port 3001 is Homepage and :443 on that name is Jitsi.

Product overview: `../README.md`. How to use the app, including the demo account: `../docs/USER_GUIDE.md`.

## Feature docs (read the one for the feature you touch)
Each feature has a `CLAUDE.md` with purpose, state, endpoints, UI, workflow, known gaps and plans. Frontend feature folders point to them.
- Engine: `python/app/core/domain/CLAUDE.md`
- Backend feature docs, each `python/app/api/v1/<dir>/CLAUDE.md`:

  | Feature | `<dir>` |
  |---|---|
  | Portfolios / holdings | `portfolio` |
  | Performance | `portfolio_calculations` |
  | Analytics | `analytics` |
  | Transactions | `transactions` |
  | PDF import | `account_statements` |
  | Watchlists | `watchlist` |
  | Assets | `assets` |
  | Market data | `market` |
  | Auth | `auth` |
  | Indicators | `statistical_indicators` |

- Frontend:
  - App shell, shared UI and conventions: `js/src/components/CLAUDE.md`
  - Dashboard: `js/src/features/dashboard/CLAUDE.md`
- When a change alters a feature's behaviour, state or gaps, update its doc in the same commit.

## Rules of engagement
- Never add, upgrade or remove a dependency (pip, npm, base image, GitHub Action) without asking first.
- After touching code, run the matching test file. **Before every commit, `scripts/verify.sh` must pass**, plus `--stack` if Docker, compose, env or startup changed. Never commit a red gate. CI runs the same script on arm64 and is a required check.
- One logical change per commit, using Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`). Work on a branch, never directly on `master`. Don't push or open PRs unless asked.
- `python/app/tests/quarantine.txt` only shrinks. Never add entries to hide a new failure. When a fix makes a quarantined test pass, delete its line (strict xfail fails otherwise).
- Don't write unnecessary comments, docstrings, tutorial-style text or boilerplate. Match the surrounding style.
- Ask before deleting Docker volumes, changing published ports or touching anything outside `portfolio/`.
- When a session establishes a new non-obvious fact about the project, update this file or the plan's progress log.

## Known state (2026-10-28)
- The refactor plan is finished apart from what `REFACTOR_PLAN.md` §6c lists as left on purpose (needs the user, GitHub settings, or a feature that does not exist yet).
- Docs: `../README.md`, `../docs/USER_GUIDE.md`, `README.md`, `CONTRIBUTING.md`, `docs/RUNBOOK.md`, `docs/adr/` and the feature `CLAUDE.md` files. The old `python/app/docs/`, `STARTUP_GUIDE.md` and the deployment checklist were folded into those and deleted.
- Gate, last recorded: ruff, eslint and tsc clean; 407 backend tests passed, quarantine empty; 12 Vitest tests; Playwright smoke passing.
- Demo data (`scripts/seed_demo_application.py --reset`, run inside `portfolio-api-1` against `http://localhost:8000`) uses real Yahoo prices, splits and dividends over ~3 years; an independent replay matched the engine to the cent on every day. The seed sends the refresh cookie itself (an http client will not return a `Secure` cookie).
- Advance-risk beta uses the `^GSPC` price index.
- `tests/unit/test_calculation_snapshots.py` pins every computed number (engine, risk, indicators, analytics) against `snapshots/calculations.json`. If it fails, a number the app shows changed: fix the regression, or regenerate with `UPDATE_SNAPSHOTS=1` only for an intended change and explain it in the commit.
- Tailwind 4: theme tokens live in `@theme` in `src/index.css` (there is no `tailwind.config.js`). Use slash opacity (`bg-black/50`), not the removed `bg-opacity-*`.
- ESLint stays on 9 until `eslint-plugin-react` supports 10. ruff `target-version` stays py312 on purpose (see pyproject). MSW 3 calls the unhandled-request option `onUnhandledFrame`.
- Lint policy: ruff ignores E501 (the formatter owns line length) and E712 (SQLAlchemy `== True`). ESLint has `react/prop-types` off. Use `eslint-disable-next-line react-hooks/exhaustive-deps -- <reason>` only when adding the dependency would change when the effect runs.
- FastAPI 0.143 wraps included routers in a private `_IncludedRouter`, so `app.routes` does not list endpoints. Test routing through `TestClient` (see `tests/unit/test_route_order.py`). Integration tests use an `https://testserver` client so the `Secure` cookie comes back.
- The SQLite test DB returns naive datetimes, so `calculate_portfolio_performance` (aware `now()` minus `transaction_date`) can't run against `test_db`. Test the engine through `get_performance_series` or stub it.
- Dev stack: `main.py`, `config.py`, `start_api.py` etc. are **single-file** bind mounts. A tool that replaces a file atomically (e.g. `ruff format`) leaves the container on the old inode — `docker compose restart api` after editing them. Directory mounts (`core/`, `api/`) are fine.
- Technical indicators (`utils/indicators/`) are pinned to the `ta` library (a dev dependency in `pyproject.toml`) by `tests/unit/test_indicator_reference.py`; deliberate differences (OBV start, PSAR two-lows cap) are documented there.
- `docker system prune -a` on this host deletes every image no running container uses, including freshly built `portfolia-*:prod` images; build right before starting a container.
