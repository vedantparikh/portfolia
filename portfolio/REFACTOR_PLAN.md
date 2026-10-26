# Portfolia — Production Refactor Plan

Status: **in progress**. Phases 0, 2 and 4 partly done; see the status marks and §6/§6b · Updated: 2026-10-26

Legend: ✅ done · 🟡 partly done (**Now:** says what is left) · ⏳ not started
Scope: `portfolio/` (FastAPI backend `python/app`, React frontend `js`, Docker, CI at git root)
Target host: NVIDIA Jetson AGX Xavier home server shared with ~35 other containers (see §1b)

---

## 0. Where we are (audit summary)

| Area | State | Most important issues |
|---|---|---|
| **Calculation correctness** | 🟡 Core fixed (2026-10-16) | *Fixed:* one engine in `core/domain` (FIFO with fees, automatic splits, completed-only, no cost fallback for missing prices, correct today's P&L, one risk-free rate, Yahoo FX into the portfolio currency); chart, performance, multi-period, risk, summary, holdings, overview, allocation and rebalancing all read it and agree; verified to the cent against an independent replay. *Open:* legacy analytics snapshot metrics, indicator formulas. |
| **Backend architecture** | ⚠️ Inconsistent | Every endpoint is `async def` but uses a sync SQLAlchemy session, so it blocks the event loop. There is no repository layer, and routers (analytics, assets, auth) run queries and commits directly. Domain errors and leak-free details since 1.3 (🟡). Three config systems are stacked. Alembic owns the schema (1.6 ✅). Symbol search is `GET /stock/symbols`. The dashboard router is dead and never mounted. |
| **Frontend** | 🟡 Cleaner, still hard to extend | *Done:* modernised dashboard/portfolio screens, shared `StatCard`/`Sparkline`/charts, financial maths removed from the main views, React 19/Vite 8/Tailwind 4, Sentry removed. *Open:* zero tests, `api.js` 1,731 lines, no data-fetching layer, tokens in localStorage, `dangerouslySetInnerHTML`, hard-coded `$`, 24 hand-rolled modals. |
| **Tests** | 🟡 Green gate, thin coverage | Gate: 165 passed, 42 quarantined xfail, 8 quarantined uncollectable files. Golden tests for the engine (`test_domain_engine.py`), SQLite service tests for positions/summary/series, characterisation snapshots. Still no frontend or e2e tests; integration tests mostly quarantined. |
| **Infra / CI** | ⚠️ Gated, still dev-only | *Fixed:* CI now runs `verify.sh --stack` on arm64, compose is hardened for the shared host, and secrets are out of images. Product docs rewritten 2026-10-26 (`README.md`, `docs/USER_GUIDE.md`). *Open:* there is a single dev compose (reload, bind mounts, DEBUG), the API image is large and runs as root, and there is no release or deploy process. |

> ✅ **Resolved:** the staged `docker-compose.yml` change.
> - The broken `3000:5173` port is fixed.
> - The `/media/...` bind mount was dropped on purpose: there is no production data yet.
> - Data now lives in named volumes under the Docker data-root.

---

## 1. Guiding principles

1. **One source of truth for every number.** All financial values are computed in one pure, tested Python *calculation engine*. Services, persisted snapshots and the frontend only consume its output and never recompute it.
2. **Correctness is proven by tests.** Every metric gets golden-value tests: hand-calculated scenarios covering splits, dividends, FX, mid-period deposits and partial sells. These tests are written **before** the refactor touches that metric.
3. **Same shape everywhere.** Every backend feature module has the same files, and every frontend feature folder has the same files. Adding a feature means copying a template.
4. **Strangler, not big-bang.** Each phase ships as small, reviewable PRs. The app keeps working on `master` after every PR.
5. **Production defaults, dev overrides.** The base compose file and Dockerfiles are production-grade. Dev conveniences such as reload, bind mounts and the Vite dev server live in an override.

6. **Every commit is deployable.** No commit lands on `master` unless `scripts/verify.sh --stack` passes. Locally that means before pushing; in CI it is a required check. The test-quarantine ratchet only ever shrinks.

---

## 1b. Deployment target: the Jetson server

| Fact | Value | Consequence |
|---|---|---|
| Board | Jetson AGX Xavier, 8× Carmel ARMv8.2, 512-core Volta GPU, **30 GB unified RAM** (CPU and GPU share it) | Build and run **linux/arm64** only. Any GPU memory use takes RAM from every other service. |
| OS / SDK | JetPack 5.1.6 (L4T R35.6.5, Ubuntu 20.04, CUDA 11.4). Docker 26 with the `nvidia` runtime (not the default) and Compose v5 | GPU containers must use `runtime: nvidia` and L4T-matched base images (`nvcr.io/nvidia/l4t-*:r35.x`). |
| Storage | eMMC root 28 GB (74% used). Docker data-root is `/mnt/samsung_ufs/docker_data` (234 GB) | Keep images slim, use named volumes (they land on the UFS disk), rotate logs, prune old images after deploys. |
| Neighbours | ~35 containers. GPU users: immich (server and ML), jellyfin, ollama. Shared `nginx-proxy-manager` (80/443, Tailscale TLS), `homepage`, `glances`, `portainer`, `shared-postgres`/`shared-redis` | Portfolio is a guest: memory limits, no host ports for DB/Redis, only the UI published, and it joins `homepage_proxy-network`. |
| Taken host ports | 80, 443, 2283, 3001, 3030, 3333, 5000, 5230, 7788, 8001, 8010, 8081, 8082, 8085, 8096, 8181, 8222, 8443, 8999, 9444, 11434 … | Prod UI on **3000**, prod API on loopback 8000, staging on 3100/8100. Ports can be overridden with `PORTFOLIO_UI_PORT` and `PORTFOLIO_API_PORT`. |
| Repo | `github.com/vedantparikh/portfolia` is **public** | Free native arm64 GitHub runners (`ubuntu-24.04-arm`). **Never** register a self-hosted runner on the Jetson, because a public-repo PR could run code on the home server. |

### GPU strategy: use the GPU where it actually pays off

The request was "use the NVIDIA GPU as much as possible". The recommendation is to **not** run the portfolio API, worker or DB on the GPU, and to reach the GPU through services that already own it:

- **The current workloads are tiny.** Hundreds of transactions and a few thousand price rows: every pandas/numpy calculation takes microseconds to milliseconds. The bottlenecks are Yahoo network I/O and DB round trips. Moving such small arrays to the GPU costs more in kernel-launch and copy overhead than the computation itself.
- **No GPU dataframe library fits.** RAPIDS (cuDF) does not support Jetson/JetPack 5. CuPy and PyTorch need L4T base images (2–6 GB) that are tied to the JetPack version. They cannot run on GitHub runners or a developer laptop, which breaks principle 6 (the image we test must be the image we ship).
- **The GPU is already contended.** Immich ML, jellyfin transcoding and ollama share the one GPU and the unified RAM.

**Where the GPU is used (opt-in, behind interfaces, always with a CPU fallback):**

| Use | How | When |
|---|---|---|
| **LLM features** via the existing GPU-accelerated `ollama` (`http://ollama:11434` on `homepage_proxy-network`) | An `LLMProvider` interface (ollama first). Uses: parsing statements from unknown brokers (fallback to the Trade Republic parser), categorising transactions, plain-language "explain my portfolio" summaries. Portfolio images stay CPU-only, and the model memory is shared with open-webui. | After Phase 3 (needs the clean transaction and import modules) |
| **Monte Carlo / optimisation** (retirement projections, efficient frontier, VaR simulation with ≥100k paths) | A separate optional `portfolio-gpu-worker` image (`l4t-pytorch:r35.x`, `runtime: nvidia`, `profiles: [gpu]`) behind a `ComputeBackend` interface. A NumPy implementation is the default and is what CI tests. | Only when such a feature exists **and** a benchmark shows ≥5× speed-up at realistic sizes on the Xavier |
| **OCR for scanned statements** | Reuse the host's `paperless` OCR pipeline, or Tesseract (CPU). GPU OCR is not worth an L4T image here. | With the importer work |

Every GPU path gets a CI test against the CPU fallback, plus a manual benchmark script that runs on the Jetson.

---

## 2. Target architecture

### 2.1 Backend layout (`python/app` → package `portfolia`)

```
python/
  pyproject.toml            # single source of deps (uv + uv.lock); [dev] extra
  alembic/ alembic.ini
  src/portfolia/
    main.py                 # create_app() factory: middleware, handlers, routers
    core/
      config.py             # pydantic-settings only, SecretStr, no environs/dotenv
      db.py                 # engine, SessionLocal, get_session (UoW: commit/rollback per request)
      errors.py             # DomainError → NotFound/Forbidden/Conflict/Validation/ExternalService
      error_handlers.py     # one JSON envelope: {error:{code,message,details}, request_id}
      logging.py            # structured JSON logs, configured once
      middleware.py         # request-id, access log, timing, security headers
      security.py           # PyJWT, bcrypt/argon2, hashed refresh tokens
      redis.py              # thin typed wrapper on app.state (replaces pickle RedisClient)
    domain/                 # PURE — no DB, no HTTP, no yfinance
      money.py              # Decimal helpers, rounding policy, Currency
      positions.py          # build_positions(txns): FIFO lots, fees, splits, transfers, dividends
      valuation.py          # value_series(positions, prices, fx) → value / inflow / outflow per day
      returns.py            # simple, TWR, XIRR/MWR, CAGR, period returns
      risk.py               # vol, Sharpe, Sortino, max DD, Calmar, VaR/CVaR, beta/alpha
      allocation.py         # weights, drift, rebalancing (shares, not $/100)
      indicators/           # RSI(Wilder), MACD, BB(pop std), ATR(Wilder), ADX, CCI …
    modules/                # one folder per feature, identical shape
      auth/        router.py service.py repository.py schemas.py models.py
      portfolios/  …
      transactions/ …       # + importers/ (trade_republic, portfolia) + pdf export
      assets/      …
      market_data/ provider.py (MarketDataProvider protocol) yahoo.py cache.py router.py
      fx/          provider.py service.py   # historical FX rates
      analytics/   …        # orchestrates domain/* for a portfolio; owns snapshots
      watchlists/  …
      health/      router.py   # /health/live, /health/ready (503 when unhealthy)
    api/v1.py               # explicit router aggregation; import errors fail fast
    workers/                # scheduled price/FX refresh + snapshot rebuild (arq or APScheduler)
  tests/
    unit/ (domain/*, services with fakes)  integration/ (Postgres, API)  fixtures/ (recorded prices)
```

**Rules**
- Routers are thin. They do validation, dependency injection and call a service. They never touch the DB and never contain `try/except Exception`.
- Services hold the business flow, call repositories and `domain/*`, and raise `DomainError`s.
- Repositories own all SQLAlchemy queries. They never commit; the request-scoped unit of work commits.
- Ownership is checked once, in a dependency such as `get_owned_portfolio(portfolio_id, user)`, not in 15 copy-pasted blocks.
- **Sync vs async decision (recommended):** keep sync SQLAlchemy 2.0 and make DB endpoints plain `def`, so FastAPI runs them in its threadpool. This is the smallest change that stops event-loop blocking. Use `Mapped[]` typed models and timezone-aware DateTimes everywhere. Any yfinance, SMTP or bcrypt call that remains in an `async` path is wrapped in `run_in_threadpool`.

### 2.2 Calculation engine: the canonical rules

| Topic | Rule |
|---|---|
| Money | `Decimal` in the domain layer and `Numeric(20,8)` for prices. Round only at the API boundary. |
| Units | Percentages are returned as **percent** (15.0), everywhere, with a documented API convention. |
| Cost basis | FIFO lots including fees. Realized P&L = proceeds − fees − lot cost. |
| Corporate actions | SPLIT multiplies lot quantities and divides lot prices. TRANSFER_IN/OUT create/close lots at a given cost. DIVIDEND is a cash flow using the *given amount*, net of withholding tax (tax is recorded). |
| Prices | **Unadjusted** closes for valuation (`auto_adjust=False`). Splits and dividends come from transactions, never from adjusted prices, so nothing is double counted. |
| FX | Each transaction stores its trade currency. Each asset stores its quote currency. Every valuation converts to `portfolio.currency` with the FX rate **of that date**. GBp/ILA minor units are normalised. |
| Missing price | Forward-fill. After 5 sessions the day is flagged `stale_price` and the value still uses the last close. No price at all raises. It is **never** silently valued at cost. |
| Value history | Rebuilt from transactions day by day, using each day's holdings (never current qty × historical price). The calendar is the trading days of the portfolio's exchanges, and the series excludes today's incomplete candle. |
| Returns | TWR from cash-flow-adjusted daily returns. MWR = XIRR with the opening value as a flow on period start. CAGR is derived from TWR. Period returns (1D/1W/1M/YTD/1Y/ALL) use calendar dates, not row offsets. |
| Risk | Sample std, annualised by √252 over a trading-day series. Risk-free rate comes from **one** setting. Sortino uses downside deviation versus the MAR. Beta/alpha use returns aligned on common dates and return `None` (not 0) when undefined. |
| Today's P&L | qty_at_prev_close × (P_now − P_prev_close) + Σ trades today × (P_now − trade_price). |
| Benchmark | A shadow portfolio that buys and sells the benchmark with the *same* external flows, priced with a total-return index (e.g. `^SP500TR`). It reuses the same TWR/XIRR functions. |
| NaN/Inf | These never reach the DB or JSON. Undefined metrics are `null`, with a reason. |
| Derived state | `PortfolioAsset.quantity/cost_basis` are a cache rebuilt from transactions. The API does not accept client-written quantity or P&L. |

---

## 3. Phased roadmap

Each step is roughly one PR. The order matters: **safety net → release platform → foundation → correctness → consolidation → frontend → hardening**.

### Phase 0: Stabilise and create a safety net (≈1 week)
| # | Work | Done when |
|---|---|---|
| ✅ 0.1 | ✅ Compose for the shared host: UI port fixed, API on loopback only, DB/Redis not published, named volumes, memory limits, log rotation (`fe0e6c3`) | Stack healthy, UI :3000 → 200 |
| 🟡 0.2 | ✅ `.env.example` templates and `.dockerignore` files, so secrets are no longer baked into images (`f5579c3`). ⏳ **Still to do:** rotate the Brevo SMTP password (Sentry was removed on 2026-10-15), check history commits `508abfd`/`51bdb8d`, and add gitleaks to CI. | gitleaks clean, secrets rotated |
| 🟡 0.3 | ✅ Repo hygiene: 59 dead or stray files removed (`a1b50e4`). ✅ Root README, `STARTUP_GUIDE.md`, and the guides under `python/app/docs/` rewritten 2026-10-26. ⏳ `setup-docker.sh` is still only a host check. | README accurate |
| ⏳ 0.4 | One import root and one dependency file. Use a single `pyproject.toml` with uv and a lock file. Split dev and prod deps. Add `ta` for tests. Drop `schedule`, `requests`, `scipy` and `PyPDF2`. Set `requires-python >= 3.12`. Delete the empty `python/app/app/` dir, which shadows the `app` package. **Now:** Still `requirements.txt` + `pyproject.toml`, empty `python/app/app/`, `ta` installed ad hoc by the gate. | `pytest --collect-only` collects with **0 errors** |
| 🟡 0.5 | **Burn down `tests/quarantine.txt`** (50 entries: 8 uncollectable files, 42 xfail). Fix the `/app/v1` → `/api/v1` prefix and delete tests for removed APIs. Then turn on blocking lint: ruff on changed files via pre-commit, and eslint once `react/prop-types` is solved by TS or disabled. **Now:** Lint is gating (ruff + eslint, 0 warnings, 2026-10-15). Quarantine unchanged: 50 entries. | Quarantine file empty, lint is a required check |
| 🟡 0.6 | ✅ CI gate: `scripts/verify.sh --stack` on `ubuntu-24.04-arm` for every PR and every push to master (`e30df0f`). ⏳ Turn on GitHub branch protection: require the `verify` check, squash-merge only, no direct pushes to `master`. **Now:** CI runs `verify.sh --stack` on arm64; branch protection not confirmed. | A red check blocks merge |
| ✅ 0.7 | ✅ **Characterisation tests**: `tests/unit/test_calculation_snapshots.py` pins positions, value history, TWR/CAGR/XIRR, risk metrics, all indicators and the analytics/advanced-risk helpers on deterministic inputs (added in deps wave 3). | Every number change fails the gate and must be explained |

### Phase R: Release platform (≈1.5 weeks, right after Phase 0, *before* the big refactors)
There is no production data yet, so this is the cheapest moment to set up how releases work. Every later phase then ships through it. See §7 for the full release strategy.

| # | Work | Done when |
|---|---|---|
| 🟡 R.1 | **Production images.** API: multi-stage `python:3.12-slim`, prod deps only, non-root, `uvicorn` workers with no reload, `alembic upgrade head` as a separate one-off `migrate` service. UI: `npm ci && vite build`, then `nginx:alpine` (non-root) serving `dist` with SPA fallback and `/api` proxied to the API. Postgres and Redis use the official images directly (drop the thin Dockerfiles). **Now:** `Dockerfile.prod` for the API (`python:3.14.9-slim`, uid 1000, `uvicorn` workers, no reload; `alembic upgrade head` is `docker run <image> alembic upgrade head`) and the web (`nginx:1.28.0-alpine`, uid nginx, port 8080, SPA fallback, `/api` → `api:8000`). No bind mounts. Measured 2026-10-26: API 807 MB, web 49 MB. The 400 MB API cap is not reachable with polars + pyarrow + pandas (~450 MB of wheels). The dev compose and the thin Postgres/Redis Dockerfiles stay until R.2, so the live database container is not recreated. | Both images start without bind mounts. API size is the numeric stack, not 400 MB |
| 🟡 R.2 | **Compose split.** `compose.yaml` holds the prod base, using images only (`image: ghcr.io/vedantparikh/portfolia-{api,web}:${PORTFOLIO_VERSION}`). `compose.dev.yaml` holds the build, bind mounts, reload and the Vite dev server. `compose.staging.yaml` holds the staging ports and volumes. Prod and staging have separate env files under `/home/bubbly/server/appdata/portfolia/env/` (outside the repo, `chmod 600`). **Now:** the three files exist. `compose.yaml` defaults to the local tags `portfolia-api:prod` and `portfolia-web:prod` (`PORTFOLIO_API_IMAGE` / `PORTFOLIO_WEB_IMAGE` override them; GHCR is R.3). Dev is project `portfolio-dev` on :3200/:8200. Staging is project `portfolio-staging` on :3100/:8100 with its own volumes and `env/staging.env`. Secrets are `env/prod.env` and `env/staging.env` (mode 600, gitignored). Postgres and Redis keep the `docker-compose.yml` `build:` blocks: dropping them changes the config hash and would recreate the live database containers. App, API, worker and migrate have no `build:` and no bind mounts. The live containers were not recreated. | `docker compose -f compose.yaml config` has no `build:` and no bind mounts on app, api, worker and migrate; postgres and redis hashes match the live containers |
| 🟡 R.3 | **Release workflow** (`.github/workflows/release.yml`). On a `v*` tag, build `linux/arm64` images natively on `ubuntu-24.04-arm`, push to GHCR tagged `X.Y.Z`, `X.Y` and `sha-<short>`, and attach SBOM and provenance. On every master push, publish an `edge` tag. Use release-please (Conventional Commits, which the repo already uses) to open the release PR and maintain `CHANGELOG.md`. **Now:** the workflow, `release-please-config.json` and `.release-please-manifest.json` (starting at `0.0.0`) are in the repo. `edge` and `sha-<short>` publish only after the `CI` workflow succeeds on `master`. A `vX.Y.Z` tag publishes `X.Y.Z`, `X.Y` and `sha-<short>` for `ghcr.io/vedantparikh/portfolia-api` and `portfolia-web`, with SBOM and max provenance. release-please opens the release PR; merging it creates the tag. The first successful push creates private GHCR packages: set both to Public once so the Jetson can pull them. The live stack still runs the local `portfolia-*:prod` tags until R.4. | Tagging `v0.1.0` publishes pullable images |
| 🟡 R.4 | **`scripts/deploy.sh <env> <version>`** on the Jetson: pull, then `pg_dump` backup, then `docker compose run --rm migrate`, then `up -d --wait`, then the smoke checks from `verify.sh`. On any failure it automatically redeploys the previous version, which is recorded in `env/<env>.deployed`. It prunes images older than the last 3 releases. **Now:** `scripts/deploy.sh` and `scripts/test-deploy.sh`. Prod restarts only api, app, and worker (`--no-deps`) and refuses to create Postgres or Redis. Rollback swaps the image back and does not run migrations. The test deploys a broken `0.2.0`, smoke fails, and the recorded `0.1.0` is restored. Not run against the live stack. | A deliberately broken release rolls itself back |
| 🟡 R.5 | **Staging environment** on the same Jetson: project `portfolio-staging`, UI :3100, its own volumes and seeded demo data. It auto-deploys `edge` through a systemd timer that runs `deploy.sh staging edge` every 15 minutes when the digest changes. **Now:** `scripts/staging-sync.sh` compares the GHCR `edge` digests with `env/staging.digest` and deploys only on change, then seeds demo data when staging has no users. The first staging boot creates its own Postgres and skips the dump. Units are `deploy/portfolia-staging.service` and `.timer` (every 15 minutes). They are not installed, and staging is not started, so the live project is untouched. | A merge to master shows up on staging within 15 minutes |
| 🟡 R.6 | **Backups and restore.** Run a nightly `pg_dump` to `/mnt/samsung_ufs/backups/portfolio/`, keeping 14 daily and 8 weekly copies, with an optional copy to Nextcloud. Add a `restore.sh`, and run a monthly restore drill into staging. **Now:** `scripts/backup.sh` writes `daily/<env>-YYYYMMDD.dump` (14) and `weekly/<env>-YYYY-Www.dump` (8). Deploy dumps in the directory root are not pruned. `scripts/restore.sh` restores into staging and refuses prod unless `--allow-prod` is passed. `scripts/restore-drill.sh` restores the newest prod daily dump into staging and checks the public table count. Units are `deploy/portfolia-backup.timer` (03:10) and `deploy/portfolia-restore-drill.timer` (monthly). They are not installed. The drill is proven with a fake database, not against the live stack. Nextcloud runs only when `env/backup.env` is present. | A restore drill passes |
| ✅ R.7 | **Exposure and monitoring.** Add an nginx-proxy-manager host `portfolio.<tailnet>.ts.net` with TLS, upstream `portfolio-web:8080` on `homepage_proxy-network`. Add a homepage tile and status widget and an uptime check (Sentry was removed on request; errors go to structured logs). **Now:** `https://ubuntu-1.tail13e229.ts.net:3443` returns 200. NPM cannot serve `portfolio.tail13e229.ts.net`: its certificate is only `ubuntu-1.tail13e229.ts.net`, already used for Jitsi, and a Tailscale Service name needs a tagged node. Port 3001 is Homepage, so tailscale serve uses 3443 and proxies to `127.0.0.1:3000`. The UI container is `portfolio-app-1`. Gatus checks that UI and `portfolio-api-1:8000/health/` (database and redis). Containers cannot open the tailnet port, so they do not check :3443. The homepage tile links to the HTTPS URL and shows container status plus a site monitor. No Sentry. | HTTPS URL works, and an outage shows up on homepage |

### Phase 1: Backend foundation (≈1.5 weeks)
| # | Work |
|---|---|
| ✅ 1.1 | Rewrite `config.py` as pure pydantic-settings. Collapse the duplicate keys (`SECRET_KEY`/`JWT_SECRET_KEY`, `ALGORITHM`/`JWT_ALGORITHM`). Fix `REFRESH_TOKEN_EXPIRE_DAYS`. Make Redis read its settings from config. **Done:** `JWT_SECRET_KEY` is the signing key and `SECRET_KEY` is only the fallback, so existing tokens still verify. `REFRESH_TOKEN_EXPIRE_DAYS` (default 7) is the refresh lifetime unless minutes are set. Redis host, db, password and TTL come from `settings`. |
| ✅ 1.2 | Add an `app` factory with explicit router aggregation, deleting the ~230 lines of `try/import` blocks. Standardise prefixes and tags. Fix the `/assets/search` shadowing and the duplicate operationIds. **Done:** `create_app()` includes `api/v1/router.py`. Each router owns its prefix and one tag. Operation ids are `method` + path, so shared handler names cannot collide. Paths are unchanged and pinned by `tests/unit/api_routes.txt`. `/assets/search/{query}` removed (#73); shadowed routes stay pinned by `test_route_order.py`. |
| ✅ 1.3 | Add `DomainError` classes, global handlers and the uniform error envelope. Remove the `detail=str(e)` leaks and the blanket `except Exception`. **Done:** `core/error_handlers.py` returns `{error:{code,message}}` for domain errors, HTTP errors, validation errors, and unhandled exceptions. API routers no longer catch `Exception` only to return a generic 500; the ones that still catch an exception do real work (a per-item failure, a skipped email, a rollback). The UI reads the message with `apiErrorMessage`. |
| ✅ 1.4 | Add middleware for request-id, structured access logging and timing. Configure logging once and remove the `print()` calls. **Done:** `RequestContextMiddleware` puts `X-Request-ID` on every response and logs one `access` line with method, path, status, and duration. The same id is on the error body. Logging is configured only from `main.py`. Application `print()` calls are gone (the one-off quantity script still prints to the terminal). SQLAlchemy `echo` is off, so SQL no longer floods the API log. |
| ✅ 1.5 | Add a unit-of-work session dependency and a `get_owned_portfolio` dependency. Make DB endpoints `def`. **Done:** `get_db` commits when the request succeeds and rolls back when it raises. `get_owned_portfolio` is the active-portfolio ownership check (the analytics and transaction-summary copies now call it). API routes are plain `def` unless they await I/O, and the auth dependencies are sync too. |
| ✅ 1.6 | **Alembic as the only schema authority.** Autogenerate a baseline migration from the models. There is no production data yet, so it simply runs on empty DBs in every env, with no `stamp`. Do this **before** the first prod release (R.4) so prod is born on Alembic. Remove every `create_all` and the auto-seeding on startup. A CI check fails on model/migration drift. **Done:** baseline in `e97c82868ff5_baseline.py`, no `create_all` at startup, `scripts/check_migrations.sh` (upgrade, `alembic check`, full downgrade, upgrade) in `verify.sh`. |
| ✅ 1.7 | Models: move to SQLAlchemy 2 `Mapped[]`, make all DateTimes timezone-aware (in a migration), and widen price precision. **Done:** every model column is `mapped_column`. The live database already stores datetimes as `timestamp with time zone` (43 columns), so the migration does not change them. Prices and cash amounts are `Numeric(20, 8)` in `b8c1d4e27a90`; percent and ratio columns are unchanged. |
| ✅ 1.8 | Health endpoints: `/health/live` and `/health/ready` with real checks, returning 503 when unhealthy. Delete `health_router` (the test router) and the hardcoded timestamp. **Done:** `/health/live` only checks that the process is serving. `/health/ready` checks Postgres and Redis and returns 503 when either is down, with a real UTC timestamp. `/health/` is the same check, so Compose and Gatus keep their current URL. The test router (`GET /api/v1/health`) is gone. |
| ✅ 1.9 | Auth hardening: python-jose → PyJWT, passlib → bcrypt (or argon2) directly, hash refresh tokens at rest, dummy hash on unknown users, remove the no-op `require_admin`. Optional: refresh token in an httpOnly cookie (see Phase 4.6). **Done:** tokens are signed with PyJWT 2.15.1. `user_sessions.refresh_token` stores the SHA-256 hex of the token (`c3a7e9b14d20` hashes rows that still hold the token). Login runs bcrypt against a fixed hash when the username is missing. `require_admin` is gone. The httpOnly cookie stays in 4.6. passlib → bcrypt was already done. |

### Phase 2: Calculation engine and correctness (≈2–3 weeks, the core of the work)
Golden tests are written first for every item.

| # | Work | Fixes |
|---|---|---|
| 🟡 2.1 | `domain/positions.py`: FIFO with fees, SPLIT, TRANSFER_IN/OUT and DIVIDEND (with a given amount and tax). Add schema validation: qty > 0 and price ≥ 0 per type. **Now:** `core/domain/positions.py`: completed-only, FIFO with fees, splits applied automatically from market data (trades in today's share units). TRANSFER_IN/OUT and per-type validation open. | C1, C2, M2, M3 |
| ✅ 2.2 | Importer fix: the Trade Republic dividend amount and withholding tax are kept, and the currency is set. Run a data migration that recomputes affected rows. **Done:** dividends keep their cash amount, EUR currency and taxes stored, €1 trade fee split out (€0 savings plans), cash rows skipped with a reason. A real quarterly statement parses: split dates, page-break rows and dotted savings-plan quantities. No data migration (nothing imported from the old parser). Withholding tax is a separate statement row and stays skipped. | C2 |
| ✅ 2.3 | `core/domain/fx.py` + `MarketDataService.get_fx_rates`. `assets.currency` is the quote currency (no second column). `GBp`/`GBX` and `ILA` scale to GBP/ILS. Yahoo `{QUOTE}{PORTFOLIO}=X` daily closes (inverse if needed), same 6h Redis cache as history. Closes and live prices convert every day; cash converts only when `transaction.currency` differs. Missing rate raises. Dashboard totals stay per portfolio currency. | C3 |
| ✅ 2.4 | `MarketDataProvider` with one Yahoo implementation. **Done:** every Yahoo call goes through `YahooMarketDataProvider` (4 at a time, exponential backoff). Batch cache writes use one Redis pipeline. Symbol search is only `GET /stock/symbols` (the exact-ticker `/market-data/search` is gone). Valuation history is unchanged: split-adjusted closes (`auto_adjust=False`), plus splits and dividends, cached 6h. Requests still call Yahoo on a cache miss (3.3). | C1, H5, perf |
| ✅ 2.5 | `domain/valuation.py`: daily holdings × price × FX on a trading calendar, with explicit stale/missing flags. **Done:** `daily_series` forward-fills. A close older than 5 sessions sets `stale_price` and `stale_symbols` on that day and on the chart points; the value still uses the last close. No price at all raises `MissingPriceError` (never valued at cost). FX is applied by the caller before this. | H4, H6, M5 |
| ✅ 2.6 | `domain/returns.py` and `domain/risk.py`: TWR, XIRR (with opening value), CAGR, calendar-date period returns, and risk metrics with a single risk-free rate and percent units. **Now:** `core/domain/returns.py`: TWR, XIRR (period + annual), CAGR, calendar periods, `period_summary`, one `RISK_FREE_RATE`; chart, /performance, /multi-period and risk agree exactly. | H1, H3, M6, M10 |
| ✅ 2.7 | Benchmark shadow portfolio built on the same functions, with a total-return index. **Done:** `core/domain/benchmark.py` `shadow_series` + `GET /portfolios/calculations/portfolio/{id}/benchmark`, Performance Chart "Compare with"; old benchmark endpoints and ~560 lines of legacy helpers removed. A foreign-currency benchmark is converted with 2.3 before the shadow is built. | C4, H2 |
| ✅ 2.8 | Today's P&L formula and a correct previous close. **Done:** `day_change` is used by holdings, summary and overview. The previous close is the last session that started before the current one, using the bar's timezone, not the older of two downloaded rows. Cached 12 hours under the UTC date. | H5 |
| ✅ 2.9 | Allocation and rebalancing in shares. Fix the indicator formulas (Wilder RSI/ATR/ADX, population-std Bollinger, CCI, StochRSI). **Done (2026-10-16):** all 17 indicators match `ta` (reference test), real PSAR, configuration UI wired. **Now:** Allocation from live holdings, rebalancing in shares with the stored threshold. Indicator formulas open (PSAR stub, non-Wilder RSI/ATR/ADX, sample-std Bollinger). | M8, Low |
| ✅ 2.10 | `PortfolioAsset` is a cache rebuilt from transactions on every write and on refresh. **Done:** `PUT /portfolios/{id}/assets/{asset_id}` is gone, so a client cannot write quantity, cost, or P&L. Adding a holding (`POST /assets` and the legacy post) creates a buy. Deleting a holding deletes its transactions. | M1 |
| 🟡 2.11 | Re-run the Phase 0.7 characterisation snapshots and review **each** changed number against a hand calculation or a broker statement. **Now:** Characterisation snapshots unchanged through the refactor; demo data replayed independently to the cent. Broker-statement check open. | — |

### Phase 3: Consolidate backend modules (≈1.5 weeks)
| # | Work |
|---|---|
| 🟡 3.1 | Merge `portfolio_service`, `portfolio_calculation_service`, `portfolio_analytics_service`, `portfolio_risk_metrics_service`, `portfolio_advance_risk_metrics` and `portfolio_dashboard_service` into `modules/portfolios` (CRUD and holdings) plus `modules/analytics` (which orchestrates the domain functions and owns snapshots). Remove the dead dashboard router and service, or mount them properly. **Now:** Maths extracted to `core/domain`; service merge not started. |
| ⏳ 3.2 | Move all DB access out of the analytics, assets and auth routers into repositories. |
| 🟡 3.3 | Snapshots are persisted by a **background worker** (daily close, plus on transaction change), not inside request handlers. The same worker refreshes prices and FX. **Now:** `workers/run.py` refreshes watchlist prices and evaluates alerts; snapshots, holdings prices and FX not yet. **Now:** Legacy snapshot writes (`create_performance_snapshot`) still happen in requests (analytics `/summary`). |
| ⏳ 3.4 | Replace the pickle `RedisClient` with a typed wrapper. Delete `SingletonMeta`, `watchlist_alert_service` (or finish it), the FHIR leftovers and `fix_asset_quantities_and_pnl.py` (which becomes a management command: `portfolia recalc`). |
| ⏳ 3.5 | Move the PDF export and transaction export to portfolio currency and formatted money. Stop summing volume across currencies. **Now:** PDF export hard-codes `$`. |
| ⏳ 3.6 | Enforce mypy (strict on `domain/` and `core/`, gradually elsewhere). Add an OpenAPI snapshot test so contract changes are deliberate. |

### Phase 4: Frontend (≈3 weeks, can start in parallel with Phase 2)
| # | Work |
|---|---|
| 🟡 4.1 | Tooling: Vitest, React Testing Library, MSW and Playwright. Move ESLint 9 to flat config with jsx-a11y, `no-console` and `max-lines`. Add Prettier, husky with lint-staged, and `knip`. Remove unused deps and declare `prop-types`, or move to TS. **Now:** ESLint 9 flat config done; no Vitest/Playwright yet. |
| ⏳ 4.2 | **TypeScript, gradually** (`allowJs`, strict for new files). API types are generated from FastAPI's `openapi.json` (`openapi-typescript`), and CI fails on drift. |
| 🟡 4.3 | Split `api.js` into `shared/api/client.ts` (axios, single-flight refresh, `ApiError`) plus a per-feature `api.ts`. Remove the duplicate endpoints and the `portfolios[0]` bug. **Now:** Dead client functions removed (#72, #73, fix/calculations); `api.js` still 1,731 lines. |
| ⏳ 4.4 | Adopt **TanStack Query**: one hook per resource, invalidation on mutation, cache cleared on logout. Replace `assetCache` and `useAssetPreloader`. |
| 🟡 4.5 | Build the `shared/ui` primitives (Button, Modal with focus trap and Esc, FormModal with react-hook-form and zod, Table, Card, Spinner, EmptyState, ErrorState). Collapse the 24 modals, the 4 search components (1 remains) and the 2 charts (1 remains). **Now:** `StatCard`, `Sparkline`, single `LoadingSpinner`, `PerformanceSeriesChart`, `AllocationDonut` added (#73, fix/calculations). |
| ⏳ 4.6 | Security: remove `dangerouslySetInnerHTML` and the `innerHTML` tooltips. Keep a single `tokenStore`. Ideally put the refresh token in an httpOnly cookie, with the access token held in memory. **Now:** `dangerouslySetInnerHTML` for risk reasoning remains; tokens in localStorage. |
| 🟡 4.7 | **Delete all frontend financial math.** Display backend values only. One `formatMoney(value, currency, locale)`, with lint rules banning raw `toFixed` and `$`. **Now:** Done for performance chart, holdings price/weight, realized total, totals and allocation. Left: transaction-form helpers, `Chart.jsx` tooltip, hard-coded `$`. |
| ⏳ 4.8 | Routing: `ProtectedLayout` (Sidebar and `<Outlet/>`), `React.lazy` per route, an error boundary, and a 404 page. |
| ⏳ 4.9 | Feature-folder layout (see §2.3). Migrate feature by feature: auth → portfolios → transactions → assets → watchlists → analytics → dashboard. |

### 2.3 Frontend layout
```
js/src/
  app/        main.tsx App.tsx router.tsx providers.tsx ErrorBoundary.tsx
  shared/     api/(client, errors, generated/) ui/ lib/format/ hooks/ charts/PriceChart.tsx
  features/<name>/  api.ts queries.ts components/ pages/ __tests__/
  test/       setup.ts msw/handlers/ fixtures/ renderWithProviders.tsx
js/e2e/       Playwright specs
```

### Phase 5: Test pyramid and e2e (runs alongside every phase, finalised here)
| Layer | Tool | Scope | Target |
|---|---|---|---|
| Domain unit | pytest + hypothesis | `domain/*`, with golden scenarios and property tests (e.g. TWR is invariant to deposits, quantity is never < 0) | ≥ 95% line coverage, 100% of metrics |
| Service unit | pytest + fakes | Services with fake repo and provider, `fakeredis`, network blocked (`pytest-socket`) | ≥ 85% |
| Integration | pytest + testcontainers Postgres 16 | Repositories, migrations up/down, API through httpx with a real DB and per-test transaction rollback | All endpoints happy path plus auth/ownership |
| Contract | OpenAPI snapshot + schemathesis (nightly) | No unintended API changes, no 500s on fuzzed input | — |
| Frontend unit | Vitest + RTL + MSW | Formatters, API client refresh logic, forms, key components | ≥ 70% on `shared/` and `features/*/` |
| E2E | Playwright against the prod compose profile + deterministic seed (recorded prices, no live Yahoo) | Register/login → create portfolio → add buy/sell/dividend/split → dashboard numbers equal the golden values → import Trade Republic PDF → watchlist | Runs on PRs (smoke) and nightly (full) |

**Golden scenario fixture set** (shared by domain tests, integration tests and e2e):
1. Single buy, flat price
2. Buy and partial sell with fees (FIFO)
3. 2:1 split mid-period
4. Dividend with withholding tax
5. Mid-period deposit in a flat market (TWR = 0%)
6. EUR portfolio holding a USD asset with an FX move
7. Missing price days and holidays
8. Trade executed today (today's P&L)
9. Benchmark comparison with identical flows

### Phase 6: Production hardening (≈1 week; the deployment basics moved to Phase R)
| # | Work |
|---|---|
| 🟡 6.1 | Add a worker service (prices, FX, snapshots) to the release images and compose files, with its own memory limit. **Now:** `worker` service in the dev compose (384 MB, heartbeat healthcheck); prod images/compose still to come with R.1/R.2. |
| ⏳ 6.2 | Redis requires a password. Add a Trivy scan to the release workflow, which fails on critical CVEs. Run Playwright e2e against the release images in staging before promotion. |
| ⏳ 6.3 | Optional GPU profile (§1b): `portfolio-gpu-worker` and the ollama `LLMProvider`, only once a feature needs them. |
| 🟡 6.4 | Docs: one root README (quick start, architecture diagram, dev/staging/prod commands, runbooks for deploy, rollback and restore), `docs/adr/` (sync DB, calc engine conventions, FX source, GPU strategy, release strategy), and `CONTRIBUTING.md` ("how to add a feature module"). **Now:** Root README and `docs/USER_GUIDE.md` rewritten 2026-10-26 (screenshots, demo user, workflows). Per-feature `CLAUDE.md` docs remain the endpoint reference. Open: `docs/adr/`, `CONTRIBUTING.md`, deploy/rollback runbooks (they wait on Phase R). |

---

## 4. Decisions

Answered:
- **Existing data:** none yet. No data migration or recompute report is needed, and the Phase 1.6 Alembic baseline can be created fresh with no `stamp`.
- **Compose intent:** drop the `/media` bind mount and keep DB/Redis private. Done in 0.1.
- **GPU:** use it via shared GPU services (ollama) and an optional GPU worker profile only where benchmarks justify it (§1b).

- **Multi-currency:** yes. Source is Yahoo `{QUOTE}{PORTFOLIO}=X` daily closes (free), inverted when only the reverse pair exists. ECB rates were not used.

Open:
1. **Sync vs async DB:** I recommend sync SQLAlchemy with `def` endpoints, which is simpler and fits the Jetson. The alternative is a full AsyncSession/asyncpg migration.
2. **TypeScript migration on the frontend:** gradual (recommended) or not at all.
3. **Refresh token in an httpOnly cookie:** this changes the auth flow between frontend and backend. Recommended, but it is optional.
4. **Public hostname:** Tailscale-only (`*.ts.net`, recommended) or exposed to the internet?
5. **Staging auto-deploy:** a systemd timer pulling `edge` (recommended), or manual `deploy.sh staging edge` only?

## 5. Risks

| Risk | Mitigation |
|---|---|
| Numbers change for users after Phase 2 | Characterisation snapshots (0.7), a per-number review (2.11) and a changelog entry |
| Prod gets data before Alembic owns the schema | Land 1.6 before the first `deploy.sh prod`, and make `alembic check` (model drift) a CI gate |
| Yahoo rate limits or outages | Provider, cache and backoff are in place (2.4). A background worker so a request never calls Yahoo is still 3.3 |
| A long-running refactor drifts from master | Small PRs, the strangler approach, and CI gates from week 1 |
| Portfolio starves the other services on the shared Jetson (immich, jellyfin, ollama) | Memory limits per service, log rotation, no GPU by default, image pruning in `deploy.sh` |
| A bad release breaks prod | Staging soak, `deploy.sh` with automatic rollback, a `pg_dump` before every migration, and expand/contract migrations so the previous version can still run |
| arm64-only issues (wheels, native deps) | CI builds and tests natively on `ubuntu-24.04-arm` with the same images that are deployed |

**Rough total:** 9–11 weeks for one developer, with Phase R added. Phases 2 and 4 can overlap.

---

## 6. Progress log

| Date | Branch | Commit | What |
|---|---|---|---|
| 2026-10-14 | `chore/repo-cleanup` | `a1b50e4` | Removed 59 dead/stray files (no behaviour change) |
| 2026-10-14 | `chore/release-foundation` | `fe0e6c3` | Compose for the shared Jetson host |
| 2026-10-14 | `chore/release-foundation` | `f5579c3` | Env templates and `.dockerignore` |
| 2026-10-14 | `chore/release-foundation` | `e30df0f` | `verify.sh` gate, test quarantine ratchet, arm64 CI |
| 2026-10-15 | `fix/app-build-run` (#67) | — | 8 runtime bugs found by seeding demo data (500s, watchlist bulk add, crashes); full ruff + eslint cleanup, lint is gating |
| 2026-10-15 | `feat/ui-polish` (#68) | — | Transaction colours, sidebar fit, compact transaction rows, mobile header, footer year |
| 2026-10-15 | `chore/deps-wave1` (#69) | — | Node 22, unused deps removed, FastAPI 0.143 / Starlette 1.8 / SQLAlchemy 2.1 / pydantic 2.14, test tooling |
| 2026-10-15 | `chore/deps-wave2` (#70) | — | React 19, React Router 7, Vite 8, ESLint 9 flat config |
| 2026-10-15 | `chore/deps-wave3` | — | Calculation snapshots (0.7 ✅), Sentry removed, lucide 1, charts 5, Router 8, Tailwind 4, passlib → bcrypt, Python 3.14, numpy 2, pandas 3, polars 2, yfinance 1.7 |
| 2026-10-16 | `chore/ui-modernize` (#73) | — | Dashboard and portfolio widgets, StatCard, analytics units fixed |
| 2026-10-16 | `fix/calculations` | — | `core/domain` engine (2.1 splits/FIFO, 2.5 valuation, 2.6 returns, 2.8 today's P&L ✅); performance series endpoint + chart; summary/holdings/overview/allocation/rebalancing/history on the engine; realistic demo seed. Open: 2.2 importer dividends/tax, 2.3 FX, 2.7 benchmark, 2.10 derived cache |
| 2026-10-16 | `fix/shadowed-routes-500s` | — | Six shadowed literal routes reachable (and the 4 bugs behind them fixed); `/overview` and `/users/dashboard` 500s fixed; asset search scoped to the user; `test_route_order.py` |
| 2026-10-16 | `chore/alembic-baseline` | — | 1.6: Alembic baseline from the models, `create_all` and the startup re-init removed, migration drift/round-trip check in the gate |
| 2026-10-16 | `fix/tr-import` | — | 2.2: Trade Republic import keeps dividends, EUR, fees and taxes; cash rows skipped with a reason; date and confidence crashes fixed; import toasts/refresh fixed |
| 2026-10-16 | `feat/pytr-csv-import` | — | pytr CSV provider (full TR history), ISIN → Yahoo listing resolver scored on the user's own fills, assets created on import with their ISIN; UI to follow |
| 2026-10-16 | `feat/benchmark-shadow` | — | 2.7: shadow-portfolio benchmark (TWR = index return exactly, MWR/profit with the portfolio's own flows), `/benchmark` + `/benchmarks` endpoints, Performance Chart comparison; legacy benchmark maths deleted |
| 2026-10-16 | `fix/error-leaks` | — | 1.3: `DomainError`/`NotFoundError`/`public_message`; 38 exception texts removed from HTTP details plus 6 from response bodies and parser warnings; 404 vs 400 split on performance endpoints; static guard test |
| 2026-10-16 | `feat/single-currency-portfolios` | — | Currency guard on manual/bulk/pytr transaction writes, global DomainError handler, per-currency overview totals, money formatted in the portfolio/row/asset currency (`useMoney`), import review flags wrong-currency listings |
| 2026-10-16 | `feat/watchlist-alerts` | — | Alerts work: thresholds now save, pure `check_alerts`, notify-once-per-crossing events, `worker` service (prices + alerts every 15 min), `/watchlists/alerts` + acknowledge, in-app alerts panel/bell/dashboard link; migration `acknowledged_at` |
| 2026-10-16 | `feat/indicators` | — | 2.9: RSI/StochRSI/MACD/ADX/Aroon/CCI/BB/ATR/Keltner/VPT/VWAP fixed and PSAR implemented, all pinned to `ta`; data now calculated oldest-first with ~400 days warm-up; second indicator class no longer dropped; saved configurations drive the chart (manager modal, configuration_id, list); one pane per oscillator; private configurations no longer readable by others |
| 2026-10-20 | `feat/import-dedup` | — | Re-importing a statement is safe: each parsed row gets a `source_key` (stored on `transactions`, unique per portfolio, migration `a3f1c9d2e7b4`); bulk-create skips known rows (`total_skipped`) and keys older keyless imports it matches by date/type/ISIN/qty/amount; `/transactions/imported` lets the review table mark and leave out rows already in the chosen portfolio |
| 2026-10-26 | `docs/product-guide` | — | Root README, user guide with screenshots of the `demo` account, and the stale guides under `python/app/docs/` rewritten to the current stack. `setup-docker.sh` left as a host check |
| 2026-10-26 | `feat/fx-yahoo-rates` | — | 2.3: Yahoo daily FX into the portfolio currency (`core/domain/fx.py`). Closes and live prices convert; cash converts only when the transaction currency differs. `GBp`/`ILA` scaled. Foreign listings and imports are accepted. Per-portfolio dashboard totals unchanged |
| 2026-10-26 | `feat/prod-images` | — | R.1 started: production API and web images (`Dockerfile.prod`). API 807 MB (polars/pyarrow/pandas), web 49 MB. Live dev compose unchanged |
| 2026-10-26 | `feat/compose-split` | — | R.2: `compose.yaml` (images only), `compose.dev.yaml` (project `portfolio-dev`), `compose.staging.yaml`. Env files in `env/` (gitignored, mode 600). Live Postgres/Redis not recreated |
| 2026-10-26 | `feat/release-workflow` | — | R.3: release-please plus arm64 GHCR images (`edge` after CI, `X.Y.Z`/`X.Y`/`sha-<short>` on a `v*` tag, SBOM and provenance). Live stack unchanged |
| 2026-10-26 | `feat/deploy-script` | — | R.4: `deploy.sh` pulls a GHCR tag, dumps Postgres, migrates, and restarts api/app/worker. A failed smoke check redeploys `env/<env>.deployed`. Live stack not deployed |
| 2026-10-26 | `feat/staging-sync` | — | R.5: staging follows the GHCR `edge` digest on its own project and ports. Timer units are in the repo and not installed |
| 2026-10-26 | `feat/backups` | — | R.6: nightly `pg_dump` with 14 daily and 8 weekly copies, `restore.sh`, and a monthly staging drill. Timers are not installed. Live database not dumped |
| 2026-10-26 | `feat/exposure` | — | R.7: tailnet HTTPS on :3443, Gatus checks for the UI, API health, and certificate, homepage tile links to the HTTPS URL |
| 2026-10-26 | `feat/settings` | — | 1.1: pydantic-settings, one signing key (`JWT_SECRET_KEY` wins), refresh tokens follow `REFRESH_TOKEN_EXPIRE_DAYS`, Redis reads config. Live containers not restarted |
| 2026-10-26 | `feat/app-factory` | — | 1.2: `create_app()` mounts routers from one list. Import failures stop startup. Paths unchanged. Live containers not restarted |
| 2026-10-26 | `feat/error-envelope` | — | 1.3: every API error is `{error:{code,message}}`. Unhandled exceptions no longer reach the client. Live containers not restarted |
| 2026-10-26 | `feat/request-logging` | — | 1.4: one request id and one access line per request. Logging configured once. SQL echo off. Live containers not restarted |
| 2026-10-26 | `feat/unit-of-work` | — | 1.5: request session commits or rolls back. `get_owned_portfolio` replaces the copied ownership queries. Database routes are sync unless they await I/O. Live containers not restarted |
| 2026-10-26 | `feat/model-types` | — | 1.7: `Mapped[]` models. Prices and cash amounts widened to numeric(20, 8). Datetimes were already timezone-aware. Migration not applied to the live database |
| 2026-10-26 | `feat/health-checks` | — | 1.8: `/health/live` and `/health/ready` (503 when Postgres or Redis is down). `/health/` is the same readiness check. Test router removed. Live containers not restarted |
| 2026-10-26 | `feat/auth-hardening` | — | 1.9: PyJWT, refresh tokens hashed at rest, dummy bcrypt check for unknown usernames, `require_admin` removed. Migration not applied to the live database |
| 2026-10-26 | `feat/tr-statement-layout` | — | 2.2: Trade Republic PDF rows that a real statement splits across lines, or continues after a page break, are imported. Savings-plan quantities keep a decimal dot |
| 2026-10-26 | `feat/market-data-provider` | — | 2.4: one Yahoo provider, concurrency limit, backoff, Redis pipeline cache. Symbol search is only `GET /stock/symbols`. Live API not restarted |
| 2026-10-26 | `feat/stale-price-flags` | — | 2.5: a close older than 5 sessions is flagged on the valuation series and the chart. The last close is still the value. A missing price still raises. Live API not restarted |
| 2026-10-26 | `feat/previous-close` | — | 2.8: today's P&L uses the last finished session, in the listing's timezone. Live API not restarted |
| 2026-10-26 | `feat/derived-positions` | — | 2.10: position quantity and P&L are only rebuilt from transactions. The client update route is gone. Live API not restarted |


## 6b. Findings and to-do (2026-10-16)

### Done since the last update
- ✅ **UI modernisation** (#73): dashboard overview strip, sparklines, today's movers; Holdings Detail KPI strip, allocation donut, value-vs-invested chart; analytics units fixed; dead buttons removed.
- ✅ **Calculations** (`fix/calculations`):
  - Canonical engine: `core/domain`.
  - Split-aware valuation, with daily history from `get_daily_history`.
  - Performance series endpoint and the rebuilt Performance view.
  - Summary, holdings, overview, allocation, rebalancing and history moved onto the engine.
  - Transactions summary fixed; one risk-free rate.
  - Realistic demo seed: real prices, splits and dividends over 3 years.
- ✅ **Feature docs:** one `CLAUDE.md` per feature next to its backend router, frontend pointers, and `js/src/components/CLAUDE.md` for the app shell.

### New findings (not in the original audit)
| Area | Finding | Where |
|---|---|---|
| Import | ✅ Trade Republic PDF keeps dividends, EUR, fees and taxes. Cash rows are skipped. A real statement's split dates, page-break rows and dotted savings-plan quantities parse. The import toast reads `total_created` | `parsers/trade_republic.py` |
| Routing | ✅ Fixed: shadowed literal routes returned 422. Behind them were 4 more bugs (portfolio search response type, popular-assets schema, watchlist stats fields, JSON `tags.any`), now fixed | `GET /portfolios/search`, `/assets/search/popular` and `/suggestions`, `/watchlists/public` and `/stats`, `/statistical-indicators/configurations/search` |
| Broken endpoints | ✅ Fixed: `/overview` 500 (a tuple used as a float; now reads the engine) and `/analytics/users/dashboard` 500 (called a missing method) | calculations and analytics routers |
| Security | ✅ Fixed: `asset_search_service` was not scoped by user: `/assets/search/{id}` returned any user's asset, and popular/suggestions/breakdowns aggregated all users | `asset_search_service.py` |
| Watchlists | Alerts are never evaluated (the only caller is unused); `WatchlistPerformance` is only written on add; rating, thesis and tags have no UI | `watchlist_service.py` |
| Indicators | Selecting a saved configuration doesn't change the chart; the saved list never renders; performance metrics are hard-coded to 0; mixed `app.core` and `core` imports | `AssetAnalyticsView.jsx`, indicator services |
| Assets | The search box, sorting and "of N" count don't work (parameter and response mismatch); the dashboard's "Top Market Assets" are the user's own unsorted assets | `Assets.jsx`, `assets/router.py`, `Dashboard.jsx` |
| Auth | No settings or profile page (change password, edit or delete account unused); `models/auth.py` duplicates the user tables | `api/v1/auth`, `core/database/models/auth.py` |
| Dead code | `transactionAPI.bulkCreateTransactions` (endpoint doesn't exist); `Chart.jsx` `isPortfolioChart` branches; the `api/v1/dashboard/` stale `__pycache__`; legacy calc helpers (`_calculate_xirr`, `get_current_portfolio_value`, …) | various |
| Ops | SQLAlchemy echoes every SQL statement to the API log; a failed router import only logs a warning and the route silently disappears | `core/database/connection.py`, `main.py` |
| UX | Bulk-import success toast fires on 0 rows; the market-status tile ignores US holidays | `Transactions.jsx`, `market_data_service.py` |

### Next up (suggested order)
1. ✅ Benchmark comparison (2.7).
2. ✅ Trade Republic import fixes (2.2). The import UI counter already reads `total_created`.
3. ✅ FX (2.3): Yahoo daily pair closes.
4. ✅ Shadowed routes and the two 500s (1.2); ✅ `str(e)` leaks (1.3, envelope still open).
5. ✅ Watchlist alerts + worker (3.3 partly). Open: watchlist enrichment (UI Batch 4).
6. ✅ Indicator formulas and configuration wiring (2.9).
7. **Phase R release platform**, before any real data (1.6 Alembic baseline ✅, 1.1 settings ✅, 1.2 app factory ✅, 1.3 error envelope ✅, 1.4 request logging ✅, 1.5 unit of work ✅, 1.7 model types ✅, 1.8 health checks ✅, 1.9 auth hardening ✅, 2.2 Trade Republic import ✅, 2.4 market-data provider ✅, 2.5 stale-price flags ✅, 2.8 previous close ✅, 2.10 derived positions ✅). R.1 through R.7 are in place. Tailnet HTTPS is `https://ubuntu-1.tail13e229.ts.net:3443`. The backup and restore-drill timers are not installed. Next is 2.1, transfer lots and per-type validation.

---

## 7. Release strategy

**Branching: trunk-based.**
- `master` is always deployable.
- Work happens on short-lived branches (`feat/…`, `fix/…`, `chore/…`) and merges by squash-merge PR after the required `verify` check passes.
- Unfinished features hide behind env flags (`FEATURE_*`), not long-lived branches.
- Commit messages follow Conventional Commits, which drive the version bump and changelog.

**Versioning: SemVer.**
- `feat` produces a minor bump, `fix` a patch, and `feat!` or `BREAKING CHANGE` a major (we stay in 0.x until Phase 2 is done).
- release-please opens a release PR; merging it creates the `vX.Y.Z` tag and updates `CHANGELOG.md`.

**Artifacts are immutable images in GHCR**, built once and promoted unchanged:

| Tag | Produced by | Used by |
|---|---|---|
| `sha-<short>` | every master push | traceability and bisecting |
| `edge` | every master push | staging (auto) |
| `X.Y.Z`, `X.Y` | release tag | production (pinned to `X.Y.Z`) |

**Environments, all on the Jetson:**

| Env | Compose project | Source | Port | Data | Deploy |
|---|---|---|---|---|---|
| dev | `portfolio-dev` | local build, bind mounts, reload | 3200/8200 | dev volumes | `docker compose -f compose.dev.yaml up` |
| staging | `portfolio-staging` | `edge` | 3100 | seeded demo data, reset allowed | auto (timer) |
| prod | `portfolio` | `X.Y.Z` | 3000, plus HTTPS via NPM | real data, nightly backups | manual `scripts/deploy.sh prod X.Y.Z` |

**Promotion flow:** PR → `verify` (tests, build, arm64 stack smoke) → squash merge → `edge` published → staging auto-deploys and soaks → release PR merged → `vX.Y.Z` images → `deploy.sh prod X.Y.Z` (backup, migrate, up, smoke, auto-rollback on failure).

**Deploy style:** recreate, with health-gated `up --wait`. Expect a few seconds of downtime, which is acceptable for a personal app. If zero downtime ever matters, use blue/green: two `web` stacks (`portfolio-blue`/`portfolio-green`) with NPM switching the upstream.

**Database migrations: expand → migrate → contract.**
- A release may only *add* columns or tables, or backfill data.
- Destructive changes ship one release later, so the previous image still runs against the new schema. This keeps rollback a pure image swap.
- If a release must be irreversible, `deploy.sh` requires `--allow-irreversible` and takes a fresh backup first.

**Hotfixes:** branch from master (trunk is deployable), use a `fix:` commit, merge, and release a patch. Never patch production containers by hand.

**Pull-based deploys:** the Jetson pulls from GHCR. GitHub never gets SSH or a self-hosted runner on the home server, because the repo is public.

**What "doesn't ship broken" means, in layers:**
1. Locally, `scripts/verify.sh` before push (a pre-push hook is optional).
2. On the PR, the required `verify` check runs the same script on arm64.
3. Images are built once per tag; whatever was verified is what gets deployed.
4. Staging soaks `edge` before every prod release.
5. `deploy.sh` runs smoke checks after deploy and rolls back automatically to the last good version.
6. The uptime check and the error log alert after a release.
