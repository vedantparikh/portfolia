# Technical indicators

Computed in `python/app/utils/indicators/`, served by `/api/v1/statistical-indicators`, drawn on the Asset Analysis chart. The feature reference, including endpoints and the UI, is [../api/v1/statistical_indicators/CLAUDE.md](../api/v1/statistical_indicators/CLAUDE.md).

All 17 indicators match the `ta` library after a 150-bar warm-up (`tests/unit/test_indicator_reference.py`). A period such as `30d` fetches about 400 extra calendar days, calculates on the whole frame, and returns only the requested window, so the first visible bar is already converged.

Data from Yahoo arrives newest-first and is sorted before calculation. Each indicator's own columns are merged back. A failure in one indicator is logged rather than dropping the rest of the response.

## Formulas

Wilder smoothing is `wilder_average` in `utils/indicators/base.py`.

| Indicator | Definition used here |
|---|---|
| RSI | Wilder, EMA alpha 1/n |
| Stochastic RSI | raw `(RSI − min) / (max − min) × 100`, then %K = SMA 3, %D = SMA of %K |
| MACD | EMAs 12/26/9, `adjust=False` |
| ADX, +DI, −DI | Wilder, true range and ±DM from bar 2 |
| Aroon | Position of the high and low in the last 26 bars |
| PSAR | Wilder, step 0.02, max 0.2, capped at the min of the prior two lows |
| CCI | Mean absolute deviation of typical price from its SMA |
| Bollinger Bands | Population standard deviation. `pband` is %B, `wband` is width as a percent of the middle |
| ATR | Wilder |
| Keltner | EMA(20) ± 2 × ATR(10). `original_version=True` uses typical-price SMA bands |
| VPT | Fractional price change × volume |
| VWAP | Rolling 14 bars |
| OBV | Flat on an equal close, starts at 0. `ta` differs; tests compare daily changes |
| Force index, ROC, stochastic oscillator, MFI | As in `ta` |

## Saved sets

`POST /configurations` stores a name, the indicator list with parameters, and chart settings. `POST /calculate` with `configuration_id` uses that set. A private set is readable only by its owner. Templates, statistics, and popular-sets routes exist and have no UI.

The MACD and GFS strategy modules under `utils/trading_strategies/` are imported by tests. They have no route.
