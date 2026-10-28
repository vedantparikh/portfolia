# 0002 One pure calculation engine

**Context.** Six services computed returns, cost and risk differently: deposits counted as returns, missing prices fell back to cost, splits were double counted.

**Decision.** All portfolio maths lives in `python/app/core/domain/` as pure functions (no DB, no network): FIFO lots with fees, splits from market data, transfers, daily valuation on unadjusted-for-dividends closes, cash-flow-adjusted TWR, XIRR, risk with one `RISK_FREE_RATE`, the benchmark shadow portfolio. Services load data and call it; the frontend only formats. Percent units are `15.0`. A missing price raises `MissingPriceError`; a close older than five sessions is flagged `stale_price`.

**Consequences.** Golden tests (`test_domain_engine.py`) and a characterisation snapshot (`test_calculation_snapshots.py`) fail on any changed number, which must be explained in the commit. Details: `core/domain/CLAUDE.md`.
