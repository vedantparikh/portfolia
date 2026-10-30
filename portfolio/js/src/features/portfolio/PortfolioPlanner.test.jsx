import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import { CurrencyProvider } from "../../contexts/CurrencyContext";
import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import PortfolioPlanner from "./PortfolioPlanner";

vi.mock("./GoalChart", () => ({ default: () => <div data-testid="goal-chart" /> }));

const base = `${API}/analytics/portfolios/7/planner`;

const buy = (asset_id, symbol, amount, before, after, target) => ({
  asset_id,
  symbol,
  name: `${symbol} fund`,
  amount,
  shares: amount / 50,
  price: 50,
  value_before: 0,
  value_after: 0,
  weight_before_pct: before,
  weight_after_pct: after,
  target_pct: target,
});

describe("PortfolioPlanner", () => {
  it("plans new money, lists savings plans and projects the goal", async () => {
    const asked = { invest: [], goal: [] };
    server.use(
      http.get(`${base}/invest`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        asked.invest.push([params.get("amount"), params.get("min_amount")]);
        return HttpResponse.json({
          portfolio_id: 7,
          currency: "EUR",
          amount: Number(params.get("amount")),
          min_amount: 1,
          mode: "targets",
          buys: [buy(1, "EUNL", 370, 39.8, 50, 50), buy(2, "SAP", 30, 60.2, 50, 50), buy(3, "KO", 0, 0, 0, 0)],
          untargeted_value: 250,
          unpriced: ["XYZ"],
        });
      }),
      http.get(`${base}/savings-plans`, () =>
        HttpResponse.json({
          portfolio_id: 7,
          currency: "EUR",
          monthly_total: 400,
          plans: [
            {
              asset_id: 1, symbol: "ACME.F", name: "Acme SE", rhythm: "weekly", executions_per_month: 4, amount: 100,
              previous_amount: 50, monthly_amount: 400, executions: 30, first: "2026-03-23", last: "2026-10-23", invested: 3000,
              quantity: 20, value_now: 3876, active: true,
            },
            {
              asset_id: 2, symbol: "BETA.F", name: "Beta Inc", rhythm: "weekly", executions_per_month: 4, amount: 200,
              previous_amount: null, monthly_amount: 800, executions: 40, first: "2025-08-18", last: "2026-08-24", invested: 8000,
              quantity: 30, value_now: null, active: false,
            },
          ],
        }),
      ),
      http.get(`${base}/goal`, ({ request }) => {
        const params = new URL(request.url).searchParams;
        asked.goal.push(Object.fromEntries(params));
        return HttpResponse.json({
          portfolio_id: 7,
          currency: "EUR",
          target: Number(params.get("target")),
          target_date: params.get("target_date"),
          months: 120,
          start_value: 40000,
          monthly: 400,
          deposits: 118274.8,
          final: { 10: 150000, 25: 180000, 50: 210000, 75: 245000, 90: 290000 },
          probability_pct: 82,
          required_monthly: { 50: 120, 75: 380, 90: 700 },
          points: [{ date: "2026-11-30", p10: 1, p25: 2, p50: 3, p75: 4, p90: 5 }],
          basis: {
            symbol: "EUNL.DE", name: "MSCI World", first_month: "2009-09-30", months_of_history: 205,
            history_annual_pct: 13.4, assumed_annual_pct: params.get("annual_return") ? Number(params.get("annual_return")) : null,
            paths: 2000,
          },
        });
      }),
    );
    const user = userEvent.setup();

    renderWithProviders(
      <CurrencyProvider currency="EUR">
        <PortfolioPlanner portfolio={{ id: 7, name: "Book", currency: "EUR" }} />
      </CurrencyProvider>,
    );

    // New money: only the holdings that get something, with the weights
    const invest = (await screen.findByText("EUNL")).closest("table");
    expect(within(invest).getByText("€370.00")).toBeInTheDocument();
    expect(within(invest).queryByText("KO")).not.toBeInTheDocument();
    expect(within(invest).getByText("39.8%")).toBeInTheDocument();
    expect(screen.getByText(/left out of the weights/)).toBeInTheDocument();
    expect(screen.getByText(/skipped: XYZ/)).toBeInTheDocument();
    const amount = screen.getByLabelText("Amount (EUR)");
    await user.clear(amount);
    await user.type(amount, "1200");
    await user.click(screen.getByRole("button", { name: "Plan" }));
    expect(asked.invest).toEqual([["500", "1"], ["1200", "1"]]);

    // Savings plans: monthly total, active and stopped
    expect(await screen.findByText("€400.00", { selector: "span" })).toBeInTheDocument();
    expect(screen.getAllByText("weekly · 4× a month")).toHaveLength(2);
    expect(screen.getByText("from €50.00")).toBeInTheDocument();
    expect(screen.getByText("+29.2%")).toBeInTheDocument();
    expect(screen.getByText("stopped Aug 24, 2026")).toBeInTheDocument();

    // Goal: default 7 % assumption and the plans' monthly total as the placeholder
    expect(await screen.findByText("82%")).toBeInTheDocument();
    expect(asked.goal[0].annual_return).toBe("7");
    expect(asked.goal[0].monthly).toBeUndefined();
    expect(screen.getByPlaceholderText("400 (your plans)")).toBeInTheDocument();
    expect(screen.getByText(/shifted to average 7.0% a year/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Return assumption"), "history");
    await user.type(screen.getByLabelText("Monthly saving"), "800");
    await user.click(screen.getByRole("button", { name: "Project" }));
    expect(asked.goal.at(-1).annual_return).toBeUndefined();
    expect(asked.goal.at(-1).monthly).toBe("800");
  });
});
