# Tests

Pytest, run from the API image so the installed dependencies match production. The command is in [../../../README.md](../../../README.md). `scripts/verify.sh` runs the suite, then fails if `tests/quarantine.txt` gained a line.

Do not point pytest at the stack database. `TESTING=true` and `TEST_DATABASE_URL=sqlite:////tmp/....db` are required. The running `portfolio-api-1` container is the wrong process.

## What is covered

| Area | Where |
|---|---|
| FIFO, splits, TWR, XIRR, risk | `tests/unit/test_domain_engine.py`, `test_position_and_returns.py` |
| Benchmark shadow | `tests/unit/test_benchmark_shadow.py` |
| Numbers the UI shows | `tests/unit/test_calculation_snapshots.py` and `tests/unit/snapshots/` |
| Indicators vs `ta` | `tests/unit/test_indicator_reference.py` plus the per-group files |
| Trade Republic PDF and pytr CSV | `tests/unit/test_trade_republic_import.py`, `test_pytr_csv_import.py`, `test_import_dedup.py` |
| Watchlist alerts | `tests/unit/test_watchlist_alerts.py` |
| Route order and error leaks | `tests/unit/test_route_order.py`, `test_error_messages.py` |
| Currency guard | `tests/unit/test_currency_guard.py` |

`tests/quarantine.txt` lists tests that are allowed to fail. The file only shrinks. When a fix makes one pass, delete its line.

Integration tests are in `tests/integration/`. Several are quarantined. See [integration/README.md](integration/README.md).

There is no frontend test suite.
