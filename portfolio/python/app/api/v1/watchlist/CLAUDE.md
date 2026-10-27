# Watchlists

**Purpose:** track symbols outside your portfolios, with the price when added, change since, notes and alert levels.

**State (2026-10-16):** ✅ lists, items, reorder, refresh prices; ✅ price alerts (worker + in-app). ⚠️ rating/thesis/tags have no UI; `/stats` has no gain/loss totals.

## Backend — `router.py` (prefix `/api/v1/watchlists`), `core/services/watchlist_service.py`
| Endpoint | Behaviour |
|---|---|
| `POST /`, `GET /`, `GET /{id}?include_real_time_data`, `PUT/DELETE /{id}` | Lists (name, colour, public, default). Real-time refresh writes current price/change to the DB |
| `POST /{id}/items`, `POST /{id}/items/bulk`, `PUT/DELETE /{id}/items/{item_id}`, `POST /{id}/reorder` | Items: `added_price` captured on add; notes, `personal_rating`, `investment_thesis`, `tags`; alert thresholds `alert_price_high`, `alert_price_low`, `alert_price_change_percent` (> 0, `null` clears) and `alerts_enabled` |
| `GET /alerts?unread_only=&limit=`, `POST /alerts/acknowledge {alert_ids?}` | Triggered alerts (newest first) with `unread_count`; acknowledge given ids or all unread. Declared before `/{watchlist_id}` |
| `GET /public`, `GET /stats` | Public lists; per-user counts, most-watched symbols, recent additions, `active_alerts`. `total_gain_loss*` are null (items have no quantity). No UI caller |

Models: `Watchlist`, `WatchlistItem`, `WatchlistAlert`, `WatchlistPerformance` (`core/database/models/watchlist.py`).

## Alerts
- **Rules** (`core/domain/alerts.py` `check_alerts`, pure): high fires at price ≥ threshold, low at ≤, percent when |change since added| ≥ threshold.
- **Worker** (`workers/run.py`, compose service `worker`): every `WORKER_INTERVAL_SECONDS` (900) calls `WatchlistService.refresh_prices_and_alerts` — one batched `get_current_prices` for all watched symbols, updates price/change, keeps one `WatchlistPerformance` row per item per day, applies alerts. Heartbeat `/tmp/worker-heartbeat` drives the healthcheck. One pass by hand: `docker compose exec worker python -c "import asyncio; from workers.run import run_once; print(asyncio.run(run_once()))"`.
- **Events** are `WatchlistAlert` rows with `is_triggered=True`: created when a condition becomes true (or its threshold changed); `is_active` = condition still true (closed when it stops holding, the threshold changes or alerts are disabled); `acknowledged_at` = read. So each alert notifies once per crossing.
- **Notification**: in-app only (decided 2026-10-16) — Watchlist alerts panel, bell on items with an open alert, dashboard "N new watchlist alerts" link. No ntfy/email.
- Legacy `create_price_alert` (manual alert rows, no endpoint) is kept only for quarantined tests.

## Frontend — `js/src/features/watchlist/`
Route `/watchlist` → `Watchlist.jsx` (grid of lists, or one opened list): `WatchlistAlerts` (recent alerts, unread, mark read), `WatchlistSidebar`, `WatchlistContent` (table, `min-w-[960px]` scroll on phones; bell on items whose alert holds), `AddSymbolModal`, `EditSymbolModal` (notes; high/low/% thresholds and alerts on/off), `Create/EditWatchlistModal`. `watchlistAPI` in `services/api.js`.

## Workflow
Create list → add symbols (search) → see price, change since added, notes → edit alert high/low → reorder → Refresh pulls live prices.

## Known gaps
- Watchlist items have no currency, so prices and thresholds show as plain numbers in alerts.
- `WatchlistPerformance` (daily price per item, written by the worker) has no chart yet.
- No UI for rating/thesis/tags or browsing public lists. `bulkAddItemsToWatchlist` is unused by the UI.
- Prices are shown with a hard-coded `$`.

## Planned
Batch 4 UI (agreed earlier): show change since added, days held, rating, tags, a thesis tooltip and alert thresholds in the table.
