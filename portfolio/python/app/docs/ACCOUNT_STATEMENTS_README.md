# Statement import

Turns a broker file into reviewed transactions and writes them in one database transaction. The screen is Transactions → Import statement. The walkthrough and the sample file are in [../../../../docs/USER_GUIDE.md](../../../../docs/USER_GUIDE.md).

Feature reference, including the Trade Republic line rules and the ISIN scorer: [../api/v1/account_statements/CLAUDE.md](../api/v1/account_statements/CLAUDE.md).

## Providers

| id | UI name | Format |
|---|---|---|
| `trade_republic` | Trade Republic | PDF |
| `pytr_csv` | Trade Republic (pytr CSV) | CSV from `pytr export_transactions`. Ten columns: Date, Type, Value, Note, ISIN, Shares, Fees, Taxes, ISIN2, Shares2 |
| `portfolia` | Portfolia | PDF this app exported |

`GET /api/v1/account-statements/providers` returns that list. `POST /parse` (multipart `provider_id` and `file`) returns rows, skipped rows, and one instrument per ISIN. It does not write.

`POST /instruments/resolve` suggests a Yahoo listing for up to 10 ISINs. Uncached this is slow.

`POST /transactions/imported` says which of those rows are already in a portfolio.

`POST /transactions/bulk-create` inserts the rest, creates a missing asset from the ticker and ISIN, rebuilds each affected position, and commits once. Rows whose `source_key` is already stored are counted in `summary.total_skipped` and not inserted. The same endpoint serves the manual Bulk Entry modal, which sends no keys.

## Currency

Every imported row is checked against the portfolio currency. A mismatch is a 400 and the batch is not written. Trade Republic files are EUR. The sample CSV in `docs/examples/` is for an EUR portfolio.

## What is skipped

Cash (deposit, withdrawal, interest, card, account-level tax), splits, swaps, spin-offs, and security transfers. The review screen lists them with a reason. Splits are applied from market data instead.

## Tests

`tests/unit/test_trade_republic_import.py`, `tests/unit/test_pytr_csv_import.py`, `tests/unit/test_import_dedup.py`. The PDF parser is tested on synthetic text, not on a scanned statement.
