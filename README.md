# Portfolia

Portfolia is a self-hosted investment tracker. You record buys, sells, and dividends (by hand, in bulk, or from a broker file). The app rebuilds your positions from those transactions, prices them from Yahoo Finance, and shows what the portfolio is worth, what you put in, and how it performed.

It is a personal app: one FastAPI service, a React UI, Postgres, and Redis. It runs in Docker on a private network. There is no public signup server.

A walkthrough with screenshots is in [docs/USER_GUIDE.md](docs/USER_GUIDE.md). A demo account is already loaded on this server (details below).

## What you can do

- **See everything in one place.** The dashboard sums your portfolios, lists today's movers, and shows recent trades. Totals are never added across currencies.
- **Track positions.** Each portfolio has holdings with quantity, FIFO cost (fees included), live value, unrealized P&L, today's P&L, and realized P&L. Splits from Yahoo are applied automatically.
- **Measure performance.** For any period you get the value chart, money in and out, time-weighted return (TWR), money-weighted return (MWR / XIRR), CAGR, volatility, Sharpe ratio, and drawdown. The same engine feeds the chart, the metrics page, holdings, and the dashboard, so those numbers agree.
- **Compare with a benchmark.** "Compare with" on the performance chart invests your own deposits and withdrawals in an index or ETF and plots that shadow portfolio next to yours.
- **Set targets.** Allocation targets, drift, and rebalancing suggestions are in shares, not a hand-waved dollar amount.
- **Read risk.** Volatility, Sharpe, Sortino, VaR, CVaR, drawdown, Calmar, plus beta and concentration versus the S&P 500 price index.
- **Follow symbols you do not hold.** Watchlists store the price when you added a symbol, notes, and high/low/percent alerts. A background worker checks prices about every 15 minutes and raises each alert once per crossing.
- **Chart indicators.** RSI, MACD, Bollinger Bands, and 14 other indicators, with saved indicator sets, on the Asset Analysis page.
- **Import a broker history.** Trade Republic PDF statements, a full Trade Republic export from [pytr](https://github.com/pytr-org/pytr) (`export_transactions` CSV), or Portfolia's own PDF. Re-importing the same file skips rows that are already in the portfolio. Listings are matched from the ISIN.
- **Export transactions to PDF.**
- **Look up the definitions.** Financial Concepts is a glossary of the returns, risk, and indicator terms the app uses.

## Workflows

| You want to… | Where |
|---|---|
| Check today's result | Dashboard |
| Record a buy, sell, or dividend | Transactions → New Transaction, or Portfolio → Add Position |
| Bring in a Trade Republic history | Transactions → Import statement. Use an **EUR** portfolio. A sample file is `docs/examples/demo_trade_republic.csv` |
| See whether you beat the money you put in | Portfolio → Performance Chart |
| See whether timing helped or hurt | Portfolio → Performance Metrics (TWR vs MWR) |
| See the same cash invested in an index | Performance Chart → Compare with |
| Decide what to buy or sell to match targets | Holdings Detail → Allocations, then Rebalancing |
| Watch a symbol and get told when it hits a price | Watchlist → edit the symbol → alert levels |
| Study RSI / MACD on a symbol | Assets → open the symbol |
| Learn what a metric means | Financial Concepts |

Step-by-step use of each screen is in the [user guide](docs/USER_GUIDE.md).

## Screens

Signed in as the demo user on 26 October 2026. Prices are live Yahoo quotes, so the same screens show different numbers later. The dashboard can take a few seconds to fill in; the first paint is often a row of dashes.

![Dashboard: total value, three portfolios, recent trades, and today's movers](docs/images/02-dashboard.png)

![Portfolio overview for the dense demo book](docs/images/03-portfolio-overview.png)

![Performance chart for the last year, with risk and cash-flow cards](docs/images/07-performance.png)

![Watchlist alerts](docs/images/04-watchlist.png)

## Demo account

On this server, sign in at <http://localhost:3000> (or `http://100.104.10.24:3000` from another device on the tailnet).

| | |
|---|---|
| Username | `demo` |
| Password | `DemoApp!234` |
| Email | `demo@example.com` |

The account holds synthetic trades over about three years, priced with real Yahoo history (including real splits and dividends). It is not a real broker account.

- **Demo — Day trading (dense history)** — USD, frequent trades, 12 holdings
- **Demo — Weekly rhythm** — USD, weekly trades
- **Demo — Monthly rhythm** — USD, monthly trades
- **Demo — Europe** — empty EUR portfolio, for the sample import
- **Demo watchlist** — AAPL, GOOGL, MSFT, SPY, with two example alerts already triggered

The password is the default in `portfolio/python/app/scripts/seed_demo_application.py`. The book is fake, but the UI is reachable on the LAN, so change the password if that matters. Do not run the seed with `--reset` against any other username: `--reset` deletes that user and every portfolio they own.

## How a number is defined

Positions are rebuilt from completed transactions only. Buys and sells use FIFO lots and include fees. Today's share count is split-adjusted because Yahoo's closes are split-adjusted. A dividend counts only when you record a dividend transaction. A missing price is left blank; the holding is never silently valued at cost.

Two different "returns" appear on purpose:

- The portfolio card's **Total Return** is unrealized gain divided by cost.
- **TWR** and **MWR** on the performance views measure growth of the money you put in, and they depend on the period you pick. A portfolio can show a small gain versus cost and a large TWR since inception, or the reverse over the last year.

Percentages are shown as percents (`15.0` means 15%). The risk-free rate used for Sharpe is 3%.

## Limits of the current version

- A portfolio holds one currency. An EUR portfolio cannot contain a USD listing, and there is no FX conversion yet. Dashboard totals stay separate per currency.
- There is no cash account. Deposits, interest, card payments, and tax refunds are listed as skipped when you import a statement.
- Splits are taken from market data. Importing a split row would double-count it, so those rows are skipped.
- Watchlist alerts are in-app only. Nothing is emailed or pushed.
- The Benchmarks tab still says comparison is coming. The working comparison is **Compare with** on the Performance Chart.
- PDF export still prints a `$`. Watchlist prices are also shown with a `$`.
- The Highest Growth tile on Asset Analysis can show an implausible percent. Do not use it for a decision.
- The first request for a portfolio's history talks to Yahoo and can take several seconds. Later requests are served from Redis.

## Upcoming

Not built yet. The design notes are in [portfolio/REFACTOR_PLAN.md](portfolio/REFACTOR_PLAN.md).

- Foreign-currency holdings, converted to the portfolio currency with historical rates
- A cash balance, so deposits, withdrawals, and interest can be imported instead of skipped
- Security transfers, swaps, and spin-offs
- Withholding tax kept on Trade Republic PDF dividends (the pytr CSV import already stores it)
- Email or phone alerts for watchlist prices
- The Benchmarks tab showing the same comparison the chart already does, with beta against a total-return index
- A settings page: profile, change password, delete account
- The background worker also refreshing holding prices and stored performance snapshots
- Statements from brokers other than Trade Republic, including a model-assisted parser and OCR for scans
- Production images, a staging copy, backups, and an HTTPS name on the tailnet
- Frontend tests and a gradual TypeScript migration

## Stack

| Part | What runs |
|---|---|
| API | Python 3.14, FastAPI 0.143, SQLAlchemy 2.1, Alembic, pandas 3, polars 2, yfinance 1 |
| UI | React 19, React Router 8, Vite 8, Tailwind 4, Node 22 |
| Data | Postgres 16, Redis 7 |
| Worker | Same API image; watchlist prices and alerts every 15 minutes |

Market data is Yahoo Finance via yfinance and yahooquery. Nothing calls a paid market-data API.

## Run the app

From `portfolio/`, with Docker. This host has no usable Node or a current Python, so the containers are the supported way to run it.

```bash
cd portfolio
cp python/app/.env.example python/app/.env.docker   # then set real secrets
cp js/.env.example js/.env.docker
docker network create homepage_proxy-network        # once; already exists on the home server
docker compose up -d --wait
```

- UI: <http://localhost:3000>
- API docs (on the server only): <http://127.0.0.1:8000/docs>
- Health: `curl -f http://127.0.0.1:8000/health/`

Postgres and Redis are not published on the host. Developer commands, tests, and the layout are in [portfolio/README.md](portfolio/README.md). The rules for changing the code are in [portfolio/CLAUDE.md](portfolio/CLAUDE.md).

## Documentation map

| Doc | For |
|---|---|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Using the product |
| [docs/README.md](docs/README.md) | Index of every doc |
| [portfolio/CLAUDE.md](portfolio/CLAUDE.md) | How the code is put together, and the per-feature references |
| [portfolio/REFACTOR_PLAN.md](portfolio/REFACTOR_PLAN.md) | What is done and what is left |

## License

MIT. See [LICENSE](LICENSE).
