# Architecture

Portfolia is one API process, one worker process, Postgres, Redis, and a React dev server. It is not a set of independently deployed microservices.

```
browser :3000
  └─ Vite dev server (proxies /api)
        └─ API :8000
              ├─ core/services   SQLAlchemy session, Yahoo via Redis
              ├─ core/domain     pure functions: positions, valuation, returns, benchmark
              └─ Postgres, Redis
        worker (same image)
              └─ every WORKER_INTERVAL_SECONDS: watchlist alerts, holding prices, FX, snapshots
```

## Request path

`api/v1/<feature>/router.py` validates the body, requires `get_current_active_user`, and calls a service. The service takes a SQLAlchemy `Session` in `__init__`. Analytics, assets and auth keep their queries in `modules/*/repository.py`. Other routers still query directly.

Services that need a portfolio number call `core/domain`. They do not reimplement FIFO, TWR, or risk. The UI displays those numbers and does not recompute them. The rules are in [core/domain/CLAUDE.md](../../core/domain/CLAUDE.md).

## Market data

Only `core/services/market_data_service.py` talks to Yahoo. Valuation uses split-adjusted, not dividend-adjusted, daily closes, plus the split and dividend events. Dividends affect performance only through dividend transactions. Tests mock this service.

## Auth

JWT access token (15 minutes) and rotating refresh token (30 minutes). The UI keeps both in `localStorage`. Every row a user can see is filtered by `user_id`.

## Schema

Alembic is the only schema authority. `start_api.sh` runs `alembic upgrade head` before the process serves. Tests call `create_all` on SQLite. A model change needs a migration; the gate fails on drift. See [development/MIGRATION_GUIDE.md](../development/MIGRATION_GUIDE.md).

## What is deliberately out of this process

- No GPU. Optional later use of the shared Ollama server is described in [REFACTOR_PLAN.md](../../../../REFACTOR_PLAN.md) and is not wired up.
- No Sentry. Failures go to the API log.
- The worker refreshes holding prices, previous closes, daily history and FX, and writes a performance snapshot after a transaction and after 22:00 UTC. Analytics reads that row. Holding quotes do not call Yahoo.
