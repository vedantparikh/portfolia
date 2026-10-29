# Technical indicators & analysis configurations

**Purpose:** compute technical indicators for a symbol, chart them, and save named indicator sets per user.

**State (2026-10-28):** ✅ all 17 indicators match the `ta` reference library (`tests/unit/test_indicator_reference.py`); saved configurations drive the chart; private configurations are private.

## Backend — `routers.py` (prefix `/api/v1/statistical-indicators`)
- **Services:** `enhanced_statistical_service.py`, `indicator_registry_service.py`, `analysis_configuration_service.py`. Model: `AnalysisConfiguration` (indicators and chart_settings as JSON, is_public, tags, usage_count).
- **Indicator code:** `python/app/utils/indicators/{momentum,trend,volatility,volume}_indicators.py`, using polars.

| Endpoint | Behaviour |
|---|---|
| `GET /indicators` | Registry, built by introspecting `*_indicator` methods |
| `POST /calculate` | OHLCV plus the requested indicator series; with `configuration_id` the saved set (and its parameters) is used — only the caller's own or a public set. A request with neither `configuration_id` nor `indicators` is a 422 before any market data is fetched |
| `POST/GET /configurations`, `GET/PUT/DELETE /configurations/{id}`, `POST /configurations/{id}/duplicate` | Saved sets: `GET /configurations?user_only=true` = your own, otherwise public ones. A private set is visible only to its owner (anonymous callers see public sets only) |
| `GET /templates`, `POST /templates/{name}/create`, `POST /validate`, `GET /statistics`, `GET /popular` | Templates and helpers. The configuration manager's `ConfigurationLibrary` lists templates (Use = create from template) and popular public sets (Copy = duplicate), with a one-line summary from `/statistics`. `/validate` has no UI |
| `GET /strategies/gfs?symbol=`, `GET /strategies/macd?symbol=&since=` | Rule outputs from `core/domain/strategies.py` on `get_daily_history` closes (split-adjusted, not dividend-adjusted): GFS = RSI(14) of monthly, weekly and daily closes (all < 30 buy, all > 70 sell, else hold, each with its as-of date); MACD = MACD(12,26,9) crosses up below zero with the close above its 200-day EMA (buy) or down above zero below it (sell), default since one year ago. No history → 404; too little (15 months for GFS, 201 days for MACD) → 400. Tests: `tests/unit/test_strategies.py` (RSI equals the chart's after warm-up) |
| `GET /strategies/backtests?symbol=&years=5` | `backtest_all` in `core/domain/strategies.py`: every rule in `STRATEGIES` (gfs, macd, golden_cross 50/200 SMA, trend_200 close vs 200 SMA, rsi_reversion RSI(14) back above 30 / below 70, bollinger_reversion close back inside the 20-day 2σ bands, breakout prior 55-day high / 20-day low) over the last `years` (1–20), long only, one position, buy/sell at the signal day's close, no costs or taxes, an open trade valued at the last close; each rule starts the window flat. Per rule: trades, win rate, average and compounded total return, `vs_holding_pp`, % of sessions invested, `invested` (holds at the last close), the latest signal in the window, or `error` when that rule lacks history (400 only when none can run). Every rule reads only closes up to its signal day (`test_past_signals_only_use_what_each_day_knew` recomputes each from truncated history); past GFS signals use `live_rsi`, where each day's close ends its unfinished month and week. `backtest` locates prices by binary search: all seven over 20 years take ~0.7 s |
| `GET /configurations/search?q=` | Name, description or tags (JSON cast to text) contain `q`; own + public |

**Indicators:**
- Momentum: rsi, roc, stoch_rsi, stoch_oscillator.
- Trend: macd, adx, aroon, psar, cci.
- Volatility: bollinger_bands, average_true_range, keltner_channel.
- Volume: mfi, vpt, vwap, obv, force_index.

**Calculation path** (`EnhancedStatisticalService.calculate_indicators`): `fetch_ticker_data` returns newest-first, so the frame is sorted by date before calculating; for a period like `30d`/`3mo`/`1y`/`ytd` it fetches `WARM_UP_DAYS` (400) more calendar days, calculates on everything and returns only the requested window (`period_start`), so MACD/ADX/Wilder averages are converged on the first visible bar. The registry merges back only each indicator's own output columns (merging the whole frame used to make every second indicator class fail with a duplicate `date` column — silently, so RSI + MACD showed only RSI); calculation errors are logged. End-to-end tests: `tests/unit/test_indicator_service.py`. Live check 2026-10-16: AAPL RSI/MACD/signal on the last closed bar equal `ta` to 1e-8.

**Formulas** (all checked against `ta` after a 150-bar warm-up; Wilder smoothing = `wilder_average` in `utils/indicators/base.py`):
- RSI: Wilder (EMA alpha 1/n). StochRSI: raw = (RSI − min)/(max − min) × 100 as `stoch_rsi`, %K = SMA(raw, 3), %D = SMA(%K, 3).
- MACD: recursive EMAs (`adjust=False`) 12/26/9.
- ADX/+DI/−DI: Wilder (true range and ±DM from bar 2). Aroon: position of the high/low in the last 25+1 bars.
- PSAR: Wilder, step 0.02 / max 0.2, SAR capped at min(prior two lows) — stricter than `ta`, which takes the low two bars back. `psar_up`/`psar_down` are price values (null in the other trend).
- CCI: mean absolute deviation of the typical price from its SMA.
- Bollinger: population std. ATR: Wilder. Keltner (default): EMA(20) ± 2 × ATR(10); `original_version=True` = typical-price SMA bands. `pband` = %B, `wband` = width % of the middle.
- VPT: fractional price change × volume. VWAP: rolling 14 bars. OBV: unchanged on an equal close, starts at 0 (`ta` differs in both; only daily changes are compared).

The old `utils/trading_strategies` were removed (2026-10-29): GFS took daily RSI over 5y/1y/1mo, which is one number past the warm-up, and MACD lost the buy/sell sign. The characterisation snapshot pins indicator outputs, so any formula fix must regenerate it, explained in the commit.

## Frontend
No route of its own; it lives inside `/assets`:
- The asset modal's chart tab uses `features/analytics/IndicatorChart.jsx` (same calculation and indicator picker, no saved sets). An asset card's ⋮ menu → Analytics, or "Open analysis" in the asset modal, in `Assets.jsx` replaces the grid with `features/analytics/AssetAnalyticsView.jsx` ("Back to Assets" returns). It draws on `components/shared/EnhancedChart.jsx` (lightweight-charts v5). Each output is its own series labelled by `utils/indicatorLabels.js` ("MACD signal"); 0/1 flag outputs are not plotted. Each oscillator family (rsi, stoch, cci, roc, williams, momentum, macd, adx, aroon, mfi) gets its own pane (stretch 0.35 vs price 1), RSI fixed 0–100 with 70/30 lines; the rest overlay the price.
- `features/analytics/StrategySignals.jsx` (in `AssetAnalyticsView`): GFS action and the three RSIs, and the last 12 months of MACD signals, labelled as rule output, not advice.
- `features/analytics/StrategyBacktests.jsx` (below it): all seven rules for 1/3/5/10 years (`useStrategyBacktests`) next to holding: latest signal, in/out now, return, vs holding (pp), trades (won), time invested; a row expands to its trades, each rule has its ⓘ guide entry. The chart button on a row marks that rule's trades on the price chart (`strategyMarkers.js`: ▲ buy below the bar, ▼ sell above it, a label only on the latest call, a circle when the latest signal was not traded) and widens the chart to the backtest window. `AssetAnalyticsView` owns the window and the marked rule, so the table and the chart share one query.
- `EnhancedChart` `markers` prop: `[{date: "YYYY-MM-DD", position, shape, color, text}]`, matched to bars by the calendar day the API sent and added after every series (markers created earlier drift when later series add time points). Indicator points (naive dates) are put on their day's bar time; before 2026-10-29 they sat 4–5 h off the bars, so the time scale held two points per day.
- `features/analytics/IndicatorConfigurationManager.jsx` sits in a `Modal` rendered by `Assets.jsx`, opened from "Manage Configurations" in the analytics view, to create, edit, duplicate and select sets. The selected set is passed to `AssetAnalyticsView` as `selectedConfiguration` and calculated by `configuration_id`; the view also lists your saved sets with Apply. Toggling an indicator by hand leaves the set.
- API wrapper: `statisticalIndicatorsAPI` in `js/src/shared/api/indicators.ts` (also used by `EnhancedChart` and `Chart`). Query hooks `useIndicatorConfigurations`, `useAvailableIndicators`, `useIndicatorCalculation` in `features/analytics/queries.ts`, keyed under `["indicators", …]`.

## Workflow
Assets → a symbol → Chart tab (pick indicators), or Open analysis / the card's ⋮ → Analytics → the view loads RSI and MACD (30 days) → "Manage Configurations" to manage sets.

## Known gaps
- The backtest has no costs, taxes, slippage or position sizing, and buys at the same close that produced the signal.

## Planned
Nothing scheduled.
