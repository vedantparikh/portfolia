# Market data

`core/services/market_data_service.py` is the only code that calls Yahoo (yfinance and yahooquery). Tests mock it and do not open the network.

| Method | Used for | Redis TTL |
|---|---|---|
| `get_current_prices` | Holdings and summaries. `regularMarketPrice`, then `currentPrice`, then `previousClose` | 60 s |
| `get_yesterdays_closes` | Today's P&L. `yf.download` over 2 days, first row | 12 h |
| `get_daily_history` | Valuation. Closes are split-adjusted and not dividend-adjusted (`auto_adjust=False`), plus split and dividend events | 6 h |
| `fetch_ticker_data` | Charts, indicators, benchmark history. Dividend-adjusted by default | none |
| `get_ticker_info` | Asset detail | 15 min |
| `search_symbols` | Exact ticker lookup | — |
| `get_market_status` | Dashboard tile. Weekdays 09:30–16:00 America/New_York. Holidays are not special | — |
| `search_listings`, `get_daily_ranges` | ISIN → listing matcher for imports | search 7 d, ranges 1 d |

## HTTP

Two routers, documented in [../api/v1/market/CLAUDE.md](../api/v1/market/CLAUDE.md):

- `/api/v1/stock` — symbol search (yahooquery, optional auth, 10/hour/IP if anonymous) and the quote the transaction form uses
- `/api/v1/market-data` — ticker, bulk prices (max 50), market status, supported periods and intervals. Auth required. `/search` here is an exact-ticker lookup and has no UI

Symbol search also exists on the assets router. New UI should not add a fourth client.

## Rules that affect numbers

- Valuation must use `get_daily_history`, not the dividend-adjusted chart series. Dividends are cash transactions.
- A holding with no close raises `MissingPriceError`. Callers leave the value null. They do not fall back to cost.
- There is no concurrency limit and no backoff. A cold portfolio with many symbols is slow because each history fetch is a Yahoo call.
- No FX. EURUSD and similar pairs are not fetched.

The worker refreshes watchlist quotes through `get_current_prices`. It does not refresh holdings.
