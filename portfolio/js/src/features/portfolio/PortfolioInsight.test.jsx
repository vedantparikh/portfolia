import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { CurrencyProvider } from "../../contexts/CurrencyContext";
import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import PortfolioInsight from "./PortfolioInsight";

vi.mock("./UnderwaterChart", () => ({ default: () => <div data-testid="underwater" /> }));

const holding = (asset_id, symbol, profit, contribution_pp, extra = {}) => ({
  asset_id,
  symbol,
  name: `${symbol} Inc.`,
  start_value: 0,
  end_value: 100,
  inflow: 100,
  outflow: 0,
  profit,
  contribution_pp,
  quote_currency: null,
  currency_effect: null,
  ...extra,
});

const insight = (period) => ({
  portfolio_id: 7,
  period,
  currency: "EUR",
  start_date: "2025-01-02",
  end_date: "2026-10-29",
  twr_pct: 20,
  contributions: [
    holding(1, "AAPL", 1500, 15, { quote_currency: "USD", currency_effect: -120 }),
    holding(2, "SAP", 700, 7),
    holding(3, "KO", -200, -2, { end_value: 0 }),
  ],
  months: [
    { period: "2025-12", start: "2025-12-01", end: "2025-12-31", return_pct: 3.2, benchmark_pct: 1.1, partial: false },
    { period: "2026-01", start: "2026-01-01", end: "2026-01-31", return_pct: -4.5, benchmark_pct: -2, partial: false },
    { period: "2026-10", start: "2026-10-01", end: "2026-10-29", return_pct: 2, benchmark_pct: null, partial: true },
  ],
  years: [
    { period: "2025", start: "2025-01-02", end: "2025-12-31", return_pct: 12, benchmark_pct: 9.5, partial: true },
    { period: "2026", start: "2026-01-01", end: "2026-10-29", return_pct: 7.1, benchmark_pct: 8, partial: true },
  ],
  drawdown: {
    current_pct: -3.4,
    max_pct: -12.5,
    points: [{ date: "2025-01-02", drawdown_pct: 0 }],
    episodes: [
      { peak_date: "2025-12-24", trough_date: "2026-03-27", recovery_date: "2026-07-15", depth_pct: -12.5, days_to_trough: 93, days_to_recover: 203 },
      { peak_date: "2026-09-01", trough_date: "2026-10-10", recovery_date: null, depth_pct: -5, days_to_trough: 39, days_to_recover: null },
    ],
  },
  timing: { profit: 2000, steady_profit: 1800, timing_effect: 200, steady_daily_pct: 0.04 },
  currency_effect: { total: -120, profit: 2000, by_currency: [{ currency: "USD", effect: -120 }] },
  benchmark: { symbol: "EUNL.DE", name: "iShares Core MSCI World", note: null, error: null },
});

describe("PortfolioInsight", () => {
  it("shows contributions, the monthly grid, drawdowns, timing and currency", async () => {
    const asked = [];
    server.use(
      http.get(`${API}/portfolios/calculations/portfolio/7/insight`, ({ request }) => {
        const period = new URL(request.url).searchParams.get("period");
        asked.push(period);
        return HttpResponse.json(insight(period));
      }),
    );
    const user = userEvent.setup();

    renderWithProviders(
      <CurrencyProvider currency="EUR">
        <PortfolioInsight portfolio={{ id: 7, currency: "EUR" }} />
      </CurrencyProvider>,
    );

    expect(await screen.findByText("What drove the return")).toBeInTheDocument();
    const rows = ["contribution-0", "contribution-1", "contribution-2"].map((id) => screen.getByTestId(id).textContent);
    expect(rows[0]).toContain("+15.00 pp");
    expect(rows[0]).toContain("from USD");
    expect(rows[2]).toContain("-2.00 pp");
    expect(screen.getByText("sold")).toBeInTheDocument();

    expect(screen.getByTitle("Jan 2026: -4.5%, EUNL.DE -2.0%")).toHaveTextContent("-4.5%");
    expect(screen.getByTitle("Oct 2026: +2.0% (part of the month)")).toBeInTheDocument();
    expect(screen.getByText("+2.5 pp")).toBeInTheDocument();
    expect(screen.getByText("-0.9 pp")).toBeInTheDocument();

    expect(screen.getByText("not yet")).toBeInTheDocument();
    expect(screen.getByText("203")).toBeInTheDocument();

    const timing = screen.getByText("Timing of your money").closest(".card");
    expect(within(timing).getByText("Timing effect")).toBeInTheDocument();
    expect(within(timing).getAllByText(/200/).length).toBeGreaterThan(0);
    const currency = screen.getByText("Currency").closest(".card");
    expect(within(currency).getByText("USD → EUR")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "1Y" }));
    expect(asked).toEqual(["inception", "1y"]);
  });

  it("says when the portfolio has nothing to analyse yet", async () => {
    server.use(
      http.get(`${API}/portfolios/calculations/portfolio/8/insight`, () =>
        HttpResponse.json({ portfolio_id: 8, period: "inception", currency: "EUR", contributions: [], months: [], years: [] }),
      ),
    );

    renderWithProviders(<PortfolioInsight portfolio={{ id: 8, currency: "EUR" }} />);

    expect(await screen.findByText("No transactions in this portfolio yet.")).toBeInTheDocument();
  });
});
