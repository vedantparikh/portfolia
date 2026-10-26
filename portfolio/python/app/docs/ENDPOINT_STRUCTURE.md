# HTTP API

Base URL on the server: `http://127.0.0.1:8000`. Interactive schema: `/docs`.

Almost every route is under `/api/v1` and requires `Authorization: Bearer <access token>`. Exceptions are noted. A missing or foreign resource is 404 when the code raises `NotFoundError`, and 400 for other domain errors (oversell, wrong currency, bad input). Unexpected errors are logged and returned as a fixed sentence, not the exception text.

The tables below are the map. Request fields and the corner cases live in the feature doc linked on each row. If this file and that doc disagree, fix this file.

| Prefix | Auth | Feature doc |
|---|---|---|
| `POST /api/v1/auth/register`, `/login`, `/refresh`, `/forgot-password`, `/reset-password`, `/verify-email` | public (rate limited) | [auth](../api/v1/auth/CLAUDE.md) |
| `/api/v1/auth/me`, `/change-password`, `/logout` | bearer | same |
| `/api/v1/portfolios` | bearer, scoped to the user | [portfolios](../api/v1/portfolio/CLAUDE.md) |
| `/api/v1/portfolios/calculations` | bearer | [performance](../api/v1/portfolio_calculations/CLAUDE.md) |
| `/api/v1/transactions` | bearer | [transactions](../api/v1/transactions/CLAUDE.md) |
| `/api/v1/transactions/pdf` | bearer | [PDF export](PDF_EXPORT_README.md) |
| `/api/v1/account-statements` | bearer | [import](../api/v1/account_statements/CLAUDE.md) |
| `/api/v1/analytics` | bearer | [analytics](../api/v1/analytics/CLAUDE.md) |
| `/api/v1/assets`, `/api/v1/assets/search` | bearer | [assets](../api/v1/assets/CLAUDE.md) |
| `/api/v1/watchlists` | bearer | [watchlists](../api/v1/watchlist/CLAUDE.md) |
| `/api/v1/statistical-indicators` | bearer; public indicator sets are readable | [indicators](../api/v1/statistical_indicators/CLAUDE.md) |
| `/api/v1/stock/symbols` | optional; anonymous callers are limited to 10 searches an hour per IP | [market](../api/v1/market/CLAUDE.md) |
| `/api/v1/market-data` | bearer | same |
| `GET /health/live` | public | process is up; does not check Postgres or Redis |
| `GET /health/ready`, `GET /health/` | public | Postgres and Redis; 503 when either is down. Compose and Gatus call `/health/` |

There is no `/api/v1/dashboard` router. The dashboard page calls portfolios, transactions, and market data itself.

Literal paths are registered before `/{id}` paths. A test pins that order (`tests/unit/test_route_order.py`). FastAPI wraps included routers, so do not assert on `app.routes`; call the app through `TestClient`.

Percent fields are percents (`15.0`, not `0.15`). Money is decimal. Undefined metrics are `null`.

The Postman collection next to this file is not kept up to date. Use `/docs`.
