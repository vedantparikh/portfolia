# Portfolios (CRUD, positions, holdings, summary)

**Purpose:** a user's portfolios, the positions in them and their live value / P&L.

**State (2026-10-28):** ✅ core flows work and agree with each other. A portfolio may hold listings in other currencies; prices and cash are converted (see FX in `core/domain/CLAUDE.md`). Numbers come from `core/domain` (see `core/domain/CLAUDE.md`).

## Backend — `router.py` (prefix `/api/v1/portfolios`), `modules/portfolios/service.py`
| Endpoint | Behaviour |
|---|---|
| `POST/GET /`, `GET/PUT/DELETE /{id}`, `DELETE /{id}/hard` | CRUD; delete is soft (is_active) unless `/hard` |
| `GET /{id}/holdings` | Live holdings from the price cache the worker fills (`get_current_prices(fetch=False)`, no Yahoo call): quantity (today's share units), cost basis (FIFO+fees), `current_price`, `current_value`, unrealized, today's P&L (`day_change`), realized, `weight_percent`. No price → value fields null. Includes fully sold assets (qty 0) for realized P&L |
| `GET /{id}/summary` | Sum of the same holding rows (open positions only): value, cost, unrealized (priced positions only), today's P&L / % on start-of-day value + cash invested today, `total_realized_pnl`, `missing_prices` |
| `GET /statistics/overview` | Same rows across active portfolios, summed **per currency** in `totals[]` (value, holdings, today's P&L/%); `total_value`/`currency`/`today_pnl` only when all portfolios share one currency; missing prices. Dashboard "Total Value" tile |
| `POST /{id}/refresh` | Rebuilds every position from transactions (picks up new splits) and re-prices |
| `POST/GET /{id}/assets`, `GET /{id}/assets/details`, `DELETE /{id}/assets/{asset_id}`, `POST /{id}/assets/legacy` | `POST` and legacy `POST` add a holding by creating a buy. `DELETE` removes the holding and its transactions. There is no update: quantity and P&L are not writable |
| `POST/GET /{id}/transactions` | Portfolio-scoped transaction create/list (`limit` ≤ 1000, `offset`; newest first; create triggers `recalculate_asset_state`) |
| `GET /sync/pytr` | Whether this user may link a portfolio to the Trade Republic export (`PYTR_SYNC_USERS`), and the file's time |
| `GET/PUT/POST /{id}/sync`, `POST /{id}/sync/instruments` | Broker sync (`modules/broker_sync`): status and last report; `PUT {source: "pytr"\|null}` links (EUR portfolios only) and imports at once, or unlinks; `POST` imports now; `instruments {isin, symbol}` gives a trade-priced ISIN a Yahoo ticker (rebuilds it on market prices) |
| `GET /search?search_term=&currency=`, `GET /public/discover` | Own portfolios by name/currency; discover lists public portfolios. No UI for either |

`PortfolioAsset` is a **cache** rebuilt by `recalculate_asset_state(portfolio_id, asset_id)` on every transaction write and on refresh: `compute_position` on FX-converted trades + live price converted the same way. Holding rows (`_holding_rows`) read the cached price and the previous close `get_yesterdays_closes` (last finished session, 12h, UTC-date key), both multiplied by the FX rate on that day.

Cash currency on create (`add_transaction`): the portfolio currency when the listing or the request is already in it, otherwise the listing's currency (converted at valuation).

## Trade Republic sync (`modules/broker_sync/service.py`)
Bachat logs in to Trade Republic with pytr and keeps `trade-republic/output/account_transactions.csv` fresh; compose mounts that folder read only at `/pytr` (`PYTR_EXPORT_PATH`). Portfolia never logs in itself (ADR 0007). A linked portfolio is re-imported by the worker when the file's SHA-256 changes, and on Sync now:
- The pytr parser reads every row; bulk-create skips rows whose `source_key` is stored, so a run only adds new rows. Splits and swaps are skipped; the listing's Yahoo split ratios restate the older trades (Beyond Meat 1:30, Lucid 1:10).
- ISIN → asset: the user's asset with that ISIN; else the same name as a mapped ISIN in the file (an ISIN that changed in a swap, e.g. Lucid's sell after its reverse split); else a resolver match of status existing/matched. Anything else (knock-outs, warrants) becomes an asset with `price_source="trades"`: symbol = ISIN, valued from its own fills (`core/services/trade_prices.py`; the last fill is carried forward and flagged stale after 5 sessions), listed in `sync_report.trade_priced`.
- Knock-out redemptions: pytr writes a "Tilgung" as a Dividend row for the whole position. When the ISIN is absent from Trade Republic's current positions (`portfolio.csv` beside the export) and that row's shares equal the open quantity, the sync books a sale of all shares at the redeemed amount (often a few cents or 0) instead, so the loss is realised that day (`sync_report.redeemed`). Without `portfolio.csv` nothing is treated as redeemed.
- `portfolios.sync_source`, `synced_at`, `sync_digest`, `sync_report` (migration `e5b2c8d40a17`). A failed batch is rolled back and retried next pass.

## Frontend — `js/src/features/portfolio/`
- Route `/portfolio` → `Portfolio.jsx`: header, portfolio selector, five views (icon buttons):
  1. **Overview** — `PortfolioCard` + recent transactions.
  2. **Holdings Detail** — `PortfolioDetail.jsx`: KPI strip (summary), sortable holdings table (footer = summary totals), `AllocationDonut` (allocation analysis), `ValueVsInvestedChart`; tabs Analytics / Allocations / Rebalancing / Benchmarks (see `api/v1/analytics/CLAUDE.md`).
  3. **Portfolio Assets** — `PortfolioAssets.jsx` cards (`PortfolioAssetCard`), highlights (`StatCard`), filters; enriched with `/assets?include_detail` for sector/market cap/24h.
  4. **Performance Chart** — `PortfolioChart.jsx` (see `api/v1/portfolio_calculations/CLAUDE.md`).
  5. **Performance Metrics** — `PortfolioPerformanceMetrics.jsx`.
- Modals: `CreatePortfolioModal`, `EditPortfolioModal`. Both offer "Keep in sync with Trade Republic" when `GET /sync/pytr` says so (create makes the portfolio EUR). `PortfolioSyncBar` above a linked portfolio shows the last import, Sync now, and a ticker field per trade-priced ISIN.
- `portfolioAPI` and `portfolioCalculationsAPI` in `js/src/features/portfolio/api.ts`; query hooks (`usePortfolios`, `usePortfolioAccountSummary`, `useRecentPortfolioTransactions`, `useCalculationPeriods`) in `features/portfolio/queries.ts`, all under `["portfolios", …]`. Views are wrapped in `CurrencyProvider` with the selected portfolio's currency.

## Workflow
Create portfolio → add transactions (Transactions page, PDF import, or Add Position) → positions rebuild automatically → Holdings Detail shows live value; Refresh rebuilds/re-prices.

## Known gaps
- Delete flows have no undo; holdings include zero-quantity rows in the table.
- A cold daily-history or FX cache (a newly added symbol or pair) still fetches from Yahoo inside the request until the worker has run.
- `GET /search`, `GET /public/discover` and `GET /{id}/assets/details` have no UI caller.

## Planned
Nothing scheduled.
