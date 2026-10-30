# Roadmap: long-term investing features

Portfolia is aimed at a long-term investor, not a day trader. What decides long-term results is what you hold, how much you add, what you lose to costs and tax, and whether you stay invested through a fall. These features follow from that, in the order we plan to build them. Each is one PR. Engine maths goes in `core/domain` with golden tests, as for every metric (see `python/app/core/domain/CLAUDE.md`).

Status: ✅ done · 🚧 in progress · ⏳ planned

## 1. Performance insight ✅
What drove the portfolio's return, in a Performance Insight view next to Performance Chart and Performance Metrics.

- **Contribution per holding**: each position's profit in money and its share of the period's time-weighted return in percentage points. It includes positions sold during the period, and the parts add up exactly to the portfolio's profit and return.
- **Monthly and yearly returns**: time-weighted return per month and calendar year, next to the portfolio's benchmark (primary, else the currency default). Shows best and worst month and year.
- **Drawdown and recovery**: the underwater curve (distance below the last peak), the deepest falls with peak, trough and recovery dates and how long each took, and how far below its peak the portfolio is today.
- **Timing effect**: actual profit against the profit the same deposits and withdrawals would have made at a steady rate equal to the period's time-weighted return. The difference is what the timing of your money added or cost, in money.
- **Currency effect**: for holdings quoted in another currency, the part of the profit that came from the exchange rate rather than the price, per currency.

## 2. Next-euro planner ⏳
What to buy with new money, and whether the savings plan is on track.

- **Buy-only rebalancing**: given an amount to invest, split it across holdings to move toward the target allocation without selling. Selling realises gains and, in Germany, tax. The current Rebalancing tab only proposes sells and buys to hit targets exactly.
- **Savings plans**: detect recurring purchases (Trade Republic "Savings plan execution" rows are already parsed) and show amount, rhythm, total invested per plan, and what each plan's money is worth now.
- **Goal projection**: target amount and date, plus current value and monthly savings, give a likely range of outcomes (bootstrapped from the portfolio's or the benchmark's monthly returns) and the monthly amount needed to reach the goal in a typical market.

## 3. Dividend income ⏳
- Income received per month and year, and the next 12 months expected from current holdings (last 12 months' dividend per share × shares held).
- Yield on cost (dividends per share ÷ your average cost) next to current yield.
- Dividend growth per holding (year-on-year change of the dividend per share).
- A month-by-month calendar of expected payments.

## 4. German tax view ⏳
Information, not tax advice. Trade Republic's taxes paid and refunds are already imported.

- **Sparerpauschbetrag**: how much of the yearly €1,000 allowance (€2,000 jointly assessed) gains and dividends have used, per broker, so the Freistellungsauftrag can be split well.
- **Vorabpauschale**: an estimate of January's advance tax on accumulating funds (from the Basiszins, the fund's value at the start of the year and its gain), with the 30% Teilfreistellung for equity funds.
- **Tax-loss harvesting**: positions with unrealised losses that could offset realised gains this year. Share losses offset only share gains, and each broker offsets only its own account until the tax return.

## 5. ETF look-through ⏳
- Combined country, sector and currency exposure through the ETFs held, plus direct holdings.
- Overlap between ETFs, for example how much of an S&P 500 ETF is already inside a world ETF.
- Data: Yahoo fund data gives sector weights and top holdings only, so exposure is approximate. Full holdings would need the issuers' files (iShares, Vanguard and so on); that is a separate decision.

## 6. Long-horizon backtests ⏳
Portfolio-level questions, unlike the single-stock strategy backtests.

- **Monthly investing vs a lump sum** into the target allocation, over the same years.
- **Rebalancing rules**: never, yearly, or when a holding drifts 5 points from target. Compared on return, deepest fall and number of trades.
- **"What if I had kept what I sold?"**: each past sale against holding on to today.
- **Valuation context**: a stock's current P/E against its own 5-year range, as context rather than a signal.

## 7. Review routine ⏳
- **Quarterly review page**:
  - what changed since the last review;
  - drift from targets;
  - biggest winners and losers;
  - upcoming dividends;
  - each holding's thesis.
- **Holding thesis and review date**: the watchlist's `investment_thesis` and `personal_rating`, extended to holdings, with a "review by" date that shows on the dashboard when due.
