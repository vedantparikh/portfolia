# Portfolios (CRUD, positions, holdings, summary)

**Purpose:** a user's portfolios, the positions in them and their live value / P&L.

**State (2026-10-16):** ✅ core flows work and agree with each other. Numbers come from `core/domain` (see `core/domain/CLAUDE.md`).

## Backend — `router.py` (prefix `/api/v1/portfolios`), `core/services/portfolio_service.py`
| Endpoint | Behaviour |
|---|---|
| `POST/GET /`, `GET/PUT/DELETE /{id}`, `DELETE /{id}/hard` | CRUD; delete is soft (is_active) unless `/hard` |
| `GET /{id}/holdings` | Live holdings: quantity (today's share units), cost basis (FIFO+fees), `current_price`, `current_value`, unrealized, today's P&L (`day_change`), realized, `weight_percent`. No price → value fields null. Includes fully sold assets (qty 0) for realized P&L |
| `GET /{id}/summary` | Sum of the same holding rows (open positions only): value, cost, unrealized (priced positions only), today's P&L / % on start-of-day value + cash invested today, `total_realized_pnl`, `missing_prices` |
| `GET /statistics/overview` | Same rows across active portfolios, summed **per currency** in `totals[]` (value, holdings, today's P&L/%); `total_value`/`currency`/`today_pnl` only when all portfolios share one currency; missing prices. Dashboard "Total Value" tile |
| `POST /{id}/refresh` | Rebuilds every position from transactions (picks up new splits) and re-prices |
| `POST/GET /{id}/assets`, `GET /{id}/assets/details`, `PUT/DELETE /{id}/assets/{asset_id}`, `POST /{id}/assets/legacy` | Position records (`PortfolioAsset`) |
| `POST/GET /{id}/transactions` | Portfolio-scoped transaction create/list (create triggers `recalculate_asset_state`) |
| `GET /search?search_term=&currency=`, `GET /public/discover` | Own portfolios by name/currency; discover lists public portfolios. No UI for either |

`PortfolioAsset` is a **cache** rebuilt by `recalculate_asset_state(portfolio_id, asset_id)` on every transaction write and on refresh: `compute_position` on FX-converted trades + live price converted the same way. Prices: `MarketDataService.get_current_prices` (Redis 60s), previous close `get_yesterdays_closes` (last finished session, 12h, UTC-date key), both multiplied by the FX rate on that day.

## Frontend — `js/src/components/portfolio/`
- Route `/portfolio` → `Portfolio.jsx`: header, portfolio selector, five views (icon buttons):
  1. **Overview** — `PortfolioCard` + recent transactions.
  2. **Holdings Detail** — `PortfolioDetail.jsx`: KPI strip (summary), sortable holdings table (footer = summary totals), `AllocationDonut` (allocation analysis), `ValueVsInvestedChart`; tabs Analytics / Allocations / Rebalancing / Benchmarks (see `api/v1/analytics/CLAUDE.md`).
  3. **Portfolio Assets** — `PortfolioAssets.jsx` cards (`PortfolioAssetCard`), highlights (`StatCard`), filters; enriched with `/assets?include_detail` for sector/market cap/24h.
  4. **Performance Chart** — `PortfolioChart.jsx` (see `api/v1/portfolio_calculations/CLAUDE.md`).
  5. **Performance Metrics** — `PortfolioPerformanceMetrics.jsx`.
- Modals: `CreatePortfolioModal`, `EditPortfolioModal`.
- `portfolioAPI` in `services/api.js`.

## Workflow
Create portfolio → add transactions (Transactions page, PDF import, or Add Position) → positions rebuild automatically → Holdings Detail shows live value; Refresh rebuilds/re-prices.

## Known gaps
- `PUT /{id}/assets/{asset_id}` lets clients write quantity/cost/P&L directly (bypasses transactions) — plan 2.10.
- `PortfolioSummary()` returned bare for a foreign portfolio (validation error path).
- No FX yet (plan 2.3): a portfolio holds only assets quoted in its own currency — `add_transaction` raises `CurrencyMismatchError` (400) otherwise, and records the portfolio currency on the transaction.
- Delete flows have no undo; holdings include zero-quantity rows in the table.

## Planned
Plan 2.10 (PortfolioAsset fully derived, no client writes), 3.1 (module consolidation), 3.3 (worker refreshes prices), 2.3 FX.
