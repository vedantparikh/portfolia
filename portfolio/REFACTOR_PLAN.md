# Portfolia — Production Refactor Plan

Status: **done** (2026-10-28), apart from the items in §6c that need the user, GitHub settings, or a feature that does not exist yet · Updated: 2026-10-28

Legend: ✅ done · 🟡 partly done (**Now:** says what is left) · ⏳ not started
Scope: `portfolio/` (FastAPI backend `python/app`, React frontend `js`, Docker, CI at git root)
Target host: NVIDIA Jetson AGX Xavier home server shared with ~35 other containers (see §1b)

---

## 0. Where we are (audit summary)

| Area | State | Most important issues |
|---|---|---|
| **Calculation correctness** | ✅ (2026-10-28) | One engine in `core/domain` (FIFO with fees, automatic splits, transfers, completed-only, no cost fallback, today's P&L, one risk-free rate, Yahoo FX). Chart, performance, risk, summary, holdings, overview, allocation, rebalancing, stored snapshots, analytics summary and user dashboard all read it. Indicators match `ta`. Open: beta against a total-return index (§6c). |
| **Backend architecture** | ✅ | Sync SQLAlchemy with `def` routes (ADR 0001), unit-of-work session, one error envelope, request ids, pydantic-settings, app factory, repositories for analytics/assets/auth, Alembic only, health checks, PyJWT with hashed refresh tokens in an httpOnly cookie. |
| **Frontend** | ✅ | Feature folders, per-feature `api.ts` on one client, TanStack Query, generated API types, `shared/ui` Modal and states, formatters enforced by lint, no financial maths, no HTML injection, access token in memory only. Vitest + MSW unit tests and a Playwright smoke test. |
| **Tests** | ✅ Green gate | 407 backend tests, quarantine empty, golden and snapshot tests for every number, 13 Vitest tests, Playwright smoke in `verify.sh --stack`. Coverage targets of Phase 5 are not measured (§6c). |
| **Infra / CI** | ✅ | `verify.sh --stack` on arm64 (with gitleaks), production images (non-root, Trivy-gated), prod/dev/staging compose, GHCR release workflow, deploy with rollback, staging sync, backups and restore drill, tailnet HTTPS and Gatus. Timers and branch protection are user steps (§6c). |

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
| ✅ 0.2 | ✅ `.env.example` templates and `.dockerignore` files (`f5579c3`). ✅ gitleaks runs over the whole history in `verify.sh` (CI checks out full history); `.gitleaksignore` lists the 24 historical findings. The history check found: old `SECRET_KEY`/`JWT_SECRET_KEY` values (not the current ones), an Alpha Vantage key and sample JWTs in deleted code, and the Postgres password `password`, **which production still used** (§6c). | gitleaks clean, secrets rotated |
| ✅ 0.3 | ✅ 59 dead files removed (`a1b50e4`). ✅ `scripts/setup.sh` creates every env file with generated secrets and the shared network; `setup-docker.sh` and `start_frontend.sh` removed. ✅ Docs consolidated 2026-10-28 (§6.4). | README accurate |
| ✅ 0.4 | One import root and one dependency file. **Done:** `python/app/pyproject.toml` (runtime deps + `dev` group incl. `ta`) and `uv.lock`, pinned to the versions the images already had; both Dockerfiles run `uv sync --frozen`; the gate checks `uv lock --check`. Removed `requirements*.txt`, the duplicate `python/pyproject.toml`, the empty `app/` package, environs, python-dotenv and yahooquery (API image 828 → 735 MB). `requires-python >= 3.14` (the image). | `pytest --collect-only` collects with **0 errors** |
| ✅ 0.5 | **Burn down `tests/quarantine.txt`** (50 entries: 8 uncollectable files, 42 xfail). Fix the `/app/v1` → `/api/v1` prefix and delete tests for removed APIs. Then turn on blocking lint: ruff on changed files via pre-commit, and eslint once `react/prop-types` is solved by TS or disabled. **Now:** Lint is gating (ruff + eslint, 0 warnings, 2026-10-15). Quarantine empty (2026-10-28): obsolete files deleted, auth/market/indicator/watchlist tests rewritten against current code. | Quarantine file empty, lint is a required check |
| 🟡 0.6 | ✅ CI gate: `scripts/verify.sh --stack` on `ubuntu-24.04-arm` for every PR and push to master. ⏳ GitHub branch protection (require `verify`, squash only, no direct pushes) is a repository setting (§6c). | A red check blocks merge |
| ✅ 0.7 | ✅ **Characterisation tests**: `tests/unit/test_calculation_snapshots.py` pins positions, value history, TWR/CAGR/XIRR, risk metrics, all indicators and the analytics/advanced-risk helpers on deterministic inputs (added in deps wave 3). | Every number change fails the gate and must be explained |

### Phase R: Release platform (≈1.5 weeks, right after Phase 0, *before* the big refactors)
There is no production data yet, so this is the cheapest moment to set up how releases work. Every later phase then ships through it. See §7 for the full release strategy.

| # | Work | Done when |
|---|---|---|
| ✅ R.1 | **Production images.** `Dockerfile.prod` for the API (`python:3.14.9-slim`, uv, uid 1000, uvicorn workers, no reload) and the web (`nginx:1.28.0-alpine` + `apk upgrade`, non-root, :8080, SPA fallback, `/api` → `api:8000`). API 735 MB (polars + pyarrow + pandas; the 400 MB target is not reachable), web 62 MB. Postgres keeps its build block so the live container is not recreated (§6c). | Both images start without bind mounts |
| ✅ R.2 | **Compose split.** `compose.yaml` (prod, images only), `compose.dev.yaml` (`portfolio-dev`, :3200/:8200), `compose.staging.yaml` (`portfolio-staging`, :3100/:8100, own volumes). Env files `env/{prod,staging}.env`. The legacy `docker-compose.yml`/`.prod.yml` are removed; `verify.sh` compares `compose.yaml` with the live Postgres container's config hash. | No `build:` or bind mounts on app services; Postgres hash matches |
| ✅ R.3 | **Release workflow.** release-please + arm64 GHCR images (`edge`/`sha-<short>` after CI on master; `X.Y.Z`/`X.Y`/`sha-<short>` on a tag), SBOM, provenance, Trivy gate. First run happens on the first push (§6c). | Tagging `v0.1.0` publishes pullable images |
| ✅ R.4 | **`scripts/deploy.sh <env> <version>`**: pull, `pg_dump`, migrate, restart api/app/worker (`--no-deps`), smoke, automatic rollback to `env/<env>.deployed`, prune to the last 3 releases. Proven by `scripts/test-deploy.sh` in the gate. | A deliberately broken release rolls itself back |
| ✅ R.5 | **Staging**: `scripts/staging-sync.sh` deploys `edge` on digest change and seeds demo data; `deploy/portfolia-staging.{service,timer}`. Installing the timer needs root (§6c). | A merge to master shows up on staging within 15 minutes |
| ✅ R.6 | **Backups and restore**: `backup.sh` (14 daily, 8 weekly, optional Nextcloud), `restore.sh` (prod needs `--allow-prod`), `restore-drill.sh`, timer units. Proven by `scripts/test-backup.sh`. Installing the timers needs root (§6c). | A restore drill passes |
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
| ✅ 2.1 | `domain/positions.py`: FIFO with fees, SPLIT, TRANSFER_IN/OUT and DIVIDEND (with a given amount and tax). Add schema validation: qty > 0 and price ≥ 0 per type. **Done:** completed-only, FIFO with fees, splits from market data (trades in today's share units). A transfer in opens a lot at the given cost and a transfer out closes lots FIFO at the given proceeds; both are split-adjusted and count as a deposit or withdrawal. Buys, sells, transfers and splits require quantity > 0, and price cannot be negative. An imported dividend may have quantity 0 because its cash amount is the statement total. | C1, C2, M2, M3 |
| ✅ 2.2 | Importer fix: the Trade Republic dividend amount and withholding tax are kept, and the currency is set. Run a data migration that recomputes affected rows. **Done:** dividends keep their cash amount, EUR currency and taxes stored, €1 trade fee split out (€0 savings plans), cash rows skipped with a reason. A real quarterly statement parses: split dates, page-break rows and dotted savings-plan quantities. No data migration (nothing imported from the old parser). Withholding tax is a separate statement row and stays skipped. | C2 |
| ✅ 2.3 | `core/domain/fx.py` + `MarketDataService.get_fx_rates`. `assets.currency` is the quote currency (no second column). `GBp`/`GBX` and `ILA` scale to GBP/ILS. Yahoo `{QUOTE}{PORTFOLIO}=X` daily closes (inverse if needed), same 6h Redis cache as history. Closes and live prices convert every day; cash converts only when `transaction.currency` differs. Missing rate raises. Dashboard totals stay per portfolio currency. | C3 |
| ✅ 2.4 | `MarketDataProvider` with one Yahoo implementation. **Done:** every Yahoo call goes through `YahooMarketDataProvider` (4 at a time, exponential backoff). Batch cache writes use one Redis pipeline. Symbol search is only `GET /stock/symbols` (the exact-ticker `/market-data/search` is gone). Valuation history is unchanged: split-adjusted closes (`auto_adjust=False`), plus splits and dividends, cached 6h. Requests still call Yahoo on a cache miss (3.3). | C1, H5, perf |
| ✅ 2.5 | `domain/valuation.py`: daily holdings × price × FX on a trading calendar, with explicit stale/missing flags. **Done:** `daily_series` forward-fills. A close older than 5 sessions sets `stale_price` and `stale_symbols` on that day and on the chart points; the value still uses the last close. No price at all raises `MissingPriceError` (never valued at cost). FX is applied by the caller before this. | H4, H6, M5 |
| ✅ 2.6 | `domain/returns.py` and `domain/risk.py`: TWR, XIRR (with opening value), CAGR, calendar-date period returns, and risk metrics with a single risk-free rate and percent units. **Now:** `core/domain/returns.py`: TWR, XIRR (period + annual), CAGR, calendar periods, `period_summary`, one `RISK_FREE_RATE`; chart, /performance, /multi-period and risk agree exactly. | H1, H3, M6, M10 |
| ✅ 2.7 | Benchmark shadow portfolio built on the same functions, with a total-return index. **Done:** `core/domain/benchmark.py` `shadow_series` + `GET /portfolios/calculations/portfolio/{id}/benchmark`, Performance Chart "Compare with"; old benchmark endpoints and ~560 lines of legacy helpers removed. A foreign-currency benchmark is converted with 2.3 before the shadow is built. | C4, H2 |
| ✅ 2.8 | Today's P&L formula and a correct previous close. **Done:** `day_change` is used by holdings, summary and overview. The previous close is the last session that started before the current one, using the bar's timezone, not the older of two downloaded rows. Cached 12 hours under the UTC date. | H5 |
| ✅ 2.9 | Allocation and rebalancing in shares. Fix the indicator formulas (Wilder RSI/ATR/ADX, population-std Bollinger, CCI, StochRSI). **Done (2026-10-16):** all 17 indicators match `ta` (reference test), real PSAR, configuration UI wired. **Now:** Allocation from live holdings, rebalancing in shares with the stored threshold. Indicator formulas open (PSAR stub, non-Wilder RSI/ATR/ADX, sample-std Bollinger). | M8, Low |
| ✅ 2.10 | `PortfolioAsset` is a cache rebuilt from transactions on every write and on refresh. **Done:** `PUT /portfolios/{id}/assets/{asset_id}` is gone, so a client cannot write quantity, cost, or P&L. Adding a holding (`POST /assets` and the legacy post) creates a buy. Deleting a holding deletes its transactions. | M1 |
| ✅ 2.11 | Re-run the Phase 0.7 characterisation snapshots and review **each** changed number against a hand calculation or a broker statement. **Done:** `test_calculation_snapshots.py` was re-run and the snapshot file did not change, so there was no number to review. Separately, every open position on a Trade Republic securities statement matches the share count and the cost basis (quantity × price) from that broker's own trade confirmations, to the cent. The statement's unrealized figure is market value minus that cost. No holdings or amounts are stored in the repo. | — |

### Phase 3: Consolidate backend modules (≈1.5 weeks)
| # | Work |
|---|---|
| ✅ 3.1 | Merge `portfolio_service`, `portfolio_calculation_service`, `portfolio_analytics_service`, `portfolio_risk_metrics_service`, `portfolio_advance_risk_metrics` and `portfolio_dashboard_service` into `modules/portfolios` (CRUD and holdings) plus `modules/analytics` (which orchestrates the domain functions and owns snapshots). Remove the dead dashboard router and service, or mount them properly. **Done:** Holdings are `modules/portfolios`. Series, risk and snapshot writes are `modules/analytics`. `core.services` still re-exports the two service classes. The dashboard router and service were already gone; the empty `api/v1/dashboard/` directory is removed. `/analytics/users/dashboard` stays, on the analytics service. |
| ✅ 3.2 | Move all DB access out of the analytics, assets and auth routers into repositories. **Done:** `modules/analytics/repository.py`, `modules/assets/repository.py` and `modules/auth/repository.py` own those queries. The request session still commits. Refresh-token reuse commits inside the auth repository, because the 401 would otherwise roll the revocation back. |
| ✅ 3.3 | Snapshots are persisted by a **background worker** (daily close, plus on transaction change), not inside request handlers. The same worker refreshes prices and FX. **Done:** Each pass refreshes watchlist alerts, holding prices, previous closes, daily history and FX. A snapshot is written when a transaction is newer than the last one, and once after 22:00 UTC if that close is not stored. Analytics reads the stored snapshot. Holding quotes are cache-only. Symbol search, a history or FX cache miss, and an explicit quote lookup still call Yahoo. |
| ✅ 3.4 | Replace the pickle `RedisClient` with a typed wrapper. Delete `SingletonMeta`, `watchlist_alert_service` (or finish it), the FHIR leftovers and `fix_asset_quantities_and_pnl.py` (which becomes a management command: `portfolia recalc`). **Done:** JSON get/set only, one client per process. `SingletonMeta` and the pickle FHIR helpers are gone. `watchlist_alert_service` was already gone. Holdings are rebuilt with `python -m portfolia recalc`. |
| ✅ 3.5 | Move the PDF export and transaction export to portfolio currency and formatted money. Stop summing volume across currencies. **Done:** Each row converts into its portfolio currency. Totals are per currency. The PDF and the preview print the currency code. A missing rate stays in the trade currency and is not added to the other total. |
| ✅ 3.6 | Enforce mypy (strict on `domain/` and `core/`, gradually elsewhere). Add an OpenAPI snapshot test so contract changes are deliberate. **Done:** `mypy core/domain` is in the verify gate (the rest of `core/` is still 264 errors). `tests/unit/openapi_operations.txt` pins method, path and operation id. Paths were already pinned by `api_routes.txt`. |

### Phase 4: Frontend (≈3 weeks, can start in parallel with Phase 2)
| # | Work |
|---|---|
| ✅ 4.1 | Tooling. **Done:** ESLint 9 flat config; Vitest + Testing Library + MSW (`src/test/`, MSW fails on unhandled requests) and a Playwright smoke test (`js/e2e/`), both in the gate. Not adopted: Prettier, husky/lint-staged, knip and jsx-a11y were not approved as new dependencies (§6c). |
| ✅ 4.2 | **TypeScript, gradually** (`allowJs`, strict for new files). API types are generated from FastAPI's `openapi.json` (`openapi-typescript`), and CI fails on drift. **Done:** `tsconfig.json` checks new `.ts` files and leaves the existing JavaScript unchecked. `src/shared/api/generated/schema.ts` is generated from the OpenAPI schema, and the verify gate fails if it drifts. |
| ✅ 4.3 | Split `api.js` into `shared/api/client.ts` (axios, single-flight refresh, `ApiError`) plus a per-feature `api.ts`. Remove the duplicate endpoints and the `portfolios[0]` bug. **Done:** `shared/api/client.ts` holds the axios instance, `apiErrorMessage` and the single-flight refresh. Endpoints live in `features/<name>/api.ts`, plus `shared/api/market.ts` and `shared/api/indicators.ts`. 39 uncalled wrappers are gone, among them `bulkUpdateUserAssets` with the `portfolios[0]` bug. The three asset wrappers are one `assetAPI` that returns response bodies. |
| ✅ 4.4 | Adopt **TanStack Query**: one hook per resource, invalidation on mutation, cache cleared on logout. Replace `assetCache` and `useAssetPreloader`. **Done:** Hooks live in `features/<name>/queries.ts`. The dashboard, the assets page (infinite query), the analytics tabs and the indicator views read through them too. Portfolio analytics and dashboard keys sit under `["portfolios", …]`, so portfolio and transaction writes refresh them. The portfolio detail (holdings, assets tab, performance metrics, charts, benchmark overlay, allocation donut) and the import screens (statement providers, already-imported rows) followed. The one fetch left in an effect is `InstrumentMappingPanel`'s batched ISIN resolution: it POSTs ten ISINs at a time and pushes each batch into the parent's mapping as it lands, so it stays a one-off job per parsed file. |
| ✅ 4.5 | `shared/ui`: `Modal` (portal, labelled, Esc, focus trap and restore), `Button`, `Card`, `Spinner`, `EmptyState`, `ErrorState`. All 21 dialogs use `Modal` with their existing look. Not built: a `FormModal` (zod would be a new dependency; the forms don't use react-hook-form) and a `Table` (no shared table shape). The search components and the two charts do different jobs (Yahoo vs own assets; OHLC vs indicator panes) and stay separate. |
| ✅ 4.6 | Security: remove `dangerouslySetInnerHTML` and the `innerHTML` tooltips. Keep a single `tokenStore`. Ideally put the refresh token in an httpOnly cookie, with the access token held in memory. **Done:** Risk reasoning and both chart tooltips are text nodes. Access and refresh tokens are only read and written in `shared/auth/tokenStore.ts`. They are still in `localStorage`. The httpOnly cookie is still an open decision. |
| ✅ 4.7 | **Delete all frontend financial math.** Display backend values only. One `formatMoney(value, currency, locale)`, with lint rules banning raw `toFixed` and `$`. **Done:** Money goes through `formatCurrency` / `useMoney()`, ratios through `formatRatio`. Chart tooltips and market caps use the asset's currency. ESLint `no-restricted-syntax` rejects `.toFixed(` and `$` before a digit or an interpolation outside `utils/formatters.jsx` and the glossary. What is left is input arithmetic in the transaction forms (via `toInputDecimal`) and a candle's open→close change in the chart tooltips. Locale stays `en-US`. |
| ✅ 4.8 | Routing: `ProtectedLayout` (Sidebar and `<Outlet/>`), `React.lazy` per route, an error boundary, and a 404 page. **Done:** `src/app/ProtectedLayout.jsx` owns the sidebar, the mobile drawer, and an error boundary that resets on navigation. Each route is lazy. Unknown paths render `NotFound`. Pages register search, the portfolio selector, and quick actions with `usePageChrome`. |
| ✅ 4.9 | Feature-folder layout (see §2.3). Migrate feature by feature: auth → portfolios → transactions → assets → watchlists → analytics → dashboard. **Done:** Those features live under `features/`. Shared UI and the concepts page stay in `components/`. |

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
| ✅ 6.1 | Worker service in the prod and staging compose files, same image, 384 MB limit, heartbeat healthcheck: prices, previous closes, history, FX, watchlist alerts, engine snapshots. |
| ✅ 6.2 | Redis password from `env/prod.env` (enforced by `ENVIRONMENT=production`), Trivy gate in the release workflow, Playwright e2e on every PR. Running e2e against the release images in staging before promotion waits for staging to run (§6c). |
| ⏸ 6.3 | Optional GPU profile and the ollama `LLMProvider`: deferred by design until a feature needs them (ADR 0004). |
| ✅ 6.4 | Docs: root `README.md` (product), `portfolio/README.md` (setup, architecture, API map, database, configuration), `CONTRIBUTING.md` (adding a feature, migrations, tests), `docs/RUNBOOK.md` (deploy, rollback, staging, backups, secrets, timers), `docs/adr/0001–0006`. `python/app/docs/`, `STARTUP_GUIDE.md` and the deployment checklist were folded in and deleted. |

---

## 4. Decisions

Answered:
- **Existing data:** none yet. No data migration or recompute report is needed, and the Phase 1.6 Alembic baseline can be created fresh with no `stamp`.
- **Compose intent:** drop the `/media` bind mount and keep DB/Redis private. Done in 0.1.
- **GPU:** use it via shared GPU services (ollama) and an optional GPU worker profile only where benchmarks justify it (§1b).

- **Multi-currency:** yes. Source is Yahoo `{QUOTE}{PORTFOLIO}=X` daily closes (free), inverted when only the reverse pair exists. ECB rates were not used.

- **Sync vs async DB:** sync SQLAlchemy with `def` routes (ADR 0001).
- **TypeScript:** gradual; generated API types, new files in TypeScript.
- **Refresh token:** httpOnly cookie, access token in memory (decided 2026-10-28, ADR 0006).
- **Public hostname:** Tailscale only (`https://ubuntu-1.tail13e229.ts.net:3443`).
- **Staging auto-deploy:** systemd timer following `edge`.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Numbers change for users after Phase 2 | Characterisation snapshots (0.7), a per-number review (2.11) and a changelog entry |
| Prod gets data before Alembic owns the schema | Land 1.6 before the first `deploy.sh prod`, and make `alembic check` (model drift) a CI gate |
| Yahoo rate limits or outages | Provider, cache and backoff are in place (2.4). The worker refreshes holding prices and FX (3.3 ✅). Symbol search and a cold history cache still call Yahoo |
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
| 2026-10-26 | `feat/transfer-lots` | — | 2.1: transfer in/out open and close FIFO lots at the given cost. Quantity and price are checked per type. Live API not restarted |
| 2026-10-27 | `feat/broker-statement-check` | — | 2.11: characterisation snapshots re-run, unchanged. Open positions on a broker securities statement match the confirmations' share count and cost to the cent |
| 2026-10-27 | `feat/portfolio-modules` | — | 3.1: holdings in `modules/portfolios`, series/risk/snapshots in `modules/analytics`. Empty dashboard package removed. Live API not restarted |
| 2026-10-27 | `feat/router-repositories` | — | 3.2: analytics, assets and auth queries live in repositories. Live API not restarted |
| 2026-10-27 | `feat/worker-snapshots` | — | 3.3: the worker refreshes holding prices and FX and writes snapshots. Requests no longer do. Live API not restarted |
| 2026-10-27 | `feat/cleanup-export` | — | 3.4–3.6: JSON Redis client, `python -m portfolia recalc`, PDF totals per portfolio currency, mypy on `core/domain`, OpenAPI operation snapshot. Live API not restarted |
| 2026-10-27 | `feat/frontend-contract` | — | 4.2 and 4.6: generated API types, text tooltips, one token store. 4.4: query cache replaces the asset preloader. Live UI not restarted |
| 2026-10-27 | `feat/frontend-contract` | — | 4.2, 4.4, 4.6: generated API types, query cache replaces the asset preloader, chart and risk HTML removed, one token store. Live UI not restarted |
| 2026-10-27 | `feat/app-shell` | — | 4.8: protected layout, lazy routes, error boundary, 404. 4.9 started: auth pages in `features/auth`. Live UI not restarted |
| 2026-10-27 | `feat/feature-folders` | — | 4.9: portfolios, transactions, assets, watchlists, analytics, and the dashboard live under `features/`. Live UI not restarted |
| 2026-10-27 | `feat/query-screens` | — | 4.4: portfolio, transaction, and watchlist screens read through the query cache and invalidate it after writes. Live UI not restarted |
| 2026-10-28 | `fix/manual-test-findings` | — | Manual pass after 4.4: adding a watchlist item no longer returns 500, existing assets can be watched, watchlist prices are formatted and drag reorder only runs in custom order, asset search filters by symbol, quick actions work on every page, login returns to the requested page. A watchlist threshold the price already meets is recorded when it is saved, and the alerts panel refreshes. Live API not restarted |
| 2026-10-28 | `feat/frontend-finish` | — | 4.3 per-feature API modules, 4.4 query hooks for the dashboard, assets page and analytics tabs, 4.7 formatters plus lint rules, 4.5 `shared/ui` with every dialog on `Modal`. Checked with eslint, tsc and vite build only. Live UI not restarted |
| 2026-10-28 | `chore/uv-lockfile` | — | 0.4: one `pyproject.toml` with a uv lockfile; requirements files, the duplicate pyproject, the empty `app/` and three unused packages removed |
| 2026-10-28 | `feat/refresh-cookie` | — | 4.6: refresh token in an httpOnly `Secure` `SameSite=Strict` cookie, access token in memory, session restored on load |
| 2026-10-28 | `chore/security-scans` | — | 0.2, 6.2: gitleaks over history in the gate, Trivy gate on releases, web image `apk upgrade` (2 critical OpenSSL CVEs), Redis password from `env/prod.env`, legacy compose files removed |
| 2026-10-28 | `test/frontend-tooling` | — | 4.1: Vitest + Testing Library + MSW, Playwright smoke in `verify.sh --stack` |
| 2026-10-28 | `test/quarantine` | — | 0.5: quarantine emptied (8 obsolete files deleted, watchlist and integration tests rewritten); indicator request without indicators is a 422 |
| 2026-10-28 | `fix/analytics-engine` | — | Stored snapshots, `/analytics/.../summary` and `/users/dashboard` on the engine (percent, no cost fallback, totals per currency); migration `d4e8a2f61c07` clears old metrics; dead analytics helpers removed |
| 2026-10-28 | `fix/analytics-engine` | — | 0.3: `scripts/setup.sh` |
| 2026-10-28 | `docs/consolidate` | — | 6.4: README, CONTRIBUTING, RUNBOOK, ADRs, feature references corrected, old guides folded in and deleted |
| 2026-10-28 | `master` | `7309f68` | Deployed to the live `portfolio` project from local `portfolia-{api,web}:prod` images: dump in `env/backups/`, migration `d4e8a2f61c07`, `ENVIRONMENT=production`, `DEBUG=false`. Rotated: the Postgres password (was `password`), the JWT key (was the 40-character placeholder; everyone signs in again), a new Redis password. HTTPS login, cookie refresh, health and the worker checked. About 3 minutes down |
| 2026-10-28 | `master` | `812caac` | Realized P&L before the tax withheld at sale; `python -m portfolia recalc` fixed. Trade Republic sync: reads Bachat's pytr export (read-only `/pytr`), knock-outs priced from their fills and redemptions booked as sales. Deployed: migration `e5b2c8d40a17`, 82 holdings recalculated, portfolio 11 renamed "Trade Republic (old import)", new synced "Trade Republic" (id 16, 948 rows) reconciles with pytr: all 20 open positions, realized 14,359.65 EUR before tax incl. -10,112.28 EUR on 16 knock-outs |
| 2026-10-29 | `master` | `44da284` | Tax view: summary adds dividends before tax, tax withheld, tax entries (Trade Republic refunds after loss offsetting, Vorabpauschale; migration `f1c4d7a92b36`), net taxes paid and realized after tax. A Yahoo quote older than 4 days gives way to a newer daily close (82W.SG was frozen at 18.705 since 2024-07-23). Checked before deploy: an independent FIFO replay of the pytr export matched every ISIN of portfolio 16; holdings, summary, overview, allocation, series cost basis and analytics agree on every portfolio. Deployed: 41 tax entries; portfolio 16 withheld 10,192.76, adjustments -5,023.20, net taxes 5,169.56, realized after tax 9,397.14 EUR. Rollback images `:pre-taxes` |
| 2026-10-29 | `master` | `65f3f48` | Fetch from Trade Republic on demand (ADR 0008): pytr 0.4.10 web login from the portfolio page, session Fernet-encrypted in `broker_connections` (migration `a7d3e9c51f28`), download into the shared pytr folder, then import into linked portfolios. Deployed: `api` mounts `/pytr` read-write, `worker` read only; API reaches api.traderepublic.com. Not yet run against a real login. Rollback images `:pre-trfetch` |
| 2026-10-29 | `chore/plan-gaps` | — | Open gaps from §6b: US market status from an NYSE calendar (holidays, early closes, next open and close on the dashboard tile); `GET /assets/` sorts server-side (columns in SQL, quote fields from the cached quotes) and returns `X-Total-Count`, so the Assets sort and "of N" work and the dashboard's top assets are by market cap; dead code removed (`models/auth.py`, `generate_two_factor_code`, `Chart` portfolio branches, `WatchlistSidebar`) |
| 2026-10-29 | `master` | `64f30fd` | Deployed #120 (no migration): market status checked live (open, next close 16:00 ET); `/assets/` returns `X-Total-Count` 72 for demouser and sorts by name. Found: `get_symbols_info` returns no quotes at all when one symbol is an ISIN Yahoo rejects (`yf.Tickers` raises "Invalid ISIN number" before the per-symbol try), so demouser's asset details and quote sorts are empty; this predates #120. Rollback images `:pre-plangaps` |
| 2026-10-29 | `master` | `170c0d7` | Deployed #121 (no migration): quotes are fetched per symbol, so a rejected ISIN no longer empties the batch. Live for demouser: 55 of 72 assets have a price (the rest are knock-outs and listings Yahoo does not quote), top by market cap NVDA, AAPL, NVD.F, APC.F, MSFT. Rollback images `:pre-quotebatch` |
| 2026-10-29 | `master` | `f4870ed` | Deployed #123 (backlog sweep): migration `b3f8c2d14e67` (watchlist item currency; the worker filled it on its first pass). Checked live as demouser: asset highlights and change filter, GFS (AAPL hold: monthly 72.3, weekly 64.6, daily 56.1) and MACD signals, public lists, removed routes 404, `/settings` 200, no API errors. Beta now vs the currency's total-return default: portfolio 9 (USD) 0.62, portfolio 11 (EUR) 1.07. Portfolio 16's advance-risk returns `'Close'` — the same with `^GSPC`, so it predates this release. Rollback images `:pre-backlog` |
| 2026-10-29 | `master` | `37c9fd8` | Deployed #124 (no migration): portfolio 16's advanced risk computes again (beta 0.99 vs EUNL.DE; closed knock-outs no longer break it); backtests live (AAPL MACD 2 trades +62.2 % vs holding +129.5 %, GFS no trades; EUNL.DE MACD +59.0 % vs +73.6 %); asset modal chart has the indicator picker and Open analysis. Found: loading `/assets` directly (reload or a typed URL) redirects to `http://…:8080/assets/` because nginx's `try_files $uri $uri/` matches the build's `assets/` folder; in-app navigation is unaffected. Rollback images `:pre-backtest` |
| 2026-10-29 | `master` | `48fd4e0` | Deployed #127 (no migration; web image unchanged, only the API restarted): pypdf 6.21.2, no pip in the API image. Trivy on the running API image: no HIGH/CRITICAL Python findings (were pypdf ×3, msgpack ×2, urllib3 ×2, setuptools); 44 HIGH Debian findings, none fixable yet. Health, worker and HTTPS OK. Rollback images `:pre-securitydeps` |
| 2026-10-29 | `master` | `bcfb082` | Deployed #129 (no migration; frontend only, API image rebuilt from the same code): metric guide on `/concepts` and ⓘ tips next to the app's numbers. Health, worker refresh and HTTPS `/concepts` 200, the tip text is in the served bundle, no API errors. Rollback images `:pre-metricguide` |

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
| Assets | ✅ Search, sorting and the "of N" count work; the dashboard's "Top Market Assets" are the user's own assets by market cap | `Assets.jsx`, `assets/router.py`, `Dashboard.jsx` |
| Auth | No settings or profile page (change password, edit or delete account unused); `models/auth.py` duplicates the user tables | `api/v1/auth`, `core/database/models/auth.py` |
| Dead code | `transactionAPI.bulkCreateTransactions` (endpoint doesn't exist); `Chart.jsx` `isPortfolioChart` branches; the `api/v1/dashboard/` stale `__pycache__`; legacy calc helpers (`_calculate_xirr`, `get_current_portfolio_value`, …) | various |
| Ops | SQLAlchemy echoes every SQL statement to the API log; a failed router import only logs a warning and the route silently disappears | `core/database/connection.py`, `main.py` |
| UX | Bulk-import success toast fires on 0 rows; ✅ the market-status tile follows the NYSE calendar | `Transactions.jsx`, `market_data_service.py` |

### Next up
The plan is finished. What is left is in §6c.

---

## 6c. Left on purpose (2026-10-28)

| Item | Why it is not done here | Who |
|---|---|---|
| Rotate the Brevo SMTP key; revoke the Alpha Vantage key found in history | Needs the provider accounts | User |
| Branch protection on `master` (require `verify`, squash only) | GitHub repository setting | User |
| First GHCR release; set both packages Public | Happens on the first push and release PR | User |
| Create `/mnt/samsung_ufs/backups/portfolio` and install `portfolia-{backup,restore-drill,staging}.timer` | Needs root; belongs in an Ansible role. Until then `backup.sh` and `deploy.sh` cannot write their dumps | User |
| E2E against release images in staging before promotion | Needs staging running | After timers |
| Prettier, husky/lint-staged, knip, jsx-a11y; hypothesis, testcontainers, schemathesis, pytest-socket; coverage targets | New dependencies not approved in this pass | Ask first |
| Postgres on the official image | Recreates the live container; needs a planned window and a dump | Planned window |
| Beta against a total-return index; Benchmarks tab on the shadow comparison | Product changes, not refactor | Backlog |

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
