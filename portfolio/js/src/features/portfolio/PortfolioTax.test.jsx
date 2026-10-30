import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";

import { CurrencyProvider } from "../../contexts/CurrencyContext";
import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import PortfolioTax from "./PortfolioTax";

const response = (params) => {
  const year = Number(params.get("year") ?? 2026);
  return {
    portfolio_id: 7,
    currency: "EUR",
    year,
    years: [2025, 2026],
    assumptions: {
      allowance: Number(params.get("allowance") ?? 1000),
      joint: params.get("joint") === "true",
      church_pct: Number(params.get("church_pct")),
      rate_pct: 26.375,
      basiszins_pct: 3.2,
      equity_fund_exemption_pct: 30,
    },
    settlement: {
      share_net: 300, other_net: 900, share_loss_in: 0, other_loss_in: -50, income: 1150, allowance: 1000,
      allowance_used: 1000, allowance_left: 0, taxable: 150, tax: 39.56, share_loss_carried: 0,
      other_loss_carried: 0, withheld: 40,
    },
    items: [
      {
        asset_id: 1, symbol: "ACME", name: "Acme", kind: "share", sale_gain: 300, vorabpauschale_credit: 0,
        dividends: 0, vorabpauschale: 0, taxable: 300,
      },
      {
        asset_id: 2, symbol: "WRLD", name: "World", kind: "fund", sale_gain: 1300, vorabpauschale_credit: 15,
        dividends: 0, vorabpauschale: 0, taxable: 899.5,
      },
    ],
    history: [
      { year: 2025, income: 500, allowance_used: 500, tax: 0, withheld: 0, share_loss_carried: 0, other_loss_carried: -50 },
      { year: 2026, income: 1150, allowance_used: 1000, tax: 39.56, withheld: 40, share_loss_carried: 0, other_loss_carried: 0 },
    ],
    vorabpauschale: {
      year, basiszins_pct: 3.2, estimate: year === 2026, due: `${year + 1}-01-02`, amount: 22.4, taxable: 15.68, tax: 4.14,
      funds: [
        {
          asset_id: 2, symbol: "WRLD", name: "World", kind: "fund", shares: 10, start_price: 100, end_price: 110,
          distributions: 0, per_share: 2.24, amount: 22.4, taxable: 15.68,
        },
      ],
    },
    harvest: [
      { asset_id: 3, symbol: "DOWN", name: "Down", kind: "share", unrealized: -200, taxable: -200, tax_saved: 39.56 },
    ],
    tax_free_gains: [],
    excluded: ["BTC-EUR"],
  };
};

describe("PortfolioTax", () => {
  beforeEach(() => localStorage.clear());

  it("settles the year, remembers the settings and switches years", async () => {
    const asked = [];
    server.use(
      http.get(`${API}/analytics/portfolios/7/tax/germany`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        asked.push(Object.fromEntries(params));
        return HttpResponse.json(response(params));
      }),
      http.get(`${API}/analytics/tax/germany/allowance`, () =>
        HttpResponse.json({
          year: 2026,
          allowance: 1000,
          income: 1500,
          portfolios: [
            { portfolio_id: 7, name: "Broker A", income: 1150, suggested: 1000 },
            { portfolio_id: 8, name: "Broker B", income: 350, suggested: 0 },
          ],
        }),
      ),
    );
    const user = userEvent.setup();

    renderWithProviders(
      <CurrencyProvider currency="EUR">
        <PortfolioTax portfolio={{ id: 7, name: "Book", currency: "EUR" }} />
      </CurrencyProvider>,
    );

    expect(await screen.findByText("your broker withheld €40.00 (net of refunds)")).toBeInTheDocument();
    expect(asked[0]).toEqual({ joint: "false", church_pct: "0" });
    expect(screen.getByText("Vorabpauschale 2026")).toBeInTheDocument();
    expect(screen.getByText(/Carried in from last year/)).toBeInTheDocument();
    const harvest = screen.getByText("Holding with a loss").closest("table");
    expect(within(harvest).getByText("DOWN")).toBeInTheDocument();
    expect(await screen.findByText("Broker B")).toBeInTheDocument();
    expect(screen.getByText(/Crypto \(BTC-EUR\) is left out/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Freistellungsauftrag here (EUR)"), "600");
    await user.selectOptions(screen.getByLabelText("Church tax"), "9");
    expect(asked.at(-1)).toMatchObject({ allowance: "600", church_pct: "9" });
    expect(JSON.parse(localStorage.getItem("portfolia.tax.7"))).toMatchObject({ allowance: "600", church: "9" });

    await user.selectOptions(screen.getByLabelText("Year"), "2025");
    expect(await screen.findByText("Vorabpauschale 2025")).toBeInTheDocument();
    expect(asked.at(-1).year).toBe("2025");
    expect(screen.queryByText("Holding with a loss")).not.toBeInTheDocument();
  });
});
