import { useMoney } from "../../hooks/useMoney";
import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { portfolioCalculationsAPI } from "../../services/api";
import {
  formatDate,
  formatPercentage,
  formatPercentagePoints,
  formatRatio,
  getChangeColor,
} from "../../utils/formatters.jsx";
import LoadingSpinner from "../../components/shared/LoadingSpinner";
import StatCard from "../../components/shared/StatCard";
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

const Versus = ({ label, hint, mine, theirs, diff, format, diffFormat = format, level = false }) => (
  <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-6 py-1.5">
    <div>
      <p className="text-sm text-gray-300">{label}</p>
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
    <span className={`text-sm font-medium text-right ${level ? "text-gray-100" : getChangeColor(mine)}`}>
      {format(mine)}
    </span>
    <span className={`text-sm text-right ${level ? "text-gray-300" : getChangeColor(theirs)}`}>
      {format(theirs)}
    </span>
    <span className={`text-sm font-medium text-right ${getChangeColor(diff)}`}>{diffFormat(diff)}</span>
  </div>
);

const BenchmarkCard = ({ comparison }) => {
  const money = useMoney();
  const signed = (v) => money(v, { signDisplay: "exceptZero" });
  const { benchmark, portfolio: p, shadow: b, difference: d, warnings = [], error } = comparison;
  return (
    <div className="card p-6">
      <h4 className="font-semibold text-gray-100">Versus {benchmark?.name || benchmark?.symbol}</h4>
      <p className="text-xs text-gray-500 mb-3">
        What the same deposits and withdrawals, on the same days, would have done in{" "}
        {benchmark?.symbol}. Its time-weighted return is the benchmark&apos;s own return.
      </p>
      {error ? (
        <p className="text-sm text-danger-400">{error}</p>
      ) : (
        p &&
        b && (
          <>
            <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-6 text-xs text-gray-500 pb-1 border-b border-gray-700">
              <span />
              <span className="text-right">You</span>
              <span className="text-right">{benchmark.symbol}</span>
              <span className="text-right">Difference</span>
            </div>
            <Versus
              label="Value at end"
              mine={p.end_value}
              theirs={b.end_value}
              diff={d?.end_value}
              format={money}
              diffFormat={signed}
              level
            />
            <Versus label="Profit" mine={p.profit} theirs={b.profit} diff={d?.profit} format={signed} />
            <Versus
              label="Return (TWR)"
              hint="Ignores when money was added"
              mine={p.twr_pct}
              theirs={b.twr_pct}
              diff={d?.twr_pct}
              format={formatPercentage}
              diffFormat={formatPercentagePoints}
            />
            <Versus
              label="Return (money-weighted)"
              hint="Counts when money was added"
              mine={p.mwr_pct}
              theirs={b.mwr_pct}
              diff={d?.mwr_pct}
              format={formatPercentage}
              diffFormat={formatPercentagePoints}
            />
          </>
        )
      )}
      {warnings.map((w) => (
        <p key={w} className="text-xs text-warning-400 mt-2">
          {w}
        </p>
      ))}
    </div>
  );
};

const PortfolioChart = ({ portfolio }) => {
  const money = useMoney();
  const signed = (v) => money(v, { signDisplay: "exceptZero" });
  const [period, setPeriod] = useState("1y");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showCostBasis, setShowCostBasis] = useState(false);
  const [benchmarkOptions, setBenchmarkOptions] = useState([]);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState("");
  const [customSymbol, setCustomSymbol] = useState("");
  const [comparison, setComparison] = useState(null);

  useEffect(() => {
    if (!portfolio?.currency) return;
    portfolioCalculationsAPI
      .getBenchmarkOptions(portfolio.currency)
      .then((r) => setBenchmarkOptions(r.options || []))
      .catch(() => setBenchmarkOptions([]));
  }, [portfolio?.currency]);

  useEffect(() => {
    setComparison(null);
    if (!portfolio?.id || !benchmarkSymbol) return;
    let cancelled = false;
    portfolioCalculationsAPI
      .getBenchmarkComparison(portfolio.id, period, benchmarkSymbol)
      .then((r) => !cancelled && setComparison(r))
      .catch(() => !cancelled && setComparison({ error: "Benchmark could not be loaded." }));
    return () => {
      cancelled = true;
    };
  }, [portfolio?.id, period, benchmarkSymbol]);

  const points = useMemo(() => {
    if (!data?.points || !comparison?.points?.length) return data?.points;
    const byDate = new Map(comparison.points.map((p) => [p.date, p.benchmark_value]));
    return data.points.map((p) => ({ ...p, benchmark_value: byDate.get(p.date) }));
  }, [data, comparison]);

  const load = useCallback(async () => {
    if (!portfolio?.id) return;
    setLoading(true);
    try {
      setData(await portfolioCalculationsAPI.getPerformanceSeries(portfolio.id, period));
    } catch {
      setData({ points: [], error: "Performance could not be loaded." });
    } finally {
      setLoading(false);
    }
  }, [portfolio?.id, period]);

  useEffect(() => {
    setData(null);
    load();
  }, [load]);

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
