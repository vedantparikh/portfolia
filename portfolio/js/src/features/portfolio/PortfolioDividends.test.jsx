import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { CurrencyProvider } from "../../contexts/CurrencyContext";
import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import PortfolioDividends from "./PortfolioDividends";

const chart = vi.fn();
vi.mock("./IncomeChart", () => ({
  default: (props) => {
    chart(props);
    return <div data-testid="income-chart" />;
  },
}));

const income = (period, gross, tax) => ({ period, gross, tax, net: gross - tax, payments: gross ? 1 : 0 });

describe("PortfolioDividends", () => {
  it("shows received and expected income, the calendar and the paying holdings", async () => {
    server.use(
      http.get(`${API}/analytics/portfolios/7/dividends`, () =>
        HttpResponse.json({
          portfolio_id: 7,
          currency: "EUR",
          received: { gross: 150, tax: 30, net: 120, gross_12m: 100, net_12m: 80, payments: 6, first: "2024-03-15" },
          expected: { gross_12m: 120, net_12m: 96, tax_rate_pct: 20, yield_pct: 2.5, yield_on_cost_pct: 3.1 },
          monthly: [income("2026-09-01", 40, 8), income("2026-10-01", 0, 0)],
          yearly: [income("2025-01-01", 50, 10), income("2026-01-01", 100, 20)],
          calendar: [
            {
              month: "2026-11-01",
              amount: 60,
              payments: [{ asset_id: 1, symbol: "ACME", day: "2026-11-20", per_share: 1.5, amount: 60 }],
            },
            { month: "2026-12-01", amount: 0, payments: [] },
          ],
          holdings: [
            {
              asset_id: 1, symbol: "ACME", name: "Acme SE", quantity: 40, source: "market", per_share_12m: 3,
              expected_12m: 120, current_yield_pct: 2.5, yield_on_cost_pct: 3.1, growth_pct: 12.5,
              per_share_by_year: [{ year: 2025, per_share: 2.8 }], last_dividend: "2026-05-02", pay_lag_days: 18,
              received_total: 150, received_12m: 100,
            },
          ],
          no_dividends: ["GROW"],
        }),
      ),
    );
    const user = userEvent.setup();

    renderWithProviders(
      <CurrencyProvider currency="EUR">
        <PortfolioDividends portfolio={{ id: 7, name: "Book", currency: "EUR" }} />
      </CurrencyProvider>,
    );

    expect(await screen.findByText("€80.00")).toBeInTheDocument();
    expect(screen.getByText("about €96.00 after 20.00% tax")).toBeInTheDocument();
    expect(screen.getByText("6 payments since Mar 15, 2024, €150.00 before tax")).toBeInTheDocument();

    const table = screen.getByRole("table");
    expect(within(table).getByText("ACME")).toBeInTheDocument();
    expect(within(table).getByText("3.10%")).toBeInTheDocument();
    expect(within(table).getByText("+12.5%")).toBeInTheDocument();
    expect(screen.getByText("No dividends on record: GROW")).toBeInTheDocument();
    expect(screen.getByText("€60.00", { selector: "p" })).toBeInTheDocument();

    expect(chart.mock.lastCall[0].received).toEqual([
      { time: "2026-09-01", value: 40 },
      { time: "2026-10-01", value: 0 },
    ]);
    expect(chart.mock.lastCall[0].expected).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Yearly" }));
    expect(chart.mock.lastCall[0].received).toEqual([
      { time: "2025-01-01", value: 50 },
      { time: "2026-01-01", value: 100 },
    ]);
    expect(chart.mock.lastCall[0].expected).toEqual([]);
  });
});
