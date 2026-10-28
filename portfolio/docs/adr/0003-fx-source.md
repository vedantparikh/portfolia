# 0003 Yahoo daily FX pairs

**Context.** Assets can be quoted in another currency than their portfolio (a Trade Republic EUR account holding US listings).

**Decision.** Use Yahoo's `{QUOTE}{PORTFOLIO}=X` daily closes (the inverse pair when only that exists), cached like price history. `GBp`/`GBX` and `ILA` are scaled to GBP and ILS. Closes and live prices convert every day; cash converts only when the transaction currency differs from the portfolio's. A missing rate raises `MissingFxError`. Totals across portfolios are never added across currencies. ECB rates were considered and not used: one provider, already cached and mocked in tests.

**Consequences.** FX history depends on Yahoo like prices do; the worker keeps the cache warm.
