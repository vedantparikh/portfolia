import { useMoney } from "../../hooks/useMoney";
import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import {
  useBenchmarkComparison,
  useBenchmarkOptions,
  usePerformanceSeries,
} from "./queries";
import {
  formatDate,
  formatPercentage,
  formatRatio,
  getChangeColor,
} from "../../utils/formatters.jsx";
import LoadingSpinner from "../../shared/ui/Spinner";
import StatCard from "../../components/shared/StatCard";
import BenchmarkCard from "./BenchmarkCard";
import PerformanceSeriesChart from "./PerformanceSeriesChart";

const PERIODS = [
  ["1M", "1m"],
  ["3M", "3m"],
  ["6M", "6m"],
  ["YTD", "ytd"],
  ["1Y", "1y"],
  ["2Y", "2y"],
  ["3Y", "3y"],
  ["All", "inception"],
];

const day = (d) => formatDate(`${d}T12:00:00`);

const Row = ({ label, hint, value, className = "text-gray-100" }) => (
  <div className="flex items-center justify-between gap-4 py-1.5">
    <div>
      <p className="text-sm text-gray-300">{label}</p>
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
    <span className={`text-sm font-medium shrink-0 ${className}`}>{value}</span>
  </div>
);

const PortfolioChart = ({ portfolio }) => {
  const money = useMoney();
  const signed = (v) => money(v, { signDisplay: "exceptZero" });
  const [period, setPeriod] = useState("1y");
  const [showCostBasis, setShowCostBasis] = useState(false);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState("");
  const [customSymbol, setCustomSymbol] = useState("");
  const { data: benchmarkOptions = [] } = useBenchmarkOptions(portfolio?.currency);
  const benchmark = useBenchmarkComparison(portfolio?.id, period, benchmarkSymbol);
  const comparison = useMemo(() => {
    if (!benchmarkSymbol) return null;
    if (benchmark.isError) return { error: "Benchmark could not be loaded." };
    return benchmark.data ?? null;
  }, [benchmarkSymbol, benchmark.isError, benchmark.data]);
  const series = usePerformanceSeries(portfolio?.id, period);
  const data = useMemo(
    () =>
      series.isError
        ? { points: [], error: "Performance could not be loaded." }
        : series.data ?? null,
    [series.isError, series.data]
  );
  const loading = series.isFetching;
  const load = () => series.refetch();

  const points = useMemo(() => {
    if (!data?.points || !comparison?.points?.length) return data?.points;
    const byDate = new Map(comparison.points.map((p) => [p.date, p.benchmark_value]));
    return data.points.map((p) => ({ ...p, benchmark_value: byDate.get(p.date) }));
  }, [data, comparison]);

  const s = data?.summary;

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <h3 className="text-lg font-semibold text-gray-100">Performance</h3>
          <div className="flex items-center gap-3">
            <div className="flex flex-wrap gap-1">
              {PERIODS.map(([label, code]) => (
                <button
                  key={code}
                  onClick={() => setPeriod(code)}
                  className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                    period === code ? "bg-primary-600 text-white" : "text-gray-400 hover:bg-dark-700"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <button
              onClick={load}
              disabled={loading}
              aria-label="Refresh"
              className="btn-outline text-sm p-2"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>

        {data === null ? (
          <LoadingSpinner text="Calculating performance..." centered className="h-80" />
        ) : !s || data.points.length < 2 ? (
          <p className="h-80 flex items-center justify-center text-gray-400 text-center">
            {data.error || "Not enough history for this period yet."}
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <StatCard
                label="Value"
                value={money(s.end_value)}
                sub={s.start_value ? `from ${money(s.start_value)}` : "Since the first trade"}
              />
              <StatCard
                label="Profit"
                value={signed(s.profit)}
                valueClassName={getChangeColor(s.profit)}
                sub={
                  s.net_contributions < 0
                    ? `${money(-s.net_contributions)} net withdrawn`
                    : `${money(s.net_contributions)} net added`
                }
              />
              <StatCard
                label="Return (TWR)"
                value={formatPercentage(s.twr_pct)}
                valueClassName={getChangeColor(s.twr_pct)}
                sub={
                  s.twr_annualized_pct != null
                    ? `${formatPercentage(s.twr_annualized_pct)} a year`
                    : "Ignores when money was added"
                }
              />
              <StatCard
                label="Return (money-weighted)"
                value={formatPercentage(s.mwr_pct)}
                valueClassName={getChangeColor(s.mwr_pct)}
                sub={
                  s.twr_annualized_pct != null
                    ? `${formatPercentage(s.mwr_annualized_pct)} a year`
                    : "Counts when money was added"
                }
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
              <p className="text-xs text-gray-500">
                Invested = value at the start of the period plus deposits minus withdrawals since.
              </p>
              <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showCostBasis}
                  onChange={(e) => setShowCostBasis(e.target.checked)}
                />
                Show cost basis
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-2 mb-3 text-sm">
              <span className="text-gray-400">Compare with</span>
              <select
                className="input-field py-1 text-sm w-auto"
                value={benchmarkOptions.some((o) => o.symbol === benchmarkSymbol) ? benchmarkSymbol : benchmarkSymbol ? "custom" : ""}
                onChange={(e) =>
                  setBenchmarkSymbol(e.target.value === "custom" ? customSymbol : e.target.value)
                }
              >
                <option value="">No benchmark</option>
                {benchmarkOptions.map((o) => (
                  <option key={o.symbol} value={o.symbol}>
                    {o.name} ({o.symbol})
                  </option>
                ))}
                <option value="custom">Other ticker…</option>
              </select>
              {benchmarkSymbol && !benchmarkOptions.some((o) => o.symbol === benchmarkSymbol) && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    setBenchmarkSymbol(customSymbol.trim().toUpperCase());
                  }}
                >
                  <input
                    className="input-field py-1 text-sm w-36"
                    placeholder="Yahoo ticker"
                    value={customSymbol}
                    onChange={(e) => setCustomSymbol(e.target.value)}
                  />
                </form>
              )}
              {benchmarkSymbol && !comparison && <LoadingSpinner size="sm" text={null} />}
            </div>
            <PerformanceSeriesChart
              points={points}
              showCostBasis={showCostBasis}
              benchmarkLabel={
                comparison?.benchmark ? `Same money in ${comparison.benchmark.symbol}` : null
              }
            />
          </>
        )}
      </div>

      {benchmarkSymbol && comparison && (
        <BenchmarkCard comparison={comparison} />
      )}

      {s && data.points.length >= 2 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <h4 className="font-semibold text-gray-100 mb-2">Risk</h4>
            <Row
              label="Max drawdown"
              hint="Worst fall from a peak in this period"
              value={formatPercentage(s.max_drawdown_pct)}
            />
            <Row
              label="Volatility"
              hint="Annualised swing of daily returns"
              value={formatPercentage(s.volatility_pct, { showSign: false })}
            />
            <Row label="Sharpe ratio" hint="Return per unit of risk (3% risk-free)" value={formatRatio(s.sharpe_ratio)} />
            {s.best_day && (
              <Row
                label="Best day"
                hint={day(s.best_day.date)}
                value={formatPercentage(s.best_day.return_pct)}
                className={getChangeColor(s.best_day.return_pct)}
              />
            )}
            {s.worst_day && (
              <Row
                label="Worst day"
                hint={day(s.worst_day.date)}
                value={formatPercentage(s.worst_day.return_pct)}
                className={getChangeColor(s.worst_day.return_pct)}
              />
            )}
          </div>
          <div className="card p-6">
            <h4 className="font-semibold text-gray-100 mb-2">Money in and out</h4>
            <Row label="Period" value={`${day(s.start_date)} – ${day(s.end_date)}`} hint={`${s.trading_days} trading days`} />
            <Row label="Value at start" value={money(s.start_value)} />
            <Row label="Deposits" hint="Buys, including fees" value={money(s.deposits)} />
            <Row label="Withdrawals" hint="Sale proceeds and dividends" value={money(s.withdrawals)} />
            <Row label="Value at end" value={money(s.end_value)} />
            <Row
              label="Profit"
              hint="End − start − net deposits"
              value={signed(s.profit)}
              className={getChangeColor(s.profit)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioChart;
