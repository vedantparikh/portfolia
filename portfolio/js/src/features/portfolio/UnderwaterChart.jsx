import { AreaSeries, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { formatPercentage } from "../../utils/formatters.jsx";

// How far below its previous peak the portfolio's return curve was, each day (≤ 0 %)
const UnderwaterChart = ({ points, height = "h-48" }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !points?.length) return undefined;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: "#94a3b8" },
      grid: { vertLines: { visible: false }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      crosshair: { horzLine: { visible: false } },
      localization: {
        priceFormatter: (p) => formatPercentage(p, { precision: 1, showSign: false, defaultValue: "0%" }),
      },
    });
    chart
      .addSeries(AreaSeries, {
        lineColor: "#f87171",
        topColor: "rgba(248, 113, 113, 0.05)",
        bottomColor: "rgba(248, 113, 113, 0.35)",
        invertFilledArea: true,
        lineWidth: 1,
        priceLineVisible: false,
      })
      .setData(points.map((p) => ({ time: p.date, value: p.drawdown_pct })));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [points]);

  return <div ref={containerRef} className={`w-full ${height}`} aria-label="Drawdown chart" role="img" />;
};

export default UnderwaterChart;
