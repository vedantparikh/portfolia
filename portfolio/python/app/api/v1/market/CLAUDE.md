# Market data

**Purpose:** quotes, price history, corporate actions and symbol search from Yahoo, cached in Redis. The **only** path to market data (tests mock the provider, never the network).

**State (2026-10-27):** ✅ one Yahoo provider. The worker refreshes holding prices, previous closes, daily history and FX. Holdings read the price cache and do not call Yahoo. Symbol search, an explicit quote, and a cold history or FX cache still do.

## Provider — `core/services/market_data/`
`MarketDataProvider` is the only Yahoo surface. `YahooMarketDataProvider` runs every call through one semaphore (4 at a time) and retries twice with exponential backoff (0.5s, 1s). `MarketDataService` caches in front of it. Batch price, close and profile writes use one Redis pipeline (`mset`).

## Service — `core/services/market_data_service.py`
| Method | Use | Cache |
|---|---|---|
| `get_current_prices(symbols)` | Live price (regularMarketPrice → currentPrice → previousClose) for holdings/summary | Redis 60 s, one pipeline write |
| `get_yesterdays_closes(symbols)` | Previous close for today's P&L: last session before the current one, in the bar's timezone (`auto_adjust=False`, 10 days) | 12 h, keyed by the UTC date |
| `get_daily_history(symbol)` | **Valuation source**: closes split-adjusted, *not* dividend-adjusted (`auto_adjust=False`), plus `splits` and `dividends` on ex-dates; naive date index | 6 h |
| `fetch_ticker_data(...)` | OHLCV (dividend-adjusted default) for charts/indicators/benchmark | none |
| `search_quotes` / `search_listings` | One Yahoo search. The UI gets every quote; the ISIN resolver keeps equities, ETFs, funds and crypto | 7 d |
| `get_ticker_info`, `get_market_status` | Info (15 min, one pipeline write), US market open (weekdays 9:30–16:00 ET, no holidays) | |

## Endpoints (`market/routers.py`)
- `stock.py` (`/api/v1/stock`):
  - `GET /symbols` — the only symbol search (Yahoo via the provider); optional auth; anonymous users limited to 10/hour per IP. Used by SymbolSearch and AddSymbolModal.
  - `GET /symbol-data`
  - `GET /stock-latest-data` — used by the transaction modal and ClientSideAssetSearch.
  - `GET /major-indices` — a static list.
- `data_router.py` (`/api/v1/market-data`, auth required):
  - `GET /ticker/{symbol}`, `GET /ticker/{symbol}/info`
  - `GET /prices/bulk` (max 50)
  - `GET /market-status` — Dashboard tile.
  - `GET /supported-periods`, `GET /supported-intervals`
- `marketAPI` in `js/src/services/api.js`.

## Known gaps
- Unused client fns `getMajorIndices`, `getBulkPrices`, `getTickerInfo`, `getTickerData`.
- Market status ignores US holidays.
- A cold daily-history or FX cache still calls Yahoo inside the request. The worker fills those for symbols the book already holds.
