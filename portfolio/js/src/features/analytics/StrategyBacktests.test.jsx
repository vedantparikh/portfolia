import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { GUIDE_BY_ID } from "../../shared/metricGuide";
import { renderWithProviders } from "../../test/renderWithProviders";
import StrategyBacktests from "./StrategyBacktests";

const NAMES = {
  gfs: "Grandfather-father-son RSI",
  macd: "MACD with 200-day trend",
  golden_cross: "Golden / death cross",
  trend_200: "200-day trend",
  rsi_reversion: "RSI mean reversion",
  bollinger_reversion: "Bollinger Band reversion",
  breakout: "55/20-day breakout",
};

const empty = (strategy) => ({
  strategy,
  name: NAMES[strategy],
  rule: `${NAMES[strategy]} rule`,
  error: null,
  last_signal: null,
  invested: false,
  trades: [],
  win_rate_pct: null,
  average_return_pct: null,
  total_return_pct: 0,
  vs_holding_pp: -40,
  days_invested_pct: 0,
});

const response = (years) => ({
  symbol: "ACME",
  start: years === 1 ? "2025-10-29" : "2021-10-29",
  end: "2026-10-29",
  buy_and_hold_pct: 40,
  strategies: Object.keys(NAMES).map((strategy) => {
    if (strategy === "gfs") {
      return { ...empty(strategy), error: "Not enough price history for a monthly RSI(14)", total_return_pct: null, vs_holding_pp: null };
    }
    if (strategy !== "trend_200") return empty(strategy);
    return {
      ...empty(strategy),
      last_signal: { date: "2025-03-03", action: "buy" },
      invested: true,
      trades: [
        { entry_date: "2022-01-03", entry_price: 100, exit_date: "2022-06-01", exit_price: 110, return_pct: 10, open: false },
        { entry_date: "2025-03-03", entry_price: 120, exit_date: "2026-10-29", exit_price: 162, return_pct: 35, open: true },
      ],
      win_rate_pct: 100,
      average_return_pct: 22.5,
      total_return_pct: 48.5,
      vs_holding_pp: 8.5,
      days_invested_pct: 61.4,
    };
  }),
});

const Harness = ({ onShow }) => {
  const [years, setYears] = useState(5);
  const [shown, setShown] = useState(null);
  return (
    <StrategyBacktests
      symbol="ACME"
      currency="USD"
      years={years}
      onYearsChange={setYears}
      shown={shown}
      onShow={(strategy) => {
        setShown(strategy);
        onShow(strategy);
      }}
    />
  );
};

describe("StrategyBacktests", () => {
  it("compares every rule with holding and lists a rule's trades", async () => {
    const asked = [];
    server.use(
      http.get(`${API}/statistical-indicators/strategies/backtests`, ({ request }) => {
        const years = Number(new URL(request.url).searchParams.get("years"));
        asked.push(years);
        return HttpResponse.json(response(years));
      }),
    );
    const user = userEvent.setup();
    const shown = [];

    renderWithProviders(<Harness onShow={(strategy) => shown.push(strategy)} />);

    expect(await screen.findByText("1 of 6 rules beat it.", { exact: false })).toBeInTheDocument();
    for (const strategy of Object.keys(NAMES)) {
      const guide = GUIDE_BY_ID[strategy === "macd" ? "macd_strategy" : strategy];
      expect(screen.getByRole("button", { name: `About ${guide.name}` })).toBeInTheDocument();
    }
    expect(screen.getByText("Not enough price history for a monthly RSI(14)")).toBeInTheDocument();
    const row = screen.getByRole("button", { name: "200-day trend" }).closest("tr");
    expect(within(row).getByText("In")).toBeInTheDocument();
    expect(within(row).getByText("+48.50%")).toBeInTheDocument();
    expect(within(row).getByText("+8.50 pp")).toBeInTheDocument();
    expect(within(row).getByText("2 (100%)")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "200-day trend" }));
    expect(screen.getByText("still held")).toBeInTheDocument();
    expect(screen.getByText("$162.00")).toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: "Show 200-day trend on the chart" });
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    await user.click(toggle);
    expect(shown).toEqual(["trend_200", null]);
    expect(screen.queryByRole("button", { name: /Show Grandfather/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "1y" }));
    expect(await screen.findByText("Holding since", { exact: false })).toHaveTextContent("2025");
    expect(asked).toEqual([5, 1]);
  });
});
