import { HistogramSeries, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useMoney } from "../../hooks/useMoney";

const RECEIVED = "#34d399";
const EXPECTED = "rgba(56, 189, 248, 0.55)";

// Dividends per month or year: received bars, then the expected ones in another colour
const IncomeChart = ({ received, expected = [], height = "h-64" }) => {
  const money = useMoney();
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !(received.length || expected.length)) return undefined;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: "#94a3b8" },
      grid: { vertLines: { visible: false }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      crosshair: { horzLine: { visible: false } },
      localization: { priceFormatter: (p) => money(p, { notation: "compact" }) },
    });
    const series = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false });
    const seen = new Set(received.map((r) => r.time));
    series.setData(
      [
        ...received.map((r) => ({ ...r, color: RECEIVED })),
        ...expected.filter((e) => !seen.has(e.time)).map((e) => ({ ...e, color: EXPECTED })),
      ].sort((a, b) => (a.time < b.time ? -1 : 1)),
    );
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [received, expected, money]);

  return <div ref={containerRef} className={`w-full ${height}`} role="img" aria-label="Dividend income" />;
};

export default IncomeChart;
