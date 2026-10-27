# Assets (tracked symbols)

**Purpose:** each user's instruments (symbol, type, sector…) enriched with Yahoo data; shown on the Asset Analysis page and used by transactions, portfolios and watchlists.

**State (2026-10-16):** ✅ list/create/bulk-create/detail/delete work. ⚠️ search box and sorting don't filter server-side; `/assets/search/*` has no UI.

## Backend
- `router.py` (prefix `/api/v1/assets`) reads and writes through `modules/assets/repository.py`:
  - `POST /` (create; fetches ticker info)
  - `POST /bulk-create` (verified users only; `allow_minimal_on_market_data_failure`)
  - `GET /` (`skip`, `limit`, `symbol` ilike, `asset_type`, `include_detail` → `detail` with price, 24h change, market cap, P/E, 52w, volume, dividend yield…; returns a bare list)
  - `GET/PUT/DELETE /{id}` (delete is soft)
  - `GET /{id}/prices`
- `search_router.py` (prefix `/api/v1/assets/search`): `/popular`, `/breakdown/{sectors,types,exchanges}`, `/suggestions`, `GET /{asset_id}` (declared last). All scoped to the current user's assets. No frontend caller.
- Services: `asset_search_service.py`, `market_data_service`. Tables `assets` (unique user_id+symbol), `market_indices`.

## Frontend — `js/src/components/assets/`
Route `/assets` → `Assets.jsx` ("Asset Analysis"):
- 8 `StatCard`s computed from the loaded rows: top gainer and loser, dividend, P/E, volume, beta, growth, momentum.
- `AssetCard` grid/list and `AssetFilters` (only type filtering works; the rest are hidden via `hidden=`).
- `AssetModal` (overview and chart tabs; the analytics tab was removed) and `BulkAssetModal`.
- API: `userAssetsAPI`, `assetAPI` in `services/api.js`; `services/assetCache.js` caches.

## Workflow
Add Asset / Bulk Entry → assets appear with live detail → click for overview + price chart (EnhancedChart with indicators) → used when creating transactions or watchlist items.

## Known gaps
- `Assets.jsx` sends `query`, `sort_by`, `sort_order`, ranges — backend only accepts `symbol`/`asset_type`; `response.total` never set ("of N" count dead).
- `createUserAsset` does an extra GET for a client-side duplicate check.
- Unused client fns: `getAsset`, `updateAsset`, `deleteAsset`, `bulkUpdateUserAssets`.
- Highest Growth card multiplies revenue growth by 100 (verify unit before trusting).

## Planned
Server-side search/sort/pagination with `total` is still open. Plan 4.4 replaces `assetCache` with TanStack Query. Symbol lookup is `GET /stock/symbols`, not these routes.
