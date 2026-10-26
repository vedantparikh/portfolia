# Watchlist UI

Route `/watchlist`. Behaviour, the worker, and the API are documented in [../../../../python/app/api/v1/watchlist/CLAUDE.md](../../../../python/app/api/v1/watchlist/CLAUDE.md). How a person uses the screen is in [../../../../../docs/USER_GUIDE.md](../../../../../docs/USER_GUIDE.md).

Components in this folder:

| File | Role |
|---|---|
| `Watchlist.jsx` | Page: list of watchlists, or one opened list |
| `WatchlistAlerts` | Unread alerts, mark read |
| `WatchlistContent` | Symbol table. Scrolls horizontally on a phone |
| `AddSymbolModal`, `EditSymbolModal` | Search and add; notes and high/low/percent alerts |
| `CreateWatchlistModal`, `EditWatchlistModal` | The list itself |

HTTP goes through `watchlistAPI` in `services/api.js`. Alerts are evaluated by the `worker` service, not by this page. Refresh updates prices on screen.

Not on the screen yet: personal rating, investment thesis, tags, a chart of `WatchlistPerformance`, and browsing public lists.
