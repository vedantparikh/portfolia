# Assets (tracked symbols)

**Purpose:** each user's instruments (symbol, type, sector…) enriched with Yahoo data; shown on the Asset Analysis page and used by transactions, portfolios and watchlists.

**State (2026-10-28):** ✅ list/create/bulk-create/detail/edit/delete work; the search box filters by symbol server-side and the page loads 8 at a time. sorting and the total count are server-side; ⚠️ range filters are not; `/assets/search/*` has no UI.

## Backend
- `router.py` (prefix `/api/v1/assets`) reads and writes through `modules/assets/repository.py`:
  - `POST /` (create; fetches ticker info)
  - `POST /bulk-create` (verified users only; `allow_minimal_on_market_data_failure`)
  - `GET /` (`skip`, `limit`, `symbol` ilike, `asset_type`, `sort_by` + `sort_order`, `include_detail` → `detail` with price, 24h change, market cap, P/E, 52w, volume, dividend yield…; returns a bare list, the total before paging in the `X-Total-Count` header). `sort_by` `symbol`/`name`/`created_at` sorts in SQL; `current_price`/`market_cap`/`volume_24h`/`price_change_percentage_24h` loads every matching asset's cached quote, sorts in Python (missing values last either way), then pages. Tests: `tests/unit/test_asset_list.py`
  - `GET/PUT/DELETE /{id}` (delete is soft)
  - `GET /{id}/prices`
- `search_router.py` (prefix `/api/v1/assets/search`): `/popular`, `/breakdown/{sectors,types,exchanges}`, `/suggestions`, `GET /{asset_id}` (declared last). All scoped to the current user's assets. No frontend caller.
- Services: `asset_search_service.py`, `market_data_service`. Tables `assets` (unique user_id+symbol), `market_indices`.

## Frontend — `js/src/features/assets/`
Route `/assets` → `Assets.jsx` ("Asset Analysis"):
- 8 `StatCard`s computed from the loaded rows: top gainer and loser, dividend, P/E, volume, beta, growth, momentum.
- `AssetCard` grid/list, infinite scroll (`useAssetPages`: `skip`/`limit` 8, optional 30 s auto-refresh), `AssetFilters` (type and sort work; the range filters are hidden via `hidden=`), "Showing N of total".
- `AssetModal` (overview and chart tabs; duplicate check against the loaded list) and `BulkAssetModal`. An asset card's analytics button opens `AssetAnalyticsView` in place (see `api/v1/statistical_indicators/CLAUDE.md`).
- API: `assetAPI` in `js/src/features/assets/api.ts` (returns response bodies). Query hooks in `features/assets/queries.ts`: `useAssets` (`["assets","list"]`, up to 1000, shared by asset search and duplicate checks), `useAssetPages` (`assetAPI.getAssetPage` → `{items, total}`), `useTopAssets` (dashboard).

## Workflow
Add Asset / Bulk Entry → assets appear with live detail → click for overview + price chart (EnhancedChart with indicators) → used when creating transactions or watchlist items.

## Known gaps
- Range filters (price, value, change, market cap) are not implemented server-side, so they stay hidden.
- The stat cards are computed from the pages loaded so far, not the whole list.
- Highest Growth card multiplies revenue growth by 100 (verify unit before trusting).

## Planned
Server-side range filters are still open. Symbol lookup is `GET /stock/symbols`, not these routes.
