# Documentation

| Document | What it covers |
|---|---|
| [../README.md](../README.md) | What Portfolia is, the feature list, the demo account |
| [USER_GUIDE.md](USER_GUIDE.md) | How to use every screen, with screenshots |
| [examples/demo_trade_republic.csv](examples/demo_trade_republic.csv) | Synthetic pytr CSV for the import walkthrough |
| [../portfolio/README.md](../portfolio/README.md) | Run, test, develop: setup, architecture, API map, database, configuration |
| [../portfolio/CONTRIBUTING.md](../portfolio/CONTRIBUTING.md) | Workflow, adding a feature, migrations, tests |
| [../portfolio/docs/RUNBOOK.md](../portfolio/docs/RUNBOOK.md) | Production: deploy, rollback, staging, backups, secrets, timers |
| [../portfolio/docs/adr/](../portfolio/docs/adr/) | Architecture decisions |
| [../portfolio/CLAUDE.md](../portfolio/CLAUDE.md) | Code layout, commands, and the per-feature references |
| [../portfolio/REFACTOR_PLAN.md](../portfolio/REFACTOR_PLAN.md) | The refactor: what was done, what is deliberately left, progress log |

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

The feature references are the source of truth for endpoints and gaps; update the one you touch in the same change as the code.
