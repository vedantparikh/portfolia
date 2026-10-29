# Dashboard (`/dashboard`, `Dashboard.jsx`)

**Purpose:** a one-screen overview of everything the user owns, plus the market.

**State (2026-10-28):** ✅ works. It's frontend-only: it aggregates existing endpoints, and there is no dashboard backend router.

## Sections and data sources
| Section | Source |
|---|---|
| Welcome header | `AuthContext` profile |
| Overview strip (`StatCard`s): Total Value with today's change — one amount per currency ("$1,161,431.78 · €0.00"), never summed across currencies — Portfolios, Holdings, US Market (open or closed by NYSE hours and holidays, with the next close or open in local time) | `portfolioAPI.getStatisticsOverview` (`totals[]` per currency from live holdings; ~5 s), `marketAPI.getMarketStatus` |
| Your Portfolios: value, today's P&L, total P&L, 3-month sparkline | `getPortfolios` + `getPortfolioSummary` per portfolio + `portfolioCalculationsAPI.getPerformanceSeries(id, "3m")` |
| Recent Transactions (5) | `useRecentTransactions(5)` → `GET /transactions/?limit=5` (the backend returns newest first; the `order` params are ignored) |
| Today's Movers: top 3 / bottom 3 held symbols by today's % | `getPortfolioHoldings` per portfolio, de-duplicated by symbol. The browser only sorts |
| Top Market Assets (10) | `useTopAssets()` → `assetAPI.getAssets({limit: 10, sort_by: market_cap, sort_order: desc, include_detail})` |
| Unread alerts link | `useUnreadAlertCount()` (`GET /watchlists/alerts?unread_only=true&limit=1`) |
| Quick Actions | Links |

Each section is its own query (`queries.ts`, plus `useRecentTransactions`, `useTopAssets` and `useUnreadAlertCount` from their features), so they load in parallel and come from the cache when you return within 5 minutes. A section shows its spinner only on the first load. Refresh invalidates every section (and reloads the user), and the refresh button spins while the portfolio cards, recent transactions or top assets refetch. Portfolio and transaction writes elsewhere invalidate the portfolio cards and movers.

## Known gaps
- No combined unrealized P&L across portfolios (the backend overview could add it).
- Top Market Assets are the user's own assets (`/assets/`) by market cap, not the market's.

## Planned
Nothing scheduled.
