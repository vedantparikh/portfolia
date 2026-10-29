# Frontend app shell & shared UI

**Purpose:** routing, navigation, shared components and conventions every page uses. Feature docs live next to the backend router of each feature (each folder in `src/features/` has a pointer).

**State (2026-10-28):** ✅ feature folders, per-feature API modules and query hooks, `shared/ui` primitives, in-memory access token with an httpOnly refresh cookie, Vitest and a Playwright smoke test are in place.

## Routes (`js/src/app/router.jsx`)
- Public auth pages live in `features/auth/`: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/validate-reset-token`, `/verify-email`.
- Protected routes render inside `app/ProtectedLayout.jsx`: `/dashboard`, `/portfolio`, `/assets`, `/transactions`, `/watchlist`, `/concepts`, `/settings` (`features/settings/Settings.jsx`: profile, password change, close account with the password). Their pages live in `features/`, except the concepts page, which stays in this folder.
- `/` redirects to `/dashboard`. Unknown paths render `app/NotFound.jsx`.
- Each route is `React.lazy`. `app/ErrorBoundary.jsx` wraps the outlet and resets when the path changes.

## Shell
`ProtectedLayout` owns `shared/Sidebar.jsx`, the mobile overlay, and the error boundary. Pages register the portfolio selector, search, and quick actions with `usePageChrome` (`app/chrome.js`). `currentView` comes from the path. The desktop sidebar stays visible (`lg:translate-x-0`); `isOpen` only matters on mobile.

`shared/Sidebar.jsx` provides:
- nav links;
- a portfolio selector, shown only on the portfolio and transactions views;
- a search box (the page's `onSearchChange`);
- quick actions (new portfolio, new transaction, refresh), via `onQuickAction`. A page returns `true` when it handled the action; otherwise `ProtectedLayout` opens the create modal on `/portfolio` or `/transactions` (router state `action`), or invalidates every query on refresh;
- logout.

Each page renders its own header: `text-3xl` title, subtitle, actions on the right. The mobile menu button calls `openSidebar` or `toggleSidebar` from `useShell`.

## Shared components (`shared/`, barrel `index.js`)
| Component | Notes |
|---|---|
| `StatCard` | KPI tile: label, info (a `metricGuide` id → ⓘ tip), value, valueClassName, sub, detail, icon, tone (primary/success/danger/warning/gray), className. Green/red only for gains/losses (`getChangeColor`) |
| `Sparkline` | Plain-SVG line (no dependency) |
| `LoadingSpinner` | Re-export of `shared/ui/Spinner` |
| `EnhancedChart` | lightweight-charts v5 price + indicator panes (imported directly, not via the barrel) |
| `SymbolSearch`, `ClientSideAssetSearch` | Symbol search (Yahoo) / search over the user's assets (`useAssets`, 5 min) |

Portfolio charts: `features/portfolio/PerformanceSeriesChart.jsx` (Value / Invested / Cost basis), `features/portfolio/AllocationDonut.jsx` (SVG).

## UI primitives (`src/shared/ui/`, barrel `index.js`)
| Primitive | Notes |
|---|---|
| `Modal` | Every dialog. Portal to `document.body`; the overlay div is the dialog (`role="dialog"`, `aria-modal`), labelled by its first heading unless `labelledBy` is set. Esc closes the topmost one (`closeOnEscape={false}` on the PDF import review, whose ✕ also drops the draft), Tab stays inside, focus moves to the dialog unless a child autofocuses and returns to the opener on close. `closeOnBackdrop` is opt-in (only the risk-level dialog). `overlayClassName` defaults to `fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4`; the panel is the child, so each modal keeps its own size and classes |
| `Spinner` | One ring. `type` only picks the default caption; `centered`, `size`, `text={null}` hides the caption |
| `Button` | `btn-primary` / `btn-secondary` / `btn-outline` by `variant`, `type="button"` by default |
| `Card` | `card` utility plus `className` (default `p-6`) |
| `EmptyState`, `ErrorState` | Centered icon, title, message; `ErrorState` adds a "Try Again" button for `onRetry`. Used by the analytics tabs |
| `InfoTip` | ⓘ button next to a metric (`id` = a `shared/metricGuide.js` entry): portal popover with what it is, how to read it, good, watch out, what it implies, and a link to `/concepts#id`. Esc, outside click or scroll closes it |
| `tooltipDom.js` | Text-only chart tooltips, `chartMoney`, `barChange` |

There is no `Table` primitive: the tables share no structure beyond Tailwind classes. `SymbolSearch` and `ClientSideAssetSearch` search different sources, so they were not merged. Every price chart is `EnhancedChart` (the older `Chart` was removed 2026-10-29).

## Conventions
- All HTTP goes through the axios instance in `shared/api/client.ts` (`API_BASE_URL`, `apiErrorMessage`, the auth header and the single-flight `refreshAccessToken` on a 401). Each feature has its endpoint wrappers in `features/<name>/api.ts`; market data and indicators, used by shared components too, are `shared/api/market.ts` and `shared/api/indicators.ts`. Assets have one wrapper (`assetAPI`), whose functions return the response body.
- Reads go through TanStack Query hooks in `features/<name>/queries.ts` (keys and hooks per resource; `shared/api/queryClient.ts` holds the client: 5 min stale time, one retry). Keys are prefixes: everything about a portfolio (holdings, performance series and metrics, benchmark comparison, allocation analysis, analytics tabs, the import screen's already-imported rows, the dashboard cards) sits under `["portfolios", …]`, so invalidating `portfolioKeys.all` after a portfolio or transaction write refreshes them all. Assets are under `["assets", …]` (`list` for search, `details` for the holdings' type and market data, `pages` for the Assets page's infinite scroll, `top` for the dashboard), indicator configurations under `["indicators", …]`, alerts under `["watchlists", "alerts", …]`. Writes invalidate the matching prefix; the sidebar's refresh invalidates everything; logout clears the cache. Errors show via `react-hot-toast`.
- Money: in portfolio-scoped views `const money = useMoney()` (`hooks/useMoney.js`; `money(v, opts)`, `money.price(v)`, `money.currency`) — `Portfolio.jsx` wraps its views in `CurrencyProvider` (`contexts/CurrencyContext.jsx`) with the selected portfolio's currency, the dashboard wraps nothing and passes `currency` per row/total. `formatCurrency` falls back to USD when `currency` is missing, and a null amount shows `defaultValue` or zero in the requested currency.
- Formatting only through `utils/formatters.jsx`:
  - `formatCurrency` takes Intl options, so use `signDisplay: "exceptZero"`; `showSign` is ignored by it.
  - `formatPrice(v, currency)` (more decimals below 1), `formatPercentage({showSign, precision, defaultValue})`, `formatRatio(v, precision)` (betas, P/E, indicator values), `formatDecimal`, `formatQuantity`, `formatVolume`, `formatDate`, `formatDateTime`, `formatMarketCap(v, currency)`.
  - Use `formatDate(\`${isoDate}T12:00:00\`)` for date-only values.
  - `getChangeColor`.
  - Chart tooltips use `chartMoney(v, currency)` and `barChange(open, close)` from `shared/ui/tooltipDom.js`; `Chart` and `EnhancedChart` take the asset's `currency`.
- **No financial maths in the browser.** The only remaining exceptions are the amount↔quantity↔price helpers in the transaction forms (they fill inputs through `toInputDecimal`) and a candle's open→close change in the chart tooltips.
- ESLint (`no-restricted-syntax`) fails on `.toFixed(` and on a `$` before a digit or an interpolation (`"$5"`, `` `$${x}` ``, JSX `${x}`) in every source file, except `utils/formatters.jsx`, the glossary and tests.
- `font-variant-numeric: tabular-nums` is global (`index.css`). Tailwind 4 theme lives in `@theme`; there is no `info-*` colour.
- Lint: ESLint 9 flat config with 0 warnings in the gate; `react/prop-types` is off. `.ts`/`.tsx` files use `typescript-eslint` (recommended, not type-aware) with the same React, hooks and formatter rules; `shared/api/generated/` is ignored.
- API types: `npm run generate:api` writes `shared/api/generated/schema.ts` from the OpenAPI document; `shared/api/schema.ts` exposes `Schemas` (e.g. `assetAPI` returns `Schemas["Asset"]`).
- Tests: `npm test` = Vitest (jsdom, `src/**/*.test.*`, MSW handlers in `src/test/msw/`, `renderWithProviders`); files: `utils/formatters.test.js`, `shared/auth/tokenStore.test.ts`, `contexts/AuthContext.test.jsx`. `npm run test:e2e` = Playwright `e2e/smoke.spec.ts` (sign in, reload keeps the session, create a portfolio, sign out).

## Metric guide and Financial Concepts (`/concepts`)
`shared/metricGuide.js` is the one explanation per number the app shows (id, name, category, short, what, formula as this app computes it, example, read, good, bad, implies, optional caveat). The ⓘ tips (`InfoTip`, `StatCard info=`, the `info` prop on the chart's `Row`, `BenchmarkCard`'s `Versus` and the analytics `MetricRow`) and `components/FinancialConcepts.jsx` both read it, so they cannot drift apart. The page filters by category and search, sorts by topic or name, and `/concepts#<id>` scrolls to and opens that entry. Keep the formulas consistent with `python/app/core/domain/CLAUDE.md`; good/bad bands are rules of thumb and the page says so. `shared/metricGuide.test.js` fails when a screen points at an id the guide does not have.

## Planned
Plan Phase 4:
- More TypeScript: pages and components are still `.jsx`; only the API layer, query hooks and token store are `.ts`.
- Modal forms on react-hook-form (only the auth pages use it).
- More unit and e2e coverage beyond the three test files and the smoke test.
- The concepts page still lives in `components/FinancialConcepts.jsx`.
