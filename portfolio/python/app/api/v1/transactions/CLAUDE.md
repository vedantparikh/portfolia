# Transactions (+ PDF export)

**Purpose:** record buys, sells and dividends per portfolio; positions are derived from them.

**State (2026-10-16):** ✅ CRUD, oversell protection, position rebuild, summary, PDF export work. ⚠️ some dead client code and currency gaps.

## Backend — `router.py` (prefix `/api/v1/transactions`), `pdf_export_router.py`
| Endpoint | Behaviour |
|---|---|
| `POST /`, `GET /?portfolio_id&limit≤10000&skip`, `GET/PUT/DELETE /{id}` | CRUD via `portfolio_service.py`. Each write flushes, runs `recalculate_asset_state` (FIFO + splits, see `core/domain`), then commits |
| `GET /{portfolio_id}/summary?start_date&end_date` | Completed only; cash moved: buys (with fees/taxes), net sell proceeds, dividends, fees, net investment. Matches the performance series' deposits/withdrawals. No UI caller |
| `POST /transactions/pdf/export`, `/export/download`, `/export/preview` | `core/services/transaction_pdf_export_service.py` (ReportLab). UI uses preview + download |

Rules:
- `total_amount` is always computed by the server: `Transaction.compute_total_amount`. BUY is qty×price+fees+taxes, SELL is qty×price−fees−taxes, and every other type is qty×price. A client-sent total is ignored.
- `OversellError` maps to 400 (handler in `main.py`).
- Statuses: pending, completed, cancelled, failed. Only completed transactions count anywhere.
- Types beyond buy/sell/dividend (split, transfer, fee, …) are stored but ignored by the maths. Splits come from market data.

## Frontend — `js/src/components/transactions/`
- Route `/transactions` → `Transactions.jsx`:
  - Search, plus `TransactionFilters` (portfolio, type, dates). Filtering happens client-side over `getTransactions(limit 10000)`.
  - `TransactionCard` rows.
- Modals:
  - `CreateTransactionModal` (amount↔quantity helpers from user input).
  - `EditTransactionModal`.
  - `BulkTransactionModal` (manual bulk, posts to account-statements bulk-create).
  - `TransactionExportModal` (PDF).
  - `PDFUploadModal` + `ParsedDataTable` (see `api/v1/account_statements/CLAUDE.md`).
- `transactionAPI` and `transactionPDFExportAPI` in `services/api.js`.

## Workflow
Transactions → New Transaction (pick portfolio + asset via search, buy/sell/dividend, qty, price, fees, date) → position and charts update immediately. Bulk entry or PDF import for many rows. Export → preview → download PDF.

## Known gaps
- `transactionAPI.bulkCreateTransactions` targets a nonexistent `/transactions/bulk-create` (dead).
- Bulk-create toasts use `summary.total_created` and say nothing was created when that is 0.
- PDF export hard-codes `$`; currency defaults to USD and is never converted (plan 2.3, 3.5).
- Dividend `taxes` are not netted out of `total_amount` (plan 2.2).

## Planned
Plan 2.1 (schema validation per type, TRANSFER_IN/OUT lots), 2.2, 2.3, 3.5 (export in portfolio currency), server-side filtering/pagination.
