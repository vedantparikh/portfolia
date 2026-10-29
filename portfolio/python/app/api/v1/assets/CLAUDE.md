# Assets (tracked symbols)

**Purpose:** each user's instruments (symbol, type, sector…) enriched with Yahoo data; shown on the Asset Analysis page and used by transactions, portfolios and watchlists.

**State (2026-10-28):** ✅ list/create/bulk-create/detail/edit/delete work; the search box filters by symbol server-side and the page loads 8 at a time. sorting, range filters, the total count and the highlight cards are server-side; `/assets/search/*` has no UI.

## Backend
- `router.py` (prefix `/api/v1/assets`) reads and writes through `modules/assets/repository.py`:
  - `POST /` (create; fetches ticker info)
  - `POST /bulk-create` (verified users only; `allow_minimal_on_market_data_failure`)
  - `GET /` (`skip`, `limit`, `symbol` ilike, `asset_type`, `sort_by` + `sort_order`, `include_detail` → `detail` with price, 24h change, market cap, P/E, 52w, volume, dividend yield…; returns a bare list, the total before paging in the `X-Total-Count` header). `sort_by` `symbol`/`name`/`created_at` sorts in SQL; `current_price`/`market_cap`/`volume_24h`/`price_change_percentage_24h` loads every matching asset's cached quote, sorts in Python (missing values last either way), then pages. Tests: `tests/unit/test_asset_list.py`
  - Quote filters on `GET /`: `price_min`/`price_max`, `market_cap_min`/`market_cap_max` (lower bound inclusive, upper exclusive, in the listing's currency), `change=up|down|flat` (24h change ≥ +0.5 %, ≤ −0.5 %, or within). Any quote filter or quote sort loads every matching asset's cached quote, filters and sorts in Python, then pages; an asset without the value never matches a set bound (`modules/assets/quotes.py`)
  - `GET /highlights` → top gainer and loser (24h %), highest dividend yield (%), lowest positive P/E, most traded (volume), lowest positive beta, highest revenue growth (Yahoo's fraction × 100 = %), closest to the 52-week high (price ÷ high × 100); each `{symbol, name, value}` or null, over all the user's assets
  - `GET/PUT/DELETE /{id}` (delete is soft)
  - `GET /{id}/prices`
- `search_router.py` (prefix `/api/v1/assets/search`): `/popular`, `/breakdown/{sectors,types,exchanges}`, `/suggestions`, `GET /{asset_id}` (declared last). All scoped to the current user's assets. No frontend caller.
- Services: `asset_search_service.py`, `market_data_service`. Tables `assets` (unique user_id+symbol), `market_indices`.

## Frontend — `js/src/features/assets/`
Route `/assets` → `Assets.jsx` ("Asset Analysis"):
- 8 highlight cards from `GET /assets/highlights` (`useAssetHighlights`): top gainer and loser, dividend, P/E, volume, beta, growth, momentum. The browser only displays them.
- `AssetCard` grid/list, infinite scroll (`useAssetPages`: `skip`/`limit` 8, optional 30 s auto-refresh), `AssetFilters` (type, price range, 24h change, market cap and sort; the page turns `"low-high"` ranges into `_min`/`_max` params), "Showing N of total".
- `AssetModal` (overview and chart tabs; duplicate check against the loaded list; the chart tab is `features/analytics/IndicatorChart.jsx`, `EnhancedChart` with the indicator picker; "Open analysis" in its header switches to the analytics view) and `BulkAssetModal`. An asset card's ⋮ menu → Analytics opens `AssetAnalyticsView` in place (see `api/v1/statistical_indicators/CLAUDE.md`).
- API: `assetAPI` in `js/src/features/assets/api.ts` (returns response bodies). Query hooks in `features/assets/queries.ts`: `useAssets` (`["assets","list"]`, up to 1000, shared by asset search and duplicate checks), `useAssetPages` (`assetAPI.getAssetPage` → `{items, total}`), `useTopAssets` (dashboard).

## Workflow
Add Asset / Bulk Entry → assets appear with live detail → click for overview + price chart (EnhancedChart with indicators) → used when creating transactions or watchlist items.

## Known gaps
- `GET /{id}/prices` (and `assetAPI.getAssetPrices`) lost its only caller when the modal chart moved to the indicator calculation.
- Range bounds are in each listing's own currency; mixed-currency lists are not converted.

## Planned
Symbol lookup is `GET /stock/symbols`, not these routes.
