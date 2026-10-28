# Assets (tracked symbols)

**Purpose:** each user's instruments (symbol, type, sector…) enriched with Yahoo data; shown on the Asset Analysis page and used by transactions, portfolios and watchlists.

**State (2026-10-28):** ✅ list/create/bulk-create/detail/edit/delete work; the search box filters by symbol server-side and the page loads 8 at a time. ⚠️ sorting and range filters are not server-side; `/assets/search/*` has no UI.

## Backend
- `router.py` (prefix `/api/v1/assets`) reads and writes through `modules/assets/repository.py`:
  - `POST /` (create; fetches ticker info)
  - `POST /bulk-create` (verified users only; `allow_minimal_on_market_data_failure`)
  - `GET /` (`skip`, `limit`, `symbol` ilike, `asset_type`, `include_detail` → `detail` with price, 24h change, market cap, P/E, 52w, volume, dividend yield…; returns a bare list)
  - `GET/PUT/DELETE /{id}` (delete is soft)
  - `GET /{id}/prices`
- `search_router.py` (prefix `/api/v1/assets/search`): `/popular`, `/breakdown/{sectors,types,exchanges}`, `/suggestions`, `GET /{asset_id}` (declared last). All scoped to the current user's assets. No frontend caller.
- Services: `asset_search_service.py`, `market_data_service`. Tables `assets` (unique user_id+symbol), `market_indices`.

## Frontend — `js/src/features/assets/`
Route `/assets` → `Assets.jsx` ("Asset Analysis"):
- 8 `StatCard`s computed from the loaded rows: top gainer and loser, dividend, P/E, volume, beta, growth, momentum.
- `AssetCard` grid/list, infinite scroll (`useAssetPages`: `skip`/`limit` 8, optional 30 s auto-refresh), `AssetFilters` (only type filtering works; the rest are hidden via `hidden=`).
- `AssetModal` (overview and chart tabs; duplicate check against the loaded list) and `BulkAssetModal`. An asset card's analytics button opens `AssetAnalyticsView` in place (see `api/v1/statistical_indicators/CLAUDE.md`).
- API: `assetAPI` in `js/src/features/assets/api.ts` (returns response bodies). Query hooks in `features/assets/queries.ts`: `useAssets` (`["assets","list"]`, up to 1000, shared by asset search and duplicate checks), `useAssetPages`, `useTopAssets` (dashboard).

## Workflow
Add Asset / Bulk Entry → assets appear with live detail → click for overview + price chart (EnhancedChart with indicators) → used when creating transactions or watchlist items.

## Known gaps
- `Assets.jsx` also sends `sort_by`, `sort_order` and range params; the backend accepts only `symbol`/`asset_type`, so they are ignored (the sort and range filters are hidden). There is no `total`.
- The stat cards are computed from the pages loaded so far, not the whole list.
- Highest Growth card multiplies revenue growth by 100 (verify unit before trusting).

## Planned
Server-side sort and range filters, and a `total`, are still open. Symbol lookup is `GET /stock/symbols`, not these routes.
