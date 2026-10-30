# Portfolio performance (series, period metrics)

**Purpose:** how a portfolio performed over an interval relative to the money put in, with returns and risk for that interval.

**State (2026-10-28):** ✅ series, performance, multi-period agree exactly (one `period_summary`). ✅ benchmark comparison as a shadow portfolio (`core/domain/benchmark.py`). `/overview` is a thin wrapper over inception `/performance`.

## Backend — `router.py` (mounted at `/api/v1/portfolios/calculations`), `modules/analytics/calculations.py`
| Endpoint | Behaviour |
|---|---|
| `GET /periods` | Period codes for the Performance Metrics dropdown (3m … inception). `1m` is accepted everywhere but not listed |
| `GET /portfolio/{id}/performance/series?period=` | **Chart source.** `points[]` per trading day: `value`, `invested` (= value at period start + deposits − withdrawals since), `cost_basis` (FIFO), `stale_price` and `stale_symbols` when a holding's close is more than 5 sessions old (the last close is still the value); `summary` = `period_summary`; `error` on missing price/oversell |
| `GET|POST /portfolio/{id}/performance?period=` | `metrics`: twr, mwr (both over the period), cagr (annualised TWR, plain TWR under a year), xirr (annual), volatility, max_drawdown; `current_value`. Switches to inception when the portfolio is younger than the period |
| `GET /portfolio/{id}/multi-period?periods=` | The above for several periods; one memoised engine run per request |
| `GET /benchmarks?currency=` | Suggested total-return benchmarks (`BENCHMARKS` in the service): EUR `EUNL.DE` (default), `VWCE.DE`, `SXR8.DE`, `SXRV.DE`; USD `^SP500TR` |
| `GET /portfolio/{id}/benchmark?period=&symbol=` | Portfolio vs the same flows in `symbol` (default: the portfolio's primary `PortfolioBenchmark`, else the currency default). `points[]` value / benchmark_value / invested, `portfolio` and `shadow` = `period_summary`, `difference` (portfolio − shadow: end_value, profit, twr_pct and mwr_pct in pp), `warnings` (benchmark currency unknown, so unconverted; benchmark paid dividends in the period, i.e. a price index; shadow shortfall), `error` |
| `GET /portfolio/{id}/insight?period=inception` | `core/domain/insight.py` on the memoised breakdown: `contributions[]` per holding (profit, `contribution_pp` summing to `twr_pct`, start/end value, inflow, outflow, `quote_currency` and `currency_effect` for foreign quotes), `months[]`/`years[]` (TWR per calendar period, `benchmark_pct` from the primary benchmark else the currency default, `partial`), `drawdown` (current, max, deepest 5 episodes, daily underwater `points`), `timing` (profit vs the same flows at the steady TWR rate), `currency_effect` (total and per currency, with the period profit for scale), `benchmark` (`note` when it paid dividends its price leaves out, `error` when it has no history; neither fails the rest). Errors as `/performance/series`. ~1 s warm, ~6 s cold for a 2-year demo portfolio |
| `GET /portfolio/{id}/overview` | Inception `/performance` packed into `PortfolioPerformanceOverview` (current value, TWR, CAGR, volatility); per-asset lists and benchmark empty. No UI caller |

Engine path: `get_transactions` (completed) → `get_market_history` (closes + splits + listing currency via `MarketDataService.get_daily_history`) → `load_rates` → `convert_closes` / `to_trades` + `convert_trades` into the portfolio currency → `daily_series` → `period_summary`. Memoised in `_series_cache` per service instance. First call for a portfolio fetches max history per symbol (~1–2 s each, cached 6 h in Redis).

## Frontend
- **Performance Chart** view: `js/src/features/portfolio/PortfolioChart.jsx` — period pills 1M…All, StatCards (Value, Profit, Return TWR, Return money-weighted), `PerformanceSeriesChart` (lightweight-charts: Value area, Invested line, optional Cost basis; an amber note when the hovered day is `stale_price`), Risk card (drawdown, volatility, Sharpe, best/worst day), Money in and out card.
- `ValueVsInvestedChart.jsx` (Holdings Detail) and dashboard sparklines (`period=3m`) read the same series. The analytics period select also uses `/periods` (`useCalculationPeriods`).
- **Performance Metrics** view: `PortfolioPerformanceMetrics.jsx` — `/periods`, `/performance` + `/multi-period`; tiles labelled "this period" / "per year"; MWR-vs-TWR timing insight; a note points to the benchmark comparison.
- **Benchmark**: in the Performance Chart view, "Compare with" (suggested options for the portfolio currency, or any Yahoo ticker) adds a purple "Same money in X" line to `PerformanceSeriesChart` and a "Versus …" card (You / benchmark / Difference for value, profit, TWR, money-weighted) with the backend warnings.
- **Performance Insight** view (lightbulb): `js/src/features/portfolio/PortfolioInsight.jsx` (`usePerformanceInsight`) — period pills YTD/1Y/3Y/5Y/All; StatCards return, timing effect, currency effect, below the peak today; "What drove the return" (profit and pp per holding, a centred bar per holding; collapsed to the top 7 and bottom 3 when there are more than 10); a monthly heatmap with year, benchmark and difference columns (* = partial); `UnderwaterChart` plus the drawdown episodes; timing and currency cards. Each has an ⓘ guide entry (`contribution`, `calendar_returns`, `drawdown_recovery`, `timing_effect`, `currency_effect`).
- `portfolioCalculationsAPI` in `js/src/features/portfolio/api.ts`.

## Workflow
Portfolio → Performance Chart → pick a period → read profit vs invested and the period's return/risk; Performance Metrics for side-by-side periods.

## Known gaps / planned
- A benchmark in another currency is converted with the same Yahoo daily rate as holdings before `shadow_series`. Unknown currency is still compared unconverted, with a warning. History is cached 6 h.
- Fill or drop the empty parts of `/overview`. Old helpers `_calculate_xirr`, `_calculate_cagr`, `_get_portfolio_value_at_date`, `get_current_portfolio_value` are legacy; `test_calculation_snapshots.py` still pins some of them.
- Dividend tax (2.2) is not netted out of a manually entered dividend.
