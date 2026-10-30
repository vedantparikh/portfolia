import { LineSeries, LineStyle, createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useMoney } from "../../hooks/useMoney";

const BANDS = [
  { key: "p90", color: "rgba(56, 189, 248, 0.45)", width: 1 },
  { key: "p75", color: "rgba(56, 189, 248, 0.7)", width: 1 },
  { key: "p50", color: "#38bdf8", width: 3 },
  { key: "p25", color: "rgba(56, 189, 248, 0.7)", width: 1 },
  { key: "p10", color: "rgba(56, 189, 248, 0.45)", width: 1 },
];

// Simulated portfolio value per month: the median and the 10/25/75/90th percentiles, with the goal
const GoalChart = ({ points, goal, height = "h-72" }) => {
  const money = useMoney();
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
      localization: { priceFormatter: (p) => money(p, { notation: "compact" }) },
    });
    BANDS.forEach(({ key, color, width }) => {
      const series = chart.addSeries(LineSeries, {
        color,
        lineWidth: width,
        lineStyle: key === "p50" ? LineStyle.Solid : LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: key === "p50",
      });
      series.setData(points.map((p) => ({ time: p.date, value: p[key] })));
      if (key === "p50" && goal) {
        series.createPriceLine({
          price: goal,
          color: "#fbbf24",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: "Goal",
        });
      }
    });
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [points, goal, money]);

  return <div ref={containerRef} className={`w-full ${height}`} role="img" aria-label="Projected value range" />;
};

export default GoalChart;
