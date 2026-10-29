import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { API } from "../../test/msw/handlers";
import { server } from "../../test/msw/server";
import { renderWithProviders } from "../../test/renderWithProviders";
import StrategySignals from "./StrategySignals";

describe("StrategySignals", () => {
  it("shows the GFS readings and the MACD signals, newest first", async () => {
    server.use(
      http.get(`${API}/statistical-indicators/strategies/gfs`, () =>
        HttpResponse.json({
          symbol: "ACME",
          action: "hold",
          readings: [
            { timeframe: "monthly", rsi: 61.2, as_of: "2026-10-31" },
            { timeframe: "weekly", rsi: 55.01, as_of: "2026-11-01" },
            { timeframe: "daily", rsi: 28.4, as_of: "2026-10-29" },
          ],
        }),
      ),
      http.get(`${API}/statistical-indicators/strategies/macd`, () =>
        HttpResponse.json({
          symbol: "ACME",
          since: "2025-10-29",
          signals: [
            { date: "2026-02-03", action: "buy", close: 101.5, macd: -1, signal: -1.2, trend_ema: 95 },
            { date: "2026-08-10", action: "sell", close: 120, macd: 2, signal: 2.1, trend_ema: 125 },
          ],
        }),
      ),
      http.get(`${API}/statistical-indicators/strategies/backtest`, ({ request }) => {
        const strategy = new URL(request.url).searchParams.get("strategy");
        return HttpResponse.json({
          symbol: "ACME",
          strategy,
          start: "2021-10-29",
          end: "2026-10-29",
          trades:
            strategy === "macd"
              ? [
                  { entry_date: "2022-01-03", entry_price: 100, exit_date: "2022-06-01", exit_price: 110, return_pct: 10, open: false },
                  { entry_date: "2023-01-03", entry_price: 120, exit_date: "2023-05-01", exit_price: 108, return_pct: -10, open: false },
                ]
              : [],
          win_rate_pct: strategy === "macd" ? 50 : null,
          average_return_pct: strategy === "macd" ? 0 : null,
          total_return_pct: strategy === "macd" ? -1 : 0,
          buy_and_hold_pct: 42.5,
          days_invested_pct: strategy === "macd" ? 20 : 0,
        });
      }),
    );

    renderWithProviders(<StrategySignals symbol="ACME" currency="USD" />);

    expect(await screen.findByText("hold")).toBeInTheDocument();
    expect(screen.getByText("28.4")).toBeInTheDocument();
    const actions = screen.getAllByText(/^(buy|sell)$/).map((el) => el.textContent);
    expect(actions).toEqual(["sell", "buy"]);
    expect(screen.getByText("$101.50")).toBeInTheDocument();
    expect(await screen.findByText("No trades. Holding instead:", { exact: false })).toBeInTheDocument();
    expect(await screen.findByText("2 (50%)")).toBeInTheDocument();
    expect(screen.getByText("-1.00%")).toBeInTheDocument();
  });
});
