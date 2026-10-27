import { useMoney } from "../../hooks/useMoney";
import { AreaSeries, LineSeries, LineStyle, createChart } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { formatDate } from "../../utils/formatters.jsx";

const SERIES = [
  { key: "value", label: "Value", color: "#38bdf8" },
  { key: "invested", label: "Invested", color: "#fbbf24" },
  { key: "cost_basis", label: "Cost basis", color: "#94a3b8" },
  { key: "benchmark_value", label: "Benchmark", color: "#a78bfa" },
];

const PerformanceSeriesChart = ({
  points,
  showCostBasis = false,
  benchmarkLabel = null,
  height = "h-80",
}) => {
  const money = useMoney();
  const showBenchmark = points?.some((p) => p.benchmark_value != null);
  const containerRef = useRef(null);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    if (!containerRef.current || !points?.length) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: "#94a3b8" },
      grid: { vertLines: { visible: false }, horzLines: { color: "#1e293b" } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      crosshair: { horzLine: { visible: false } },
      localization: { priceFormatter: (p) => money(p, { notation: "compact" }) },
    });
    const byTime = new Map(points.map((p) => [p.date, p]));
    const line = (color, dashed) => ({
      color,
      lineWidth: dashed ? 1 : 2,
      lineStyle: dashed ? LineStyle.Dashed : LineStyle.Solid,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chart
      .addSeries(AreaSeries, {
        lineColor: SERIES[0].color,
        topColor: "rgba(56, 189, 248, 0.25)",
        bottomColor: "rgba(56, 189, 248, 0)",
        lineWidth: 2,
        priceLineVisible: false,
      })
      .setData(points.map((p) => ({ time: p.date, value: p.value })));
    chart
      .addSeries(LineSeries, line(SERIES[1].color, false))
      .setData(points.map((p) => ({ time: p.date, value: p.invested })));
    if (showCostBasis) {
      chart
        .addSeries(LineSeries, line(SERIES[2].color, true))
        .setData(points.map((p) => ({ time: p.date, value: p.cost_basis })));
    }
    if (showBenchmark) {
      chart
        .addSeries(LineSeries, line(SERIES[3].color, false))
        .setData(
          points
            .filter((p) => p.benchmark_value != null)
            .map((p) => ({ time: p.date, value: p.benchmark_value }))
        );
    }
    chart.subscribeCrosshairMove((param) => setHover(param.time ? byTime.get(param.time) : null));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [points, showCostBasis, showBenchmark, money]);

  const shown = hover || points?.[points.length - 1];

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 mb-3 text-xs">
        {shown && <span className="text-gray-400">{formatDate(`${shown.date}T12:00:00`)}</span>}
        {SERIES.filter(
          (s) =>
            (s.key !== "cost_basis" || showCostBasis) &&
            (s.key !== "benchmark_value" || showBenchmark)
        ).map((s) => (
          <span key={s.key} className="flex items-center gap-1.5 text-gray-400">
            <span className="w-2.5 h-0.5 rounded" style={{ backgroundColor: s.color }} />
            {s.key === "benchmark_value" && benchmarkLabel ? benchmarkLabel : s.label}
            {shown && <span className="text-gray-100 font-medium">{money(shown[s.key])}</span>}
          </span>
        ))}
      </div>
      {shown?.stale_price && (
        <p className="mb-2 text-xs text-amber-300">
          Valued at a close older than 5 sessions
          {shown.stale_symbols?.length ? `: ${shown.stale_symbols.join(", ")}` : ""}.
        </p>
      )}
      <div ref={containerRef} className={height} />
    </div>
  );
};

export default PerformanceSeriesChart;
