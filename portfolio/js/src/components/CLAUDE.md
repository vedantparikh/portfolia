# Frontend app shell & shared UI

**Purpose:** routing, navigation, shared components and conventions every page uses. Feature docs live next to the backend router of each feature (each feature folder here has a pointer).

## Routes (`js/src/app/router.jsx`)
- Public auth pages live in `features/auth/`: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/validate-reset-token`, `/verify-email`.
- Protected routes render inside `app/ProtectedLayout.jsx`: `/dashboard`, `/portfolio`, `/assets`, `/transactions`, `/watchlist`, `/concepts`. Their pages live in `features/`, except the concepts page, which stays in this folder.
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
| `StatCard` | KPI tile: label, value, valueClassName, sub, detail, icon, tone (primary/success/danger/warning/gray), className. Green/red only for gains/losses (`getChangeColor`) |
| `Sparkline` | Plain-SVG line (no dependency) |
| `LoadingSpinner` | Re-export of `shared/ui/Spinner` |
| `EnhancedChart` | lightweight-charts v5 price + indicator panes (imported directly, not via the barrel) |
| `Chart` | Older chart used only by `AssetModal`; its `isPortfolioChart` branches are dead code |
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
| `tooltipDom.js` | Text-only chart tooltips, `chartMoney`, `barChange` |

There is no `Table` primitive: the tables share no structure beyond Tailwind classes. `SymbolSearch` and `ClientSideAssetSearch` search different sources, and `Chart` (asset modal, OHLC) and `EnhancedChart` (indicator panes) render different things, so neither pair was merged.

## Conventions
- All HTTP goes through the axios instance in `shared/api/client.ts` (`API_BASE_URL`, `apiErrorMessage`, the auth header and the single-flight `refreshAccessToken` on a 401). Each feature has its endpoint wrappers in `features/<name>/api.ts`; market data and indicators, used by shared components too, are `shared/api/market.ts` and `shared/api/indicators.ts`. Assets have one wrapper (`assetAPI`), whose functions return the response body.
- Reads go through TanStack Query hooks in `features/<name>/queries.ts` (keys and hooks per resource; `shared/api/queryClient.ts` holds the client: 5 min stale time, one retry). Keys are prefixes: everything about a portfolio (holdings, performance series and metrics, benchmark comparison, allocation analysis, analytics tabs, the import screen's already-imported rows, the dashboard cards) sits under `["portfolios", …]`, so invalidating `portfolioKeys.all` after a portfolio or transaction write refreshes them all. Assets are under `["assets", …]` (`list` for search, `details` for the holdings' type and market data, `pages` for the Assets page's infinite scroll, `top` for the dashboard), indicator configurations under `["indicators", …]`, alerts under `["watchlists", "alerts", …]`. Writes invalidate the matching prefix; the sidebar's refresh invalidates everything; logout clears the cache. Errors show via `react-hot-toast`.
- Money: in portfolio-scoped views `const money = useMoney()` (`hooks/useMoney.js`; `money(v, opts)`, `money.price(v)`, `money.currency`) — `Portfolio.jsx` wraps its views in `CurrencyProvider` with the selected portfolio's currency, the dashboard wraps nothing and passes `currency` per row/total. `formatCurrency` falls back to USD when `currency` is missing.
- Formatting only through `utils/formatters.jsx`:
  - `formatCurrency` takes Intl options, so use `signDisplay: "exceptZero"`; `showSign` is ignored by it.
  - `formatPercentage({showSign, precision, defaultValue})`, `formatRatio(v, precision)` (betas, P/E, indicator values), `formatDecimal`, `formatQuantity`, `formatDate`, `formatMarketCap(v, currency)`.
  - Use `formatDate(\`${isoDate}T12:00:00\`)` for date-only values.
  - `getChangeColor`.
  - Chart tooltips use `chartMoney(v, currency)` and `barChange(open, close)` from `shared/ui/tooltipDom.js`; `Chart` and `EnhancedChart` take the asset's `currency`.
- **No financial maths in the browser.** The only remaining exceptions are the amount↔quantity↔price helpers in the transaction forms (they fill inputs through `toInputDecimal`) and a candle's open→close change in the chart tooltips.
- ESLint (`no-restricted-syntax`) fails on `.toFixed(` and on a `$` before a digit or an interpolation (`"$5"`, `` `$${x}` ``, JSX `${x}`) anywhere but `utils/formatters.jsx` and the glossary.
- `font-variant-numeric: tabular-nums` is global (`index.css`). Tailwind 4 theme lives in `@theme`; there is no `info-*` colour.
- Lint: ESLint 9 flat config with 0 warnings in the gate; `react/prop-types` is off.

## Financial Concepts (`FinancialConcepts.jsx`, `/concepts`)
A static glossary of about 30 concepts in categories: returns (TWR, MWR, XIRR, CAGR, Modified Dietz), risk (Sharpe, Sortino, VaR, beta, drawdown), allocation, transactions and technical (RSI, MACD, MA). It has search, a category filter, sort and expandable cards, and makes no API calls. Keep its definitions consistent with `python/app/core/domain/CLAUDE.md` (e.g. MWR is shown per period, XIRR per year).

## Planned
Plan Phase 4:
- Vitest/RTL/MSW and Playwright.
- Gradual TypeScript with generated API types.
- Modal forms on react-hook-form (the auth pages already use it).
- Chart tooltips and risk reasoning are text, not HTML. The access token lives in memory in `shared/auth/tokenStore.ts`; the refresh token is an httpOnly cookie.
- Feature folders are in place. The concepts page still lives in `components/FinancialConcepts.jsx`.
