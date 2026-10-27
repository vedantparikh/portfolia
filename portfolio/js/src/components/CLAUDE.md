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
- quick actions (new portfolio, new transaction, refresh), via `onQuickAction`;
- logout.

Each page renders its own header: `text-3xl` title, subtitle, actions on the right. The mobile menu button calls `openSidebar` or `toggleSidebar` from `useShell`.

## Shared components (`shared/`, barrel `index.js`)
| Component | Notes |
|---|---|
| `StatCard` | KPI tile: label, value, valueClassName, sub, detail, icon, tone (primary/success/danger/warning/gray), className. Green/red only for gains/losses (`getChangeColor`) |
| `Sparkline` | Plain-SVG line (no dependency) |
| `LoadingSpinner` | One ring. `type` only picks the default caption; `centered`, `size`, `text={null}` hides the caption |
| `EnhancedChart` | lightweight-charts v5 price + indicator panes (imported directly, not via the barrel) |
| `Chart` | Older chart used only by `AssetModal`; its `isPortfolioChart` branches are dead code |
| `SymbolSearch`, `ClientSideAssetSearch` | Symbol search (Yahoo) / search over the user's assets (`useAssets`, 5 min) |

Portfolio charts: `features/portfolio/PerformanceSeriesChart.jsx` (Value / Invested / Cost basis), `features/portfolio/AllocationDonut.jsx` (SVG).

## Conventions
- All HTTP goes through `services/api.js` (axios, refresh interceptor). Data fetching uses `useEffect` + `useState`; errors show via `react-hot-toast`.
- Money: in portfolio-scoped views `const money = useMoney()` (`hooks/useMoney.js`; `money(v, opts)`, `money.price(v)`, `money.currency`) — `Portfolio.jsx` wraps its views in `CurrencyProvider` with the selected portfolio's currency, the dashboard wraps nothing and passes `currency` per row/total. `formatCurrency` falls back to USD when `currency` is missing.
- Formatting only through `utils/formatters.jsx`:
  - `formatCurrency` takes Intl options, so use `signDisplay: "exceptZero"`; `showSign` is ignored by it.
  - `formatPercentage({showSign, precision})`, `formatRatio`, `formatQuantity`, `formatDate`.
  - Use `formatDate(\`${isoDate}T12:00:00\`)` for date-only values.
  - `getChangeColor`.
- **No financial maths in the browser.** The only remaining exceptions are amount↔quantity helpers in the transaction forms and the `Chart.jsx` tooltip.
- `font-variant-numeric: tabular-nums` is global (`index.css`). Tailwind 4 theme lives in `@theme`; there is no `info-*` colour.
- Lint: ESLint 9 flat config with 0 warnings in the gate; `react/prop-types` is off.

## Financial Concepts (`FinancialConcepts.jsx`, `/concepts`)
A static glossary of about 30 concepts in categories: returns (TWR, MWR, XIRR, CAGR, Modified Dietz), risk (Sharpe, Sortino, VaR, beta, drawdown), allocation, transactions and technical (RSI, MACD, MA). It has search, a category filter, sort and expandable cards, and makes no API calls. Keep its definitions consistent with `python/app/core/domain/CLAUDE.md` (e.g. MWR is shown per period, XIRR per year).

## Planned
Plan Phase 4:
- Vitest/RTL/MSW and Playwright.
- Gradual TypeScript with generated API types.
- Split `api.js` per feature.
- TanStack Query.
- `shared/ui` primitives (Modal, Table…), collapsing the 24 modals, 4 search components and 2 charts.
- Chart tooltips and risk reasoning are text, not HTML. Access and refresh tokens go through `shared/auth/tokenStore.ts` (still `localStorage`; an httpOnly cookie is still an open decision).
- Feature folders are in place. The concepts page still lives in `components/FinancialConcepts.jsx`.
