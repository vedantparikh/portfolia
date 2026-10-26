# Documentation

| Document | What it covers |
|---|---|
| [../README.md](../README.md) | What Portfolia is, the feature list, the demo account |
| [USER_GUIDE.md](USER_GUIDE.md) | How to use every screen, with screenshots |
| [examples/demo_trade_republic.csv](examples/demo_trade_republic.csv) | Synthetic pytr CSV for the import walkthrough |
| [../portfolio/README.md](../portfolio/README.md) | Run, test, and develop |
| [../portfolio/STARTUP_GUIDE.md](../portfolio/STARTUP_GUIDE.md) | Bring the Docker stack up |
| [../portfolio/PRODUCTION_DEPLOYMENT_CHECKLIST.md](../portfolio/PRODUCTION_DEPLOYMENT_CHECKLIST.md) | What "production" means today (it is not shipped) |
| [../portfolio/CLAUDE.md](../portfolio/CLAUDE.md) | Code layout, commands, and the per-feature references |
| [../portfolio/REFACTOR_PLAN.md](../portfolio/REFACTOR_PLAN.md) | Roadmap and progress log |

Feature references live beside the code. They are the source of truth for endpoints and known gaps:

- [Calculation engine](../portfolio/python/app/core/domain/CLAUDE.md)
- [Portfolios](../portfolio/python/app/api/v1/portfolio/CLAUDE.md)
- [Performance](../portfolio/python/app/api/v1/portfolio_calculations/CLAUDE.md)
- [Analytics](../portfolio/python/app/api/v1/analytics/CLAUDE.md)
- [Transactions](../portfolio/python/app/api/v1/transactions/CLAUDE.md)
- [Statement import](../portfolio/python/app/api/v1/account_statements/CLAUDE.md)
- [Watchlists](../portfolio/python/app/api/v1/watchlist/CLAUDE.md)
- [Assets](../portfolio/python/app/api/v1/assets/CLAUDE.md)
- [Market data](../portfolio/python/app/api/v1/market/CLAUDE.md)
- [Indicators](../portfolio/python/app/api/v1/statistical_indicators/CLAUDE.md)
- [Auth](../portfolio/python/app/api/v1/auth/CLAUDE.md)
- [UI shell](../portfolio/js/src/components/CLAUDE.md)

Older guides under `portfolio/python/app/docs/` were rewritten on 26 October 2026 so they match this layout. Prefer the feature references above when the two disagree, and update the feature reference in the same change as the code.
