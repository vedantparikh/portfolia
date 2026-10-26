# Portfolia

Self-hosted investment-portfolio tracker (holdings, P&L, TWR/XIRR, risk metrics, watchlists, broker-PDF import). Python 3.14 / FastAPI + SQLAlchemy 2.1 (sync) + Postgres 16 + Redis + pandas 3 / polars 2 / yfinance 1 backend (`python/app`); React 19 + React Router 8 + Vite 8 + Tailwind 4 frontend (`js`, Node 22). No Sentry/telemetry.

Git root is the parent dir (`../`: `.github/workflows/ci.yml`, `.pre-commit-config.yaml`). Roadmap, release strategy and progress log: `REFACTOR_PLAN.md`.

## Host: shared NVIDIA Jetson AGX Xavier (prod server)
- arm64, JetPack 5.1.6/CUDA 11.4, 30 GB unified RAM, ~35 other containers (immich, jellyfin, ollama use the GPU). The Docker data-root is `/mnt/samsung_ufs/docker_data`, and eMMC `/` is nearly full.
- Host `python3` is 3.8 and there is no host `node`. **Everything runs through Docker.**
- Never touch other projects' containers, networks or volumes. Portfolio only publishes UI :3000 and API on 127.0.0.1:8000. DB/Redis stay unpublished.
- No GPU in portfolio images by default. GPU work goes through shared `ollama` or an opt-in `gpu` profile with a CPU fallback (plan §1b).

## Quick commands (cwd `portfolio/`)
```
scripts/verify.sh            # the gate: compose config, lint, pytest in API image, migration check, vite prod build (~3 min)
scripts/check_migrations.sh  # throwaway Postgres: upgrade from empty, `alembic check` (drift), downgrade base, upgrade
scripts/verify.sh --stack    # + dev project portfolio-dev on :3200/:8200 (does not touch the live portfolio project)
docker compose -f compose.dev.yaml up -d --wait  # dev → UI :3200, API 127.0.0.1:8200
docker compose -f compose.dev.yaml logs -f api
docker compose -f compose.dev.yaml logs -f worker   # background jobs (watchlist prices + alerts, every WORKER_INTERVAL_SECONDS)
```
Single test file (same env as the gate):
```
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD/python/app:/app" -w /app -e TESTING=true -e TEST_DATABASE_URL=sqlite:////tmp/t.db \
  -e PYTHONDONTWRITEBYTECODE=1 portfolio-api python -m pytest tests/unit/test_position_and_returns.py -q -p no:cacheprovider
```
Lint is part of the gate, and both linters must report 0. Autofix before committing:
```
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/python/app:/app" -w /app portfolio-api sh -c 'ruff check --fix --no-cache . && ruff format --no-cache .'
docker run --rm -v "$PWD/js/src:/app/src" -v "$PWD/js/eslint.config.js:/app/eslint.config.js:ro" portfolio-app npx eslint src --fix
```
Never run pytest inside the running `portfolio-api-1`, which is wired to the stack's Postgres.

## Architecture & patterns
- **Imports are rooted at `python/app`**: `from core.services...`, `from api.v1...`. Never `app.core...`.
- **Backend layers:** `api/v1/<feature>/router.py` → `core/services/<x>_service.py` (class takes `db: Session` in `__init__`) → `core/database/models/*` (legacy `Column` style, `Numeric` money). Pydantic schemas live in `core/schemas/<feature>.py`. There is no repository layer yet. New code puts queries and commits in services, not routers.
- **Router mounting** is `create_app()` in `main.py`, which includes `api/v1/router.py`. Each router owns its prefix under `/api/v1` and one tag. A failed import stops startup. Watch route order: literal paths go before `/{id}`.
- **Auth:** `Depends(get_current_active_user)` from `core/auth/dependencies.py`. Every resource must be scoped by `user_id`.
- **Errors:** expected failures raise `DomainError` / `NotFoundError` from `core/errors.py` (both subclass ValueError; `OversellError` and `MissingPriceError` are DomainErrors). Their message is written for the user. Every failed response is `{error:{code,message}, request_id}` from `core/error_handlers.py` (validation errors also include `details`). `RequestContextMiddleware` sets `X-Request-ID` and logs one access line (method, path, status, duration). Logging is configured once, in `main.py`. SQLAlchemy does not echo SQL. An unhandled exception is logged and returned as `internal_error` / "Something went wrong". Routers that still catch an exception use `public_message(e, "fixed text")` for the `HTTPException` detail. The UI reads the message with `apiErrorMessage`. `tests/unit/test_error_messages.py` guards both the envelope and leaked exception text. NotFoundError → 404, other DomainError → 400.
- **FX:** an asset may be quoted in another currency than its portfolio. `core/domain/fx.py` scales `GBp`/`ILA` and converts closes and live prices with Yahoo's daily pair (`MarketDataService.get_fx_rates`, same 6h cache as history). Cash (`transaction.currency`, `total_amount`) converts only when it is not already the portfolio currency — a Trade Republic EUR amount on a USD listing is left as euros. A missing rate raises `MissingFxError` and the chart shows it. Manual create stores the listing currency for that cash unless the request (or the listing) is already the portfolio currency. `/portfolios/statistics/overview` still returns `totals[]` per portfolio currency and does not add EUR and USD portfolios together.
- **Financial math lives in `core/domain/`** (pure, no DB/network, golden-tested in `tests/unit/test_domain_engine.py` and `tests/unit/test_fx.py`): `positions.py` (split-adjusted trades in today's share units, FIFO lots with fees, `day_change`), `fx.py` (quote currency → portfolio currency), `valuation.py` (`daily_series`: value, FIFO cost basis, net invested and flows per trading day; a held asset without a price raises `MissingPriceError`, never valued at cost), `returns.py` (TWR, XIRR, risk, `period_summary`, the one `RISK_FREE_RATE`), `benchmark.py` (`shadow_series`: the portfolio's own flows invested in a benchmark). Services only load data and call these: `PortfolioCalculationService.get_portfolio_series` converts then (memoised per request) feeds the series/performance/risk endpoints; `PortfolioService._holding_rows` converts the live price and feeds holdings, summary, overview and allocation. Never add another copy of a metric. Percent units are 15.0, not 0.15. The frontend displays backend values and never computes them.
- **Market data** goes only through `core/services/market_data_service.py` (Redis-cached yfinance; `search_listings` and `get_daily_ranges` serve the ISIN resolver). Valuation uses `get_daily_history` (closes split-adjusted but *not* dividend-adjusted, plus split and dividend events, cached 6h); dividends count only via DIVIDEND transactions. Tests mock it and never hit the network.
- **Schema:** Alembic is the only schema authority; the app never calls `create_all` (tests do, on SQLite). `start_api.sh` runs `alembic upgrade head` before the API starts and aborts on failure. Baseline = `alembic/versions/e97c82868ff5_baseline.py` (rewritten in place from the old no-op, so existing dev DBs stamped at it are already correct). A model change needs a migration: autogenerate it against a throwaway Postgres (pattern in `scripts/check_migrations.sh`), review it, drop any new Postgres enum types in `downgrade()`, and keep it expand/contract: additive in release N, destructive in N+1. The gate fails on model/migration drift.
- **Frontend:** pages and components are in `js/src/components/<feature>/` (with an `index.js` barrel). All HTTP calls go through the axios objects in `js/src/services/api.js`. Auth state is in `contexts/AuthContext.jsx`. Data fetching is `useEffect`+`useState`, errors are shown with `react-hot-toast`, and formatting goes through `utils/formatters.jsx` (no inline `toFixed` or `$`). Money in portfolio views uses `useMoney()` (`hooks/useMoney.js`, provided by `CurrencyProvider` in `Portfolio.jsx`); lists that mix portfolios pass the row's own `currency`; market data uses the asset's `currency`.
- **Config:** `config.py` `settings`, fed by compose `env_file` (`python/app/.env.docker`, `js/.env.docker`). These are gitignored secrets: never print or commit them. When you add a key, also add it to the matching `.env.example`.
- **Compose:** `compose.yaml` is production (project `portfolio`, UI :3000, API loopback :8000). `app`, `api`, `worker` and `migrate` are images only (`portfolia-web:prod`, `portfolia-api:prod`, overridable with `PORTFOLIO_WEB_IMAGE` / `PORTFOLIO_API_IMAGE`; API env `../env/prod.env`). Postgres and Redis in that file are the same `build:` blocks as `docker-compose.yml`, so their config hash matches the live containers and `docker compose up` does not recreate them. Official database images wait for a planned window. `compose.dev.yaml` is the dev stack CI runs (project `portfolio-dev`, bind mounts, reload, Vite, UI :3200, API :8200). `compose.staging.yaml` overlays production with project `portfolio-staging`, UI :3100, its own volumes, and `../env/staging.env`. Bare `docker compose` in this directory selects `compose.yaml`. `docker-compose.yml` plus `docker-compose.prod.yml` is how the running containers were started. Images: `python/app/Dockerfile.prod` (non-root, no reload; migrate with `docker compose --profile migrate run --rm migrate`) and `js/Dockerfile.prod` (nginx on 8080, `/api` proxied to `api:8000`). `.github/workflows/release.yml` publishes those Dockerfiles to `ghcr.io/<owner>/portfolia-api` and `portfolia-web` (`edge` and `sha-<short>` after CI on master; `X.Y.Z`, `X.Y` and `sha-<short>` on a `v*` tag). release-please opens the release PR from Conventional Commits. `scripts/deploy.sh prod X.Y.Z` pulls that GHCR tag, dumps the database, migrates, and restarts api, app, and worker with `--no-deps`. A failed smoke check redeploys the version in `env/prod.deployed` without migrating backwards. It does not recreate Postgres or Redis. Do not run it until that version exists on GHCR. `scripts/staging-sync.sh` deploys `edge` to project `portfolio-staging` (UI :3100, its own volumes) when the GHCR digest changes, then seeds demo data if the staging database has no users. `deploy/portfolia-staging.timer` runs that every 15 minutes. It does not touch project `portfolio`. `scripts/backup.sh` writes a nightly custom-format dump of the production database to `/mnt/samsung_ufs/backups/portfolio/` (14 daily, 8 weekly). `scripts/restore.sh` loads a dump into staging; production needs `--allow-prod`. `scripts/restore-drill.sh` restores the newest production dump into staging and checks the table count. The backup and drill timers are `deploy/portfolia-backup.timer` (03:10) and `deploy/portfolia-restore-drill.timer` (1st of the month, 04:10). Neither is installed by the repo. Gatus checks the UI at `portfolio-app-1:8080` and the API health at `portfolio-api-1:8000/health/` (database and redis). The homepage tile shows container status and that UI check. There is no Sentry. HTTPS is `https://ubuntu-1.tail13e229.ts.net:3443` (`tailscale serve` to port 3000). It is not an NPM name: the only Tailscale certificate is `ubuntu-1.tail13e229.ts.net`, and that name on port 443 is Jitsi. Port 3001 is Homepage.

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
  - Dashboard: `js/src/components/dashboard/CLAUDE.md`
- When a change alters a feature's behaviour, state or gaps, update its doc in the same commit.

## Rules of engagement
- Never add, upgrade or remove a dependency (pip, npm, base image, GitHub Action) without asking first.
- After touching code, run the matching test file. **Before every commit, `scripts/verify.sh` must pass**, plus `--stack` if Docker, compose, env or startup changed. Never commit a red gate. CI runs the same script on arm64 and is a required check.
- One logical change per commit, using Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`). Work on a branch, never directly on `master`. Don't push or open PRs unless asked.
- `python/app/tests/quarantine.txt` only shrinks. Never add entries to hide a new failure. When a fix makes a quarantined test pass, delete its line (strict xfail fails otherwise).
- Don't write unnecessary comments, docstrings, tutorial-style text or boilerplate. Match the surrounding style.
- Ask before deleting Docker volumes, changing published ports or touching anything outside `portfolio/`.
- When a session establishes a new non-obvious fact about the project, update this file or the plan's progress log.

## Known state (2026-10-26)
- Product docs (`../README.md`, `../docs/USER_GUIDE.md`, `python/app/docs/`) match the app as of this date. Feature `CLAUDE.md` files stay the endpoint reference.
- Gate, last recorded: lint clean (ruff + eslint, 0 warnings); 259 tests passed, 42 quarantined xfail, plus 8 quarantined uncollectable files. Not re-run for the doc rewrite.
- Demo data (`scripts/seed_demo_application.py --reset`, run inside `portfolio-api-1` against `http://localhost:8000`) uses real Yahoo prices, splits and dividends over ~3 years; an independent replay matched the engine to the cent on every day.
- Still on old code paths: analytics `/summary` and `/users/dashboard` (snapshot metrics that count deposits as returns). Advance-risk beta uses `^GSPC` price index.
- `tests/unit/test_calculation_snapshots.py` pins every computed number (engine, risk, indicators, analytics) against `snapshots/calculations.json`. If it fails, a number the app shows changed: fix the regression, or regenerate with `UPDATE_SNAPSHOTS=1` only for an intended change and explain it in the commit.
- Tailwind 4: theme tokens live in `@theme` in `src/index.css` (there is no `tailwind.config.js`). Use slash opacity (`bg-black/50`), not the removed `bg-opacity-*`.
- ESLint stays on 9 until `eslint-plugin-react` supports 10. ruff `target-version` stays py312 on purpose (see pyproject).
- Lint policy: ruff ignores E501 (the formatter owns line length) and E712 (SQLAlchemy `== True`). ESLint has `react/prop-types` off (TS migration is planned). Use `eslint-disable-next-line react-hooks/exhaustive-deps -- <reason>` only when adding the dependency would change when the effect runs.
- FastAPI 0.143 wraps included routers in a private `_IncludedRouter`, so `app.routes` does not list endpoints. Test routing through `TestClient` (see `tests/unit/test_route_order.py`, which also overrides the auth dependencies).
- The SQLite test DB returns naive datetimes, so `calculate_portfolio_performance` (aware `now()` minus `transaction_date`) can't run against `test_db`. Test the engine through `get_performance_series` or stub it.
- Dev stack: `main.py`, `config.py`, `start_api.py` etc. are **single-file** bind mounts. A tool that replaces a file atomically (e.g. `ruff format`) leaves the container on the old inode, so the API keeps running stale code — `docker compose restart api` after editing them. Directory mounts (`core/`, `api/`) are fine.
- Technical indicators (`utils/indicators/`) are pinned to the `ta` library by `tests/unit/test_indicator_reference.py` (ta is a test-only dependency installed by `verify.sh`); deliberate differences (OBV start, PSAR two-lows cap) are documented there.
- `npm test` is a placeholder. There are no frontend unit tests or e2e tests yet.
