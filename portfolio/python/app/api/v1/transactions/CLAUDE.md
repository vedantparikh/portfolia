# Transactions (+ PDF export)

**Purpose:** record buys, sells and dividends per portfolio; positions are derived from them.

**State (2026-10-28):** ✅ CRUD, oversell protection, position rebuild, summary, PDF export (in the portfolio currency) work. ⚠️ filtering is client-side.

## Backend — `router.py` (prefix `/api/v1/transactions`), `pdf_export_router.py` (prefix `/api/v1/transactions/pdf`)
| Endpoint | Behaviour |
|---|---|
| `POST /`, `GET /?portfolio_id&limit≤10000&offset`, `GET/PUT/DELETE /{id}` | CRUD via `modules/portfolios`. The list is always newest first (`order_by`/`order` sent by the UI are ignored). Each write flushes, runs `recalculate_asset_state` (FIFO + splits, see `core/domain`), then commits. Cash currency rule: see `api/v1/portfolio/CLAUDE.md` |
| `GET /{portfolio_id}/summary?start_date&end_date` | Completed only; cash moved: buys (with fees/taxes), net sell proceeds, dividends, fees, net investment. Matches the performance series' deposits/withdrawals. No UI caller |
| `POST /export`, `/export/download`, `/export/preview` | `core/services/transaction_pdf_export_service.py` (ReportLab). Each row is converted into its portfolio currency (a missing rate leaves it in its own currency); totals are per currency. UI uses preview + download |

Rules:
- `total_amount` is always computed by the server: `Transaction.compute_total_amount`. Buys and transfer-ins are qty×price+fees+taxes. Sells and transfer-outs are qty×price−fees−taxes. Every other type is qty×price. A client-sent total is ignored. An imported dividend is the exception: the statement amount is kept.
- `OversellError` is a `DomainError`, so it maps to 400 (`core/error_handlers.py`).
- Statuses: pending, completed, cancelled, failed. Only completed transactions count anywhere.
- A transfer in opens a lot at its cost (quantity × price + fees + taxes) and a transfer out closes FIFO lots at its proceeds (quantity × price − fees − taxes). Both count in today's P&L and in the performance series like a buy or a sell. Split, fee and the other corporate types are stored and ignored. Splits come from market data.
- Buys, sells, transfers and splits need quantity > 0. Price is never negative. A dividend may have quantity 0: an imported dividend keeps the statement amount, not shares × rate.

## Frontend — `js/src/features/transactions/`
- Route `/transactions` → `Transactions.jsx`:
  - Search, plus `TransactionFilters` (portfolio, type, dates). Filtering happens client-side over `useTransactions()` (`getTransactions(limit 10000)`, query key `["transactions","list"]`).
  - `TransactionCard` rows.
- Modals:
  - `CreateTransactionModal` (amount↔quantity helpers from user input).
  - `EditTransactionModal`.
  - `BulkTransactionModal` (manual bulk, posts to account-statements bulk-create).
  - `TransactionExportModal` (PDF).
  - `PDFUploadModal` + `ParsedDataTable` (see `api/v1/account_statements/CLAUDE.md`).
- `transactionAPI`, `accountStatementsAPI` and `transactionPDFExportAPI` in `js/src/features/transactions/api.ts`; `useTransactions` / `useRecentTransactions` in `features/transactions/queries.ts`. Writes invalidate `["transactions"]` and `["portfolios"]`.

## Workflow
Transactions → New Transaction (pick portfolio + asset via search, buy/sell/dividend, qty, price, fees, date) → position and charts update immediately. Bulk entry or PDF import for many rows. Export → preview → download PDF.

## Known gaps
- `GET /{portfolio_id}/summary` has no UI caller.
- Dividend `taxes` are not netted out of `total_amount` (plan 2.2).

## Planned
Server-side filtering/pagination.
