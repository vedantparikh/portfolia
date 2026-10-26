# Broker statement import (PDF)

**Purpose:** turn a broker PDF into reviewed transactions and create them in one atomic batch.

**State (2026-10-16):** ✅ pytr CSV: parse, ISIN → listing matching in the review table, assets created on import (checked in the browser with a real 939-row export; not yet saved into a real portfolio). Trade Republic PDF: trades, savings plans and dividends import in EUR; cash rows are listed as skipped. Tested on synthetic statement text only; a real PDF check is open (the text-layout assumptions in `_extract_transactions` are unverified). Re-importing a file skips rows already in the portfolio. Not exercised by the demo data.

## Backend — `router.py` (prefix `/api/v1/account-statements`), `core/services/account_statement_service.py`, `core/services/parsers/`
| Endpoint | Behaviour |
|---|---|
| `GET /providers` | Supported parsers: Trade Republic (`parsers/trade_republic.py`), Portfolia's own export (`parsers/portfolia.py`) |
| `POST /parse` (multipart `provider_id`, `file`) | Parsed rows for review (no DB writes), plus `skipped[]` and `instruments[]` (one per ISIN with its buy/sell fills) |
| `POST /instruments/resolve` | ≤ 10 instruments → suggested Yahoo listing per ISIN (`isin_resolver.py`). Slow uncached (~3 s per ISIN, Yahoo); cached in Redis (search 7 d, ranges 1 d) |
| `POST /transactions/imported` | `{portfolio_id, transactions: [{source_key, transaction_date, transaction_type, isin, quantity, total_amount}]}` → `imported_keys`: the rows bulk-create would skip as already imported |
| `POST /transactions/bulk-create` | Atomic: insert all rows, recalculate each affected asset, one commit. A row gives `asset_id`, or `symbol` (+ `isin`): the user's asset with that ticker is used or created from Yahoo info (once per ticker), and the ISIN is stored on the asset so the next import maps it directly. A given `total_amount` within 1 cent of qty × price ± fees/taxes is kept as the exact cash. Rows with a `source_key` already in the portfolio (or repeated in the request) are skipped and counted in `summary.total_skipped`. Also used by the manual Bulk Entry modal (no keys, never skipped) |

## Frontend
`PDFUploadModal` (provider + file; accepted extensions come from the provider's `supported_formats`) → `ParsedDataTable` (map symbols to assets, inline edits, draft saved in localStorage, choose portfolio) → bulk-create. `accountStatementsAPI` in `services/api.js`.
- When the parse result has `instruments`, `InstrumentMappingPanel` resolves them 10 at a time and shows one line per ISIN: status (Your asset / Matched / Check / No match) with match %, a listing dropdown (venue, currency, % of fills), a free ticker field and an Import checkbox. Defaults: matched/existing/uncertain are included with the suggestion; unmatched are left out. Once a portfolio is selected, an included listing in another currency is flagged in red and saving is blocked until it is changed or left out.
- A choice applies to every row of that ISIN (rows keep `isin`), unless a row's asset was picked by hand (`manual`). Left-out rows are dimmed and not sent; new tickers show a "new" badge and are sent as `symbol` + `isin`. The mapping is part of the localStorage draft (`parsedImportInstrumentMapping`).
- Amounts are shown in each row's currency.
- Once a portfolio is selected the table asks `/transactions/imported`; rows already there get an "imported" badge, are dimmed, left out of the import count and never sent. A banner says how many (or that there is nothing new). After saving, skipped rows are reported in a toast.

## Re-import safety
- `/parse` gives every row a `source_key`: sha256 of provider + the row's identity + an occurrence number (identical rows in one file stay distinct). pytr: raw timestamp, type, ISIN, shares, value. Other parsers: date, type, symbol, quantity, total. Inline edits keep the key.
- Stored on `transactions.source_key` (unique per portfolio). A key already in the portfolio is skipped.
- Transactions imported before keys existed have none: a keyed row also counts as imported when a keyless transaction in the portfolio has the same day, type, asset ISIN, quantity (8 dp) and cash amount (2 dp), each used once. Bulk-create writes the key onto that transaction, so later checks go by key.
- Keys are per provider: the same trades from a TR PDF and a pytr CSV don't match each other (only the keyless fallback could).

## Trade Republic rules (`parsers/trade_republic.py`, tests `tests/unit/test_trade_republic_import.py`)
- Rows come from the `UMSATZÜBERSICHT` block; the second-to-last amount on a line is the transaction amount, the last is the balance. Dates like `06 März 2025` / `09 Sept. 2025` are matched by month prefix.
- **Handel** → buy/sell (ISIN as symbol). The statement shows only the total, so the fee is assumed: `TRADE_FEE` = €1 per buy/sell trade, €0 for savings plan executions. `price = (total − fee) / qty` for buys, `(total + fee) / qty` for sells; `total_amount` stays the printed total.
- **Erträge** → dividend with `total_amount` = cash received, quantity and price 0. Bulk-create keeps that amount (it no longer recomputes qty × price for dividends) and rejects a dividend ≤ 0.
- **Zinszahlung, Überweisung, Kartentransaktion, Steuern** and unrecognised trades → `skipped[]` with a reason (`CASH_ROW_REASONS`); portfolios have no cash account. The review table lists them under "statement rows not imported".
- Every row is `currency="EUR"`. Bulk-create stores the portfolio currency and `taxes`, and rejects a row whose asset or statement currency differs from the portfolio's (no FX yet, plan 2.3); a new ticker in the wrong currency is not created.

## pytr CSV (`parsers/pytr_csv.py`, tests `tests/unit/test_pytr_csv_import.py`)
Full Trade Republic history via `pytr export_transactions` (homelab: `appdata/trade-republic`). Ten positional columns `Date;Type;Value;Note;ISIN;Shares;Fees;Taxes;ISIN2;Shares2`; English and German headers/types; `.` or `,` decimals.
- `Value` is the net cash moved (buy negative, incl. fees and taxes); fees and taxes are positive. Buy/Sell → price = (|value| ∓ fees ∓ taxes) / shares, `total_amount` = |value|. Dividend → `total_amount` = net value, `taxes` = withholding, quantity = shares held.
- Skipped with a reason: Split (applied from market data; importing would double it), Swap, Spinoff, transfers, and cash rows (Deposit/Removal/Interest/Taxes/Tax Refund).
- Rows are sorted by timestamp so same-day trades keep their execution order.

## ISIN → listing (`core/services/isin_resolver.py`)
TR fills in EUR on LS Exchange, which Yahoo doesn't carry; Yahoo's ISIN search usually returns only the primary (often USD) listing.
- Candidates: ISIN search + name search + names of the first hits + every German venue (`.F .SG .DE .MU .DU .HM .BE .HA`) of any German code found (or of the primary ticker). Crypto pseudo-ISINs `XF000XRP0018` → `XRP-EUR`.
- Score: share of the user's fills inside that day's low–high (±1 %), with later splits undone.
- Ranking: 5-point buckets, then account currency, then venue order Frankfurt, Stuttgart, XETRA… (hours closest to LS Exchange).
- Status: `existing` (user asset with that ISIN), `matched` (≥ 90 % in EUR), `uncertain` (≥ 50 %, suggested), `unmatched` (no suggestion; knock-outs/warrants `DE000H…`/`DE000V…` have no Yahoo prices, so the user picks a ticker or leaves the ISIN out).
- Dry run on a real 2024–2026 export: 37/60 ISINs matched (778/939 rows); Nvidia/Netflix 96/100 % after split adjustment.

## Known gaps
- No real statement in the test suite; layout drift (column order, extra amounts on a line) would show up as warnings or wrong amounts.
- In/out direction is not read (the type implies it for trades and dividends).
- Withholding tax is not printed per dividend, so `taxes` stays 0 for TR dividends.
- ISIN matching is the instrument panel (`POST /instruments/resolve`). Per-row hand mapping still exists for a row marked manual.
- Per-row `ValueError` messages are shown to the user; other errors are logged and reported generically.

## Planned
Plan 2.3 FX (Yahoo daily rates) so EUR transactions on USD assets value correctly; ISIN → ticker resolution. Later: an LLM fallback parser for unknown brokers via the shared ollama (§1b), and OCR via paperless/Tesseract.
