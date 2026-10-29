# Portfolios (CRUD, positions, holdings, summary)

**Purpose:** a user's portfolios, the positions in them and their live value / P&L.

**State (2026-10-29):** ✅ core flows work and agree with each other. A portfolio may hold listings in other currencies; prices and cash are converted (see FX in `core/domain/CLAUDE.md`). Numbers come from `core/domain` (see `core/domain/CLAUDE.md`).

## Backend — `router.py` (prefix `/api/v1/portfolios`), `modules/portfolios/service.py`
| Endpoint | Behaviour |
|---|---|
| `POST/GET /`, `GET/PUT/DELETE /{id}`, `DELETE /{id}/hard` | CRUD; delete is soft (is_active) unless `/hard` |
| `GET /{id}/holdings` | Live holdings from the price cache the worker fills (`get_current_prices(fetch=False)`, no Yahoo call): quantity (today's share units), cost basis (FIFO+fees), `current_price`, `current_value`, unrealized, today's P&L (`day_change`), realized, `weight_percent`. No price → value fields null. Includes fully sold assets (qty 0) for realized P&L |
| `GET /{id}/summary` | Sum of the same holding rows (open positions only): value, cost, unrealized (priced positions only), today's P&L / % on start-of-day value + cash invested today, `total_realized_pnl` (sales, before tax), `missing_prices`. Tax view: `total_dividends` (before tax), `taxes_withheld` (`transactions.taxes` on sales and dividends), `tax_adjustments` (`tax_entries`: refunds negative), `net_taxes_paid` = withheld + adjustments, `realized_after_tax` = realized + dividends − net taxes. All converted to the portfolio currency |
| `GET /statistics/overview` | Same rows across active portfolios, summed **per currency** in `totals[]` (value, holdings, today's P&L/%); `total_value`/`currency`/`today_pnl` only when all portfolios share one currency; missing prices. Dashboard "Total Value" tile |
| `POST /{id}/refresh` | Rebuilds every position from transactions (picks up new splits) and re-prices |
| `POST/GET /{id}/assets`, `DELETE /{id}/assets/{asset_id}`, `POST /{id}/assets/legacy` | `POST` and legacy `POST` add a holding by creating a buy. `DELETE` removes the holding and its transactions. There is no update: quantity and P&L are not writable |
| `POST/GET /{id}/transactions` | Portfolio-scoped transaction create/list (`limit` ≤ 1000, `offset`; newest first; create triggers `recalculate_asset_state`) |
| `GET /sync/pytr` | Whether this user may link a portfolio to the Trade Republic export (`PYTR_SYNC_USERS`), the file's time, the login (`connected`, `login_pending`, `session_expired`) and the last fetch (`fetch_status`, `fetch_report`) |
| `POST /sync/pytr/login` `{phone, pin}`, `POST /sync/pytr/login/confirm` `{code?}`, `DELETE /sync/pytr/login` | pytr web login: confirm in the Trade Republic app (poll confirm until `confirmed`) or send the authenticator code. PIN never stored; session Fernet-encrypted in `broker_connections` |
| `POST /sync/pytr/fetch` | 202; downloads into the shared folder after the response, then imports into every linked portfolio of the user; poll `GET /sync/pytr` |
| `GET/PUT/POST /{id}/sync`, `POST /{id}/sync/instruments` | Broker sync (`modules/broker_sync`): status and last report; `PUT {source: "pytr"\|null}` links (EUR portfolios only) and imports at once, or unlinks; `POST` imports now; `instruments {isin, symbol}` gives a trade-priced ISIN a Yahoo ticker (rebuilds it on market prices) |

`PortfolioAsset` is a **cache** rebuilt by `recalculate_asset_state(portfolio_id, asset_id)` on every transaction write and on refresh: `compute_position` on FX-converted trades + live price converted the same way. Holding rows (`_holding_rows`) read the cached price and the previous close `get_yesterdays_closes` (last finished session, 12h, UTC-date key), both multiplied by the FX rate on that day.

Cash currency on create (`add_transaction`): the portfolio currency when the listing or the request is already in it, otherwise the listing's currency (converted at valuation).

## Trade Republic sync (`modules/broker_sync/service.py`)
Bachat and Portfolia both log in to Trade Republic with pytr and write `trade-republic/output/account_transactions.csv` (ADR 0008); compose mounts that folder at `/pytr` (`PYTR_EXPORT_PATH`), read-write only on `api`. "Fetch from Trade Republic" (`modules/broker_sync/fetch.py`, client `trade_republic.py`, the same calls as Bachat's connector) downloads and then imports. A linked portfolio is also re-imported by the worker when the file's SHA-256 changes, and on Import file:
- The pytr parser reads every row; bulk-create skips rows whose `source_key` is stored, so a run only adds new rows. Splits and swaps are skipped; the listing's Yahoo split ratios restate the older trades (Beyond Meat 1:30, Lucid 1:10).
- ISIN → asset: the user's asset with that ISIN; else the same name as a mapped ISIN in the file (an ISIN that changed in a swap, e.g. Lucid's sell after its reverse split); else a resolver match of status existing/matched. Anything else (knock-outs, warrants) becomes an asset with `price_source="trades"`: symbol = ISIN, valued from its own fills (`core/services/trade_prices.py`; the last fill is carried forward and flagged stale after 5 sessions), listed in `sync_report.trade_priced`.
- Knock-out redemptions: pytr writes a "Tilgung" as a Dividend row for the whole position. When the ISIN is absent from Trade Republic's current positions (`portfolio.csv` beside the export) and that row's shares equal the open quantity, the sync books a sale of all shares at the redeemed amount (often a few cents or 0) instead, so the loss is realised that day (`sync_report.redeemed`). Without `portfolio.csv` nothing is treated as redeemed.
- Tax rows: Trade Republic withholds tax per sale and later refunds part of it when losses are offset ("Tax Refund" / Steuerkorrektur, account level, no ISIN); Vorabpauschale comes as "Taxes" rows. Both become `tax_entries` (amount positive = paid, negative = refunded; source key per row, migration `f1c4d7a92b36`), counted in `sync_report.tax_entries_created`. Tax on cash interest is not imported (interest is not in the portfolio), so a refund that offsets interest tax makes net taxes slightly low.
- `portfolios.sync_source`, `synced_at`, `sync_digest`, `sync_report` (migration `e5b2c8d40a17`). A failed batch is rolled back and retried next pass.

## Frontend — `js/src/features/portfolio/`
- Route `/portfolio` → `Portfolio.jsx`: header, portfolio selector, five views (icon buttons):
  1. **Overview** — `PortfolioCard` + recent transactions.
  2. **Holdings Detail** — `PortfolioDetail.jsx`: KPI strips (summary: value/invested/unrealized/today; realized before tax/dividends/taxes paid/realized after tax), sortable holdings table (footer = summary totals), `AllocationDonut` (allocation analysis), `ValueVsInvestedChart`; tabs Analytics / Allocations / Rebalancing / Benchmarks (see `api/v1/analytics/CLAUDE.md`).
  3. **Portfolio Assets** — `PortfolioAssets.jsx` cards (`PortfolioAssetCard`), highlights (`StatCard`), filters; enriched with `/assets?include_detail` for sector/market cap/24h.
  4. **Performance Chart** — `PortfolioChart.jsx` (see `api/v1/portfolio_calculations/CLAUDE.md`).
  5. **Performance Metrics** — `PortfolioPerformanceMetrics.jsx`.
- Modals: `CreatePortfolioModal`, `EditPortfolioModal`. Both offer "Keep in sync with Trade Republic" when `GET /sync/pytr` says so (create makes the portfolio EUR). `PortfolioSyncBar` above a linked portfolio shows the last import, Import file (re-read the shared file), a ticker field per trade-priced ISIN, and `TradeRepublicFetch`: Fetch from Trade Republic, with phone + PIN and app confirmation (or code) when there is no session, polling while a fetch runs.
- `portfolioAPI` and `portfolioCalculationsAPI` in `js/src/features/portfolio/api.ts`; query hooks (`usePortfolios`, `usePortfolioAccountSummary`, `useRecentPortfolioTransactions`, `useCalculationPeriods`) in `features/portfolio/queries.ts`, all under `["portfolios", …]`. Views are wrapped in `CurrencyProvider` with the selected portfolio's currency.

## Workflow
Create portfolio → add transactions (Transactions page, PDF import, or Add Position) → positions rebuild automatically → Holdings Detail shows live value; Refresh rebuilds/re-prices.

## Known gaps
- Delete flows have no undo; holdings include zero-quantity rows in the table.
- A cold daily-history or FX cache (a newly added symbol or pair) still fetches from Yahoo inside the request until the worker has run.

## Planned
Nothing scheduled.
