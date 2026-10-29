import { describe, expect, it } from "vitest";

import { chartPeriodFor, strategyMarkers } from "./strategyMarkers";

const row = (overrides) => ({ error: null, trades: [], last_signal: null, ...overrides });

describe("strategyMarkers", () => {
  it("marks each trade and labels the latest call", () => {
    const markers = strategyMarkers(
      row({
        trades: [
          { entry_date: "2024-01-02", exit_date: "2024-03-01", open: false },
          { entry_date: "2025-05-05", exit_date: "2026-10-29", open: true },
        ],
        last_signal: { date: "2025-05-05", action: "buy" },
      }),
    );

    expect(markers.map((m) => [m.date, m.shape, m.text])).toEqual([
      ["2024-01-02", "arrowUp", undefined],
      ["2024-03-01", "arrowDown", undefined],
      ["2025-05-05", "arrowUp", "Buy (latest)"],
    ]);
  });

  it("shows a latest signal the rule did not trade as a circle", () => {
    const markers = strategyMarkers(row({ last_signal: { date: "2026-06-02", action: "sell" } }));

    expect(markers).toEqual([
      expect.objectContaining({ date: "2026-06-02", shape: "circle", position: "aboveBar", text: "Sell signal (latest)" }),
    ]);
    expect(strategyMarkers(row({ error: "Not enough price history" }))).toEqual([]);
    expect(strategyMarkers(undefined)).toEqual([]);
  });

  it("widens the chart to the backtest window", () => {
    expect([1, 3, 5, 10].map(chartPeriodFor)).toEqual(["1y", "3y", "5y", "max"]);
  });
});
