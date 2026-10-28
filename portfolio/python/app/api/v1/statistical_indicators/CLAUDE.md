# Technical indicators & analysis configurations

**Purpose:** compute technical indicators for a symbol, chart them, and save named indicator sets per user.

**State (2026-10-16):** ✅ all 17 indicators match the `ta` reference library (`tests/unit/test_indicator_reference.py`); saved configurations drive the chart; private configurations are private.

## Backend — `routers.py` (prefix `/api/v1/statistical-indicators`)
- **Services:** `enhanced_statistical_service.py`, `indicator_registry_service.py`, `analysis_configuration_service.py`. Model: `AnalysisConfiguration` (indicators and chart_settings as JSON, is_public, tags, usage_count).
- **Indicator code:** `python/app/utils/indicators/{momentum,trend,volatility,volume}_indicators.py`, using polars.

| Endpoint | Behaviour |
|---|---|
| `GET /indicators` | Registry, built by introspecting `*_indicator` methods |
| `POST /calculate` | OHLCV plus the requested indicator series; with `configuration_id` the saved set (and its parameters) is used — only the caller's own or a public set. A request with neither `configuration_id` nor `indicators` is a 422 before any market data is fetched |
| `POST/GET /configurations`, `GET/PUT/DELETE /configurations/{id}`, `POST /configurations/{id}/duplicate` | Saved sets: `GET /configurations?user_only=true` = your own, otherwise public ones. A private set is visible only to its owner (anonymous callers see public sets only) |
| `GET /templates`, `POST /templates/{name}/create`, `POST /validate`, `GET /statistics`, `GET /popular` | Templates and helpers. No UI for templates, statistics or popular |
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

Strategies in `utils/trading_strategies/{gfs,macd}_strategy.py` are tests only, with no API. The characterisation snapshot pins indicator outputs, so any formula fix must regenerate it, explained in the commit.

## Frontend
No route of its own; it lives inside `/assets`:
- `analytics/AssetAnalyticsView.jsx` draws on `shared/EnhancedChart.jsx` (lightweight-charts v5). Each output is its own series labelled by `utils/indicatorLabels.js` ("MACD signal"); 0/1 flag outputs are not plotted. Each oscillator family (rsi, stoch, cci, roc, williams, momentum, macd, adx, aroon, mfi) gets its own pane (stretch 0.35 vs price 1), RSI fixed 0–100 with 70/30 lines; the rest overlay the price. 
- `analytics/IndicatorConfigurationManager.jsx` is a modal (rendered at page level in `Assets.jsx`, opened from "Manage Configurations" in the analytics view) to create, edit, duplicate and select sets. The selected set is passed to `AssetAnalyticsView` as `selectedConfiguration` and calculated by `configuration_id`; the view also lists your saved sets with Apply. Toggling an indicator by hand leaves the set.
- API wrapper: `statisticalIndicatorsAPI` in `services/api.js`.

## Workflow
Assets → select an asset → the analytics view loads RSI and MACD (30 days) → "Analysis Configurations" to manage sets.

## Known gaps
- No UI for templates, statistics or popular sets.
- A failed router import only logs a warning and the router silently goes unmounted (plan 1.2).
- Trading strategies (`utils/trading_strategies/`) have no API.

## Planned
Plan 1.2 app factory; templates/popular UI if wanted.
