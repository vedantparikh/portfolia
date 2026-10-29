# Watchlists

**Purpose:** track symbols outside your portfolios, with the price when added, change since, notes and alert levels.

**State (2026-10-28):** ✅ lists, items, reorder, refresh prices; ✅ price alerts (worker + in-app). ⚠️ rating/thesis/tags have no UI; `/stats` has no gain/loss totals.

## Backend — `router.py` (prefix `/api/v1/watchlists`), `core/services/watchlist_service.py`
| Endpoint | Behaviour |
|---|---|
| `POST /`, `GET /`, `GET /{id}?include_real_time_data`, `PUT/DELETE /{id}` | Lists (name, colour, public, default). Real-time refresh writes current price/change to the DB |
| `POST /{id}/items`, `POST /{id}/items/bulk` (no UI caller), `PUT/DELETE /{id}/items/{item_id}`, `POST /{id}/reorder` | Items: `added_price` captured on add; notes, `personal_rating`, `investment_thesis`, `tags`; alert thresholds `alert_price_high`, `alert_price_low`, `alert_price_change_percent` (> 0, `null` clears) and `alerts_enabled` |
| `GET /alerts?unread_only=&limit=`, `POST /alerts/acknowledge {alert_ids?}` | Triggered alerts (newest first) with `unread_count`; acknowledge given ids or all unread. Declared before `/{watchlist_id}` |
| `GET /public`, `GET /stats` | Public lists; per-user counts, most-watched symbols, recent additions, `active_alerts`. `total_gain_loss*` are null (items have no quantity). No UI caller |

Models: `Watchlist`, `WatchlistItem`, `WatchlistAlert`, `WatchlistPerformance` (`core/database/models/watchlist.py`).

## Alerts
- **Rules** (`core/domain/alerts.py` `check_alerts`, pure): high fires at price ≥ threshold, low at ≤, percent when |change since added| ≥ threshold.
- **Worker** (`workers/run.py`, compose service `worker`): every `WORKER_INTERVAL_SECONDS` (900) calls `WatchlistService.refresh_prices_and_alerts` — one batched `get_current_prices` for all watched symbols, updates price/change, keeps one `WatchlistPerformance` row per item per day, applies alerts. Heartbeat `/tmp/worker-heartbeat` drives the healthcheck. One pass by hand: `docker compose exec worker python -c "import asyncio; from workers.run import run_once; print(asyncio.run(run_once()))"`.
- **Events** are `WatchlistAlert` rows with `is_triggered=True`: created when a condition becomes true (or its threshold changed); `is_active` = condition still true (closed when it stops holding, the threshold changes or alerts are disabled); `acknowledged_at` = read. So each alert notifies once per crossing.
- **Notification**: in-app only (decided 2026-10-16) — Watchlist alerts panel, bell on items with an open alert, dashboard "N new watchlist alerts" link. No ntfy/email.
- Legacy `create_price_alert` (manual alert rows, no endpoint) is used only by `tests/unit/test_watchlist_service.py`.

## Frontend — `js/src/features/watchlist/`
Route `/watchlist` → `Watchlist.jsx` (grid of lists, or one opened list). How a person uses the screen: `docs/USER_GUIDE.md`.
| File | Role |
|---|---|
| `Watchlist.jsx` | Page: list of watchlists, or one opened list (auto-refresh every 30 s while open) |
| `WatchlistAlerts` | Recent alerts, unread, mark read (polls every 60 s) |
| `WatchlistContent` | Symbol table, drag to reorder; `min-w-[960px]`, scrolls horizontally on a phone; bell on items whose alert holds |
| `AddSymbolModal`, `EditSymbolModal` | Search (`/stock/symbols`) and add; notes, high/low/% thresholds, alerts on/off |
| `CreateWatchlistModal`, `EditWatchlistModal` | The list itself |

HTTP goes through `watchlistAPI` in `js/src/features/watchlist/api.ts`; query hooks in `features/watchlist/queries.ts` (`["watchlists", …]`; the dashboard's unread count is `["watchlists","alerts","unread"]`). Alerts are evaluated by the `worker`, not by the page; Refresh updates prices on screen.

## Workflow
Create list → add symbols (search) → see price, change since added, notes → edit alert high/low → reorder → Refresh pulls live prices.

## Known gaps
- Watchlist items have no currency: the table formats prices as USD (the `formatPrice` default) and alerts show plain numbers.
- `WatchlistPerformance` (daily price per item, written by the worker) has no chart yet.
- No UI for rating/thesis/tags or browsing public lists.

## Planned
Batch 4 UI (agreed earlier): show change since added, days held, rating, tags, a thesis tooltip and alert thresholds in the table.
