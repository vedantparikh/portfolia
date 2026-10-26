# Portfolio analytics (risk, allocation, rebalancing, benchmarks, history)

**Purpose:** risk metrics, target allocations with drift and rebalancing trades, benchmark records, and the daily value history.

**State (2026-10-26):** ✅ risk, advance-risk, allocation analysis, rebalancing, history. Benchmark *comparison* is the shadow portfolio on the performance chart (`GET /portfolios/calculations/.../benchmark`), not these records. The Benchmarks tab still shows "comparison is coming". ⚠️ `/summary`, `/performance/snapshot`, `/performance/comparison` use legacy snapshot metrics. ⚠️ `/users/dashboard` responds but uses legacy metrics.

## Backend — `router.py` (prefix `/api/v1/analytics`)
| Endpoint | Service | Behaviour |
|---|---|---|
| `GET /portfolios/{id}/risk?period=` | `portfolio_risk_metrics_service.py` | Volatility, Sharpe, Sortino, VaR 95/99, CVaR, max drawdown, Calmar (percent) + `risk_assessment` {level, reasoning HTML}. Input = engine daily returns (`get_portfolio_history`). Sample std, √252, `RISK_FREE_RATE` |
| `GET /portfolios/{id}/advance-risk?period=` | `portfolio_advance_risk_metrics.py` | Beta / Jensen's alpha vs `^GSPC` (price index), HHI, diversification ratio, effective number of assets. First call ~20 s (index history) |
| `GET/POST/PUT/DELETE /portfolios/{id}/allocations[/{aid}]` | `portfolio_analytics_service.py` | Target allocations (percent, min/max, `rebalance_threshold`, frequency) |
| `GET /portfolios/{id}/allocations/analysis` | same | Weights from live holdings (`PortfolioService.get_portfolio_holdings`), drift = current − target, `requires_rebalancing` when \|drift\| > threshold (default 5). Unpriced positions skipped; targeted-but-unheld assets included at 0% |
| `GET /portfolios/{id}/rebalancing/recommendations` | same | Actions in **shares**: drift amount ÷ current price, current/target quantity, trade value, price; 0.1% commission estimate; priority/timing from max drift. tax/risk/return impact = null |
| `POST/GET /portfolios/{id}/rebalancing/events` | same | Stored rebalancing events (no UI) |
| `POST/GET /portfolios/{id}/benchmarks` | router | Benchmark records (symbol, name, primary) |
| `GET /portfolios/{id}/performance/history?days=` | engine | Daily value + FIFO cost basis, newest first, read-only (no snapshot writes). Used by no screen now |
| `GET /portfolios/{id}/performance/snapshot`, `DELETE …/{snapshot_id}`, `GET /summary`, `GET /performance/comparison` | legacy | Persisted `PortfolioPerformanceHistory` rows from `create_performance_snapshot`; metrics count deposits as returns, calendar days, fractions. No UI caller |
| `GET /users/dashboard?force_refresh=` | legacy | Per-portfolio `get_portfolio_analytics_summary` (cost-basis fallback when no price) + snapshot count. `force_refresh` (default true) re-prices every asset from Yahoo and writes snapshots. Wired in `api.js`, no screen uses it |

## Frontend — `js/src/components/analytics/` (tabs inside Holdings Detail)
- **Analytics** `PortfolioAnalytics.jsx`: Risk Metrics + Advanced Metrics cards with plain-language hints, period select, risk-level modal (renders `reasoning` HTML via `dangerouslySetInnerHTML` — XSS item 4.6).
- **Allocations** `PortfolioAllocationManager.jsx`: edit targets.
- **Rebalancing** `RebalancingRecommendations.jsx`: summary, actions ("SELL 95.88 META ≈ $70,639 · 169.52 → 73.64 shares at $736.72"), current → target allocation.
- **Benchmarks** `BenchmarkComparison.jsx`: list/add benchmarks. The comparison note on this tab is stale: the chart's "Compare with" is the live comparison. This tab does not call `/portfolios/calculations/.../benchmark`.
- `AssetAnalyticsView.jsx` / `IndicatorConfigurationManager.jsx` belong to indicators (see `api/v1/statistical_indicators/CLAUDE.md`).
- `analyticsAPI` in `services/api.js`.

## Known gaps / planned
- Point the Benchmarks tab at the shadow comparison (plan 2.7 is done on the chart). Beta should use a total-return index.
- Delete or rebuild the legacy snapshot endpoints on the engine; snapshots should be written by a worker (plan 3.3), not in requests.
- Risk endpoints are slow cold (Yahoo); acceptable for now per user.
- `risk_assessment.reasoning` is HTML from the backend.
