# Portfolio analytics (risk, allocation, rebalancing, benchmarks, history)

**Purpose:** risk metrics, target allocations with drift and rebalancing trades, benchmark records, and the daily value history.

**State (2026-10-28):** ✅ risk, advance-risk, allocation analysis, rebalancing, history, summary, snapshots, user dashboard — all on the engine. Benchmark *comparison* is the shadow portfolio on the performance chart (`GET /portfolios/calculations/.../benchmark`), not these records.

## Backend — `router.py` (prefix `/api/v1/analytics`). Stored rows go through `modules/analytics/repository.py`.
| Endpoint | Service | Behaviour |
|---|---|---|
| `GET /portfolios/{id}/risk?period=` | `modules/analytics/risk.py` | Volatility, Sharpe, Sortino, VaR 95/99 (`value_at_risk_pct`), CVaR, max drawdown, Calmar (percent) + `risk_assessment` {level, reasoning text}. Input = engine daily returns (`get_portfolio_history`). Sample std, √252, `RISK_FREE_RATE` |
| `GET /portfolios/{id}/advance-risk?period=` | `modules/analytics/advance_risk.py` | Beta / Jensen's alpha vs `^GSPC` (price index), HHI, diversification ratio, effective number of assets. First call ~20 s (index history) |
| `GET/POST/PUT/DELETE /portfolios/{id}/allocations[/{aid}]` | `modules/analytics/service.py` | Target allocations (percent, min/max, `rebalance_threshold`, frequency) |
| `GET /portfolios/{id}/allocations/analysis` | same | Weights from live holdings (`PortfolioService.get_portfolio_holdings`), drift = current − target, `requires_rebalancing` when \|drift\| > threshold (default 5). Unpriced positions skipped; targeted-but-unheld assets included at 0% |
| `GET /portfolios/{id}/rebalancing/recommendations` | same | Actions in **shares**: drift amount ÷ current price, current/target quantity, trade value, price; 0.1% commission estimate; priority/timing from max drift. tax/risk/return impact = null |
| `POST/GET /portfolios/{id}/rebalancing/events` | same | Stored rebalancing events (no UI) |
| `POST/GET /portfolios/{id}/benchmarks` | router | Benchmark records (symbol, name, primary) |
| `GET /portfolios/{id}/performance/history?days=` | engine | Daily value + FIFO cost basis, newest first, read-only (no snapshot writes). Used by no screen now |
| `GET /portfolios/{id}/performance/snapshot` (newest row), `DELETE …/performance/{snapshot_id}`, `GET …/performance/comparison` | stored rows | The worker (`workers/book.py`) writes one when a transaction is newer than the last snapshot or the last daily close is missing: `PortfolioPerformanceHistory` with `engine_metrics`: value and FIFO cost at the last close, and one-year TWR, annualised TWR, volatility, Sharpe, max drawdown, VaR 95/99, all percent. A missing price raises; nothing is valued at cost. Rows written before migration `d4e8a2f61c07` keep value and cost but their metrics are null. No UI caller |
| `GET /portfolios/{id}/summary` | `engine_metrics` | Live engine run: value, cost, unrealized, one-year TWR (`total_return`) and annualised TWR, in the portfolio currency. No UI caller (`analyticsAPI.getPortfolioAnalyticsSummary` is unused) |
| `GET /users/dashboard` | same | One summary per portfolio plus `portfolios.totals`, one entry per currency (never added across currencies), and the snapshot count of the last 7 days. `force_refresh` is ignored. No UI caller |

## Frontend — `js/src/features/analytics/` (tabs inside Holdings Detail)
- **Analytics** `PortfolioAnalytics.jsx`: Risk Metrics + Advanced Metrics cards with plain-language hints, period select, risk-level modal (`reasoning` rendered as text).
- **Allocations** `PortfolioAllocationManager.jsx`: edit targets.
- **Rebalancing** `RebalancingRecommendations.jsx`: summary, actions ("SELL 95.88 META ≈ 70,639 · 169.52 → 73.64 shares at 736.72", amounts via `useMoney` in the portfolio currency), current → target allocation.
- **Benchmarks** `BenchmarkComparison.jsx`: list/add benchmarks. The primary one is the default for the chart's "Compare with". The tab's "Benchmark comparison is coming" note is stale: the chart is the live comparison. This tab does not call `/portfolios/calculations/.../benchmark`.
- `AssetAnalyticsView.jsx` / `IndicatorConfigurationManager.jsx` belong to indicators (see `api/v1/statistical_indicators/CLAUDE.md`).
- `analyticsAPI` in `js/src/features/analytics/api.ts`; query hooks in `features/analytics/queries.ts`, keyed under `["portfolios", id, "analytics", …]` so portfolio and transaction writes refresh them. `AllocationDonut` (Holdings Detail) also reads `/allocations/analysis`.

## Known gaps / planned
- Point the Benchmarks tab at the shadow comparison (plan 2.7 is done on the chart). Beta should use a total-return index.
- Risk endpoints are slow cold (Yahoo); acceptable for now per user.
