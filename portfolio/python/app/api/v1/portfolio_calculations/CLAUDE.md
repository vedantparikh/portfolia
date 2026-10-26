# Portfolio performance (series, period metrics)

**Purpose:** how a portfolio performed over an interval relative to the money put in, with returns and risk for that interval.

**State (2026-10-16):** ✅ series, performance, multi-period agree exactly (one `period_summary`). ✅ benchmark comparison as a shadow portfolio (`core/domain/benchmark.py`). `/overview` is a thin wrapper over inception `/performance`.

## Backend — `router.py` (mounted at `/api/v1/portfolios/calculations`), `core/services/portfolio_calculation_service.py`
| Endpoint | Behaviour |
|---|---|
| `GET /periods` | Period codes for the Performance Metrics dropdown (3m … inception). `1m` is accepted everywhere but not listed |
| `GET /portfolio/{id}/performance/series?period=` | **Chart source.** `points[]` per trading day: `value`, `invested` (= value at period start + deposits − withdrawals since), `cost_basis` (FIFO); `summary` = `period_summary`; `error` on missing price/oversell |
| `GET|POST /portfolio/{id}/performance?period=` | `metrics`: twr, mwr (both over the period), cagr (annualised TWR, plain TWR under a year), xirr (annual), volatility, max_drawdown; `current_value`. Switches to inception when the portfolio is younger than the period |
| `GET /portfolio/{id}/multi-period?periods=` | The above for several periods; one memoised engine run per request |
| `GET /benchmarks?currency=` | Suggested total-return benchmarks (`BENCHMARKS` in the service): EUR `EUNL.DE` (default), `VWCE.DE`, `SXR8.DE`, `SXRV.DE`; USD `^SP500TR` |
| `GET /portfolio/{id}/benchmark?period=&symbol=` | Portfolio vs the same flows in `symbol` (default: the portfolio's primary `PortfolioBenchmark`, else the currency default). `points[]` value / benchmark_value / invested, `portfolio` and `shadow` = `period_summary`, `difference` (portfolio − shadow: end_value, profit, twr_pct and mwr_pct in pp), `warnings` (benchmark currency unknown, so unconverted; benchmark paid dividends in the period, i.e. a price index; shadow shortfall), `error` |
| `GET /portfolio/{id}/overview` | Inception `/performance` packed into `PortfolioPerformanceOverview` (current value, TWR, CAGR, volatility); per-asset lists and benchmark empty. No UI caller |

Engine path: `get_transactions` (completed) → `get_market_history` (closes + splits via `MarketDataService.get_daily_history`) → `to_trades` → `daily_series` → `period_summary`. Memoised in `_series_cache` per service instance. First call for a portfolio fetches max history per symbol (~1–2 s each, cached 6 h in Redis).

## Frontend
- **Performance Chart** view: `js/src/components/portfolio/PortfolioChart.jsx` — period pills 1M…All, StatCards (Value, Profit, Return TWR, Return money-weighted), `PerformanceSeriesChart` (lightweight-charts: Value area, Invested line, optional Cost basis), Risk card (drawdown, volatility, Sharpe, best/worst day), Money in and out card.
- `ValueVsInvestedChart.jsx` (Holdings Detail) and dashboard sparklines (`period=3m`) read the same series.
- **Performance Metrics** view: `PortfolioPerformanceMetrics.jsx` — `/performance` + `/multi-period`; tiles labelled "this period" / "per year"; MWR-vs-TWR timing insight; a note points to the benchmark comparison.
- **Benchmark**: in the Performance Chart view, "Compare with" (suggested options for the portfolio currency, or any Yahoo ticker) adds a purple "Same money in X" line to `PerformanceSeriesChart` and a "Versus …" card (You / benchmark / Difference for value, profit, TWR, money-weighted) with the backend warnings.
- `portfolioCalculationsAPI` in `services/api.js`.

## Workflow
Portfolio → Performance Chart → pick a period → read profit vs invested and the period's return/risk; Performance Metrics for side-by-side periods.

## Known gaps / planned
- A benchmark in another currency is converted with the same Yahoo daily rate as holdings before `shadow_series`. Unknown currency is still compared unconverted, with a warning. History is cached 6 h.
- Fill or drop the empty parts of `/overview`. Old helpers `_calculate_xirr`, `_calculate_cagr`, `_get_portfolio_value_at_date`, `get_current_portfolio_value` are legacy; `test_calculation_snapshots.py` still pins some of them.
- Dividend tax (2.2) still affects imported cash. FX is applied in `get_portfolio_series`.
