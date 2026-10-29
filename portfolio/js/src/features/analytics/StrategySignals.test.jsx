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
    );

    renderWithProviders(<StrategySignals symbol="ACME" currency="USD" />);

    expect(await screen.findByText("hold")).toBeInTheDocument();
    expect(screen.getByText("28.4")).toBeInTheDocument();
    const actions = screen.getAllByText(/^(buy|sell)$/).map((el) => el.textContent);
    expect(actions).toEqual(["sell", "buy"]);
    expect(screen.getByText("$101.50")).toBeInTheDocument();
  });
});
