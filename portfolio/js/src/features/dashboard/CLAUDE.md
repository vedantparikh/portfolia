# Dashboard (`/dashboard`, `Dashboard.jsx`)

**Purpose:** a one-screen overview of everything the user owns, plus the market.

**State (2026-10-27):** ✅ works. It's frontend-only: it aggregates existing endpoints, and there is no dashboard backend router.

## Sections and data sources
| Section | Source |
|---|---|
| Welcome header | `AuthContext` profile |
| Overview strip (`StatCard`s): Total Value with today's change — one amount per currency ("$1,161,431.78 · €0.00"), never summed across currencies — Portfolios, Holdings, US Market | `portfolioAPI.getStatisticsOverview` (`totals[]` per currency from live holdings; ~5 s), `marketAPI.getMarketStatus` |
| Your Portfolios: value, today's P&L, total P&L, 3-month sparkline | `getPortfolios` + `getPortfolioSummary` per portfolio + `portfolioCalculationsAPI.getPerformanceSeries(id, "3m")` |
| Recent Transactions (5) | `transactionAPI.getTransactions({limit: 5, order: desc})` |
| Today's Movers: top 3 / bottom 3 held symbols by today's % | `getPortfolioHoldings` per portfolio, de-duplicated by symbol. The browser only sorts |
| Top Market Assets (10) | `assetAPI.getAssets({sort: market_cap, include_detail})` |
| Quick Actions | Links |

Each section is its own query (`queries.ts`, plus `useRecentTransactions`, `useTopAssets` and `useUnreadAlertCount` from their features), so they load in parallel and come from the cache when you return within 5 minutes. A section shows its spinner only on the first load. Refresh invalidates every section, and the refresh button spins while any of them refetches. Portfolio and transaction writes elsewhere invalidate the portfolio cards and movers.

## Known gaps
- Market status ignores US holidays.
- No combined unrealized P&L across portfolios (the backend overview could add it).
- Top Market Assets are the user's own assets (`/assets/`), and the `sort=market_cap` param is ignored by the backend, so neither "top" nor "market" holds.

## Planned
Nothing scheduled.
