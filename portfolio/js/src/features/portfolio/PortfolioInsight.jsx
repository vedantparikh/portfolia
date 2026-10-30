import { Lightbulb } from "lucide-react";
import { Fragment, useMemo, useState } from "react";

import StatCard from "../../components/shared/StatCard";
import { useMoney } from "../../hooks/useMoney";
import InfoTip from "../../shared/ui/InfoTip";
import LoadingSpinner from "../../shared/ui/Spinner";
import {
  formatDate,
  formatPercentage,
  formatPercentagePoints,
  getChangeColor,
} from "../../utils/formatters.jsx";
import { usePerformanceInsight } from "./queries";
import UnderwaterChart from "./UnderwaterChart";

const PERIODS = [
  ["YTD", "ytd"],
  ["1Y", "1y"],
  ["3Y", "3y"],
  ["5Y", "5y"],
  ["All", "inception"],
];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const COLLAPSED = 10;

const day = (d) => formatDate(`${d}T12:00:00`);
const pct = (v) => formatPercentage(v, { precision: 1 });

// Green or red, stronger the further from zero (full at ±10 %)
const heat = (value) => {
  if (value == null) return undefined;
  const alpha = Math.min(Math.abs(value) / 10, 1) * 0.55 + 0.08;
  return { backgroundColor: value >= 0 ? `rgba(34, 197, 94, ${alpha})` : `rgba(239, 68, 68, ${alpha})` };
};

const Card = ({ title, info, children, subtitle }) => (
  <div className="card p-6">
    <h3 className="text-lg font-semibold text-gray-100 flex items-center">
      {title}
      {info && <InfoTip id={info} className="ml-2" />}
    </h3>
    {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    <div className="mt-4">{children}</div>
  </div>
);

const Contributions = ({ rows }) => {
  const money = useMoney();
  const [all, setAll] = useState(false);
  const largest = Math.max(...rows.map((r) => Math.abs(r.contribution_pp)), 0.01);
  // Collapsed: the biggest gains and the biggest drags, the middle hidden
  const shown =
    all || rows.length <= COLLAPSED ? rows : [...rows.slice(0, COLLAPSED - 3), null, ...rows.slice(-3)];

  return (
    <>
      <div className="space-y-2">
        {shown.map((row, i) =>
          row === null ? (
            <p key="gap" className="text-center text-xs text-gray-500">
              · · · {rows.length - COLLAPSED} more · · ·
            </p>
          ) : (
            <div
              key={row.asset_id}
              className="grid grid-cols-[minmax(0,7rem)_1fr_9.5rem] sm:grid-cols-[minmax(0,10rem)_1fr_12rem] items-center gap-3 text-sm"
            >
              <div className="min-w-0">
                <p className="font-medium text-gray-100 truncate">
                  {row.symbol}
                  {row.end_value === 0 && <span className="ml-1.5 text-xs font-normal text-gray-500">sold</span>}
                </p>
                <p className="text-xs text-gray-500 truncate">{row.name}</p>
              </div>
              <div className="relative h-4" aria-hidden="true">
                <div className="absolute inset-y-0 left-1/2 w-px bg-dark-600" />
                <div
                  className={`absolute inset-y-0.5 rounded-sm ${row.contribution_pp >= 0 ? "bg-success-500/70" : "bg-danger-500/70"}`}
                  style={
                    row.contribution_pp >= 0
                      ? { left: "50%", width: `${(row.contribution_pp / largest) * 50}%` }
                      : { right: "50%", width: `${(-row.contribution_pp / largest) * 50}%` }
                  }
                />
              </div>
              <div className="text-right whitespace-nowrap" data-testid={`contribution-${i}`}>
                <span className={`font-medium ${getChangeColor(row.profit)}`}>
                  {money(row.profit, { signDisplay: "exceptZero" })}
                </span>
                <span className={`ml-2 text-xs ${getChangeColor(row.contribution_pp)}`}>
                  {formatPercentagePoints(row.contribution_pp)}
                </span>
                {row.currency_effect != null && Math.abs(row.currency_effect) >= 0.005 && (
                  <p className="text-xs text-gray-500">
                    {money(row.currency_effect, { signDisplay: "exceptZero" })} from {row.quote_currency}
                  </p>
                )}
              </div>
            </div>
          ),
        )}
      </div>
      {rows.length > COLLAPSED && (
        <button
          type="button"
          onClick={() => setAll(!all)}
          className="mt-3 text-xs text-primary-400 hover:text-primary-300"
        >
          {all ? "Show fewer" : `Show all ${rows.length} holdings`}
        </button>
      )}
    </>
  );
};

const MonthlyReturns = ({ months, years, benchmark }) => {
  const byYear = useMemo(() => {
    const grid = new Map();
    for (const m of months) {
      const [year, month] = m.period.split("-");
      if (!grid.has(year)) grid.set(year, Array(12).fill(null));
      grid.get(year)[Number(month) - 1] = m;
    }
    return grid;
  }, [months]);
  const yearRow = new Map(years.map((y) => [y.period, y]));
  const label = benchmark?.symbol ?? "Benchmark";

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] text-xs">
        <thead className="text-gray-500">
          <tr>
            <th className="text-left font-normal py-1">Year</th>
            {MONTHS.map((m) => (
              <th key={m} className="font-normal">
                {m}
              </th>
            ))}
            <th className="font-normal pl-3">Year</th>
            <th className="font-normal">{label}</th>
            <th className="font-normal">Difference</th>
          </tr>
        </thead>
        <tbody>
          {[...byYear.entries()].reverse().map(([year, cells]) => {
            const total = yearRow.get(year);
            const versus =
              total?.benchmark_pct == null ? null : total.return_pct - total.benchmark_pct;
            return (
              <tr key={year}>
                <td className="py-1 pr-2 font-medium text-gray-300">{year}</td>
                {cells.map((cell, i) => (
                  <td key={i} className="p-0.5">
                    {cell && (
                      <div
                        style={heat(cell.return_pct)}
                        title={`${MONTHS[i]} ${year}: ${pct(cell.return_pct)}${
                          cell.benchmark_pct == null ? "" : `, ${label} ${pct(cell.benchmark_pct)}`
                        }${cell.partial ? " (part of the month)" : ""}`}
                        className="rounded px-1 py-1.5 text-center text-gray-100"
                      >
                        {pct(cell.return_pct)}
                        {cell.partial && <span className="text-gray-300">*</span>}
                      </div>
                    )}
                  </td>
                ))}
                <td className={`pl-3 text-center font-semibold ${getChangeColor(total?.return_pct)}`}>
                  {total ? pct(total.return_pct) : ""}
                  {total?.partial && <span className="text-gray-400">*</span>}
                </td>
                <td className={`text-center ${getChangeColor(total?.benchmark_pct)}`}>
                  {total?.benchmark_pct == null ? "—" : pct(total.benchmark_pct)}
                </td>
                <td className={`text-center ${getChangeColor(versus)}`}>
                  {versus == null ? "—" : formatPercentagePoints(versus, { precision: 1 })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-500">* only part of the month or year is in the period.</p>
    </div>
  );
};

const Drawdowns = ({ drawdown }) => (
  <>
    <UnderwaterChart points={drawdown.points} />
    {drawdown.episodes.length === 0 ? (
      <p className="mt-3 text-sm text-gray-400">No fall below a previous high in this period.</p>
    ) : (
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead className="text-xs text-gray-500 border-b border-dark-700">
            <tr>
              <th className="text-left font-normal py-2">Peak</th>
              <th className="text-left font-normal">Low</th>
              <th className="text-right font-normal">Fall</th>
              <th className="text-right font-normal">Days down</th>
              <th className="text-left font-normal pl-4">Back at the peak</th>
              <th className="text-right font-normal">Days to recover</th>
            </tr>
          </thead>
          <tbody>
            {drawdown.episodes.map((e) => (
              <tr key={e.peak_date} className="border-b border-dark-800 text-gray-300">
                <td className="py-2">{day(e.peak_date)}</td>
                <td>{day(e.trough_date)}</td>
                <td className="text-right text-danger-400">{pct(e.depth_pct)}</td>
                <td className="text-right">{e.days_to_trough}</td>
                <td className="pl-4">{e.recovery_date ? day(e.recovery_date) : <span className="text-warning-400">not yet</span>}</td>
                <td className="text-right">{e.days_to_recover ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </>
);

// What drove the period's return (core/domain/insight.py); the numbers come from the API
const PortfolioInsight = ({ portfolio }) => {
  const money = useMoney();
  const signed = (v) => money(v, { signDisplay: "exceptZero" });
  const [period, setPeriod] = useState("inception");
  const { data, isPending, isError, isFetching } = usePerformanceInsight(portfolio?.id, period);
  const timing = data?.timing;
  const fx = data?.currency_effect;
  const drawdown = data?.drawdown;

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-gray-100 flex items-center">
              <Lightbulb className="w-5 h-5 mr-2 text-primary-400" />
              Performance insight
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              What drove the return: which holdings, which months, how deep the falls were, and what timing and
              currencies added.
              {data?.start_date && ` ${day(data.start_date)} – ${day(data.end_date)}.`}
            </p>
          </div>
          <div role="group" aria-label="Period" className="flex rounded-lg bg-dark-800 p-0.5 text-xs">
            {PERIODS.map(([label, value]) => (
              <button
                key={value}
                type="button"
                aria-pressed={period === value}
                onClick={() => setPeriod(value)}
                className={`px-3 py-1.5 rounded-md ${period === value ? "bg-primary-600 text-white" : "text-gray-400 hover:text-gray-200"}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isPending ? (
        <LoadingSpinner centered text="Working out what drove the return..." />
      ) : isError ? (
        <div className="card p-6 text-sm text-gray-400">The insight could not be loaded.</div>
      ) : data.error ? (
        <div className="card p-6 text-sm text-warning-400">{data.error}</div>
      ) : !data.contributions.length ? (
        <div className="card p-6 text-sm text-gray-400">No transactions in this portfolio yet.</div>
      ) : (
        <div className={`space-y-6 ${isFetching ? "opacity-60 transition-opacity" : ""}`}>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Return (time-weighted)" info="twr" value={pct(data.twr_pct)} valueClassName={getChangeColor(data.twr_pct)} />
            <StatCard
              label="Timing effect"
              info="timing_effect"
              value={timing ? signed(timing.timing_effect) : "—"}
              valueClassName={getChangeColor(timing?.timing_effect)}
            />
            <StatCard
              label="Currency effect"
              info="currency_effect"
              value={fx?.by_currency.length ? signed(fx.total) : "None"}
              valueClassName={getChangeColor(fx?.total)}
            />
            <StatCard
              label="Below the peak today"
              info="drawdown_recovery"
              value={drawdown?.current_pct ? pct(drawdown.current_pct) : "At a high"}
              valueClassName={drawdown?.current_pct ? "text-danger-400" : "text-success-400"}
            />
          </div>

          <Card
            title="What drove the return"
            info="contribution"
            subtitle="Profit per holding in this period, and its share of the return in percentage points. Sold holdings count too; the parts add up to the total."
          >
            <Contributions rows={data.contributions} />
          </Card>

          <Card
            title="Monthly and yearly returns"
            info="calendar_returns"
            subtitle={`Time-weighted, so deposits and withdrawals do not distort them; compared with ${
              data.benchmark?.name ?? data.benchmark?.symbol ?? "the benchmark"
            } over the same days.`}
          >
            {data.benchmark?.note && <p className="mb-3 text-xs text-warning-400">{data.benchmark.note}</p>}
            {data.benchmark?.error && <p className="mb-3 text-xs text-warning-400">{data.benchmark.error}</p>}
            <MonthlyReturns months={data.months} years={data.years} benchmark={data.benchmark} />
          </Card>

          {drawdown && (
            <Card
              title="Drawdowns and recovery"
              info="drawdown_recovery"
              subtitle={`How far below its previous high the portfolio was. Deepest: ${pct(drawdown.max_pct)}.`}
            >
              <Drawdowns drawdown={drawdown} />
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {timing && (
              <Card title="Timing of your money" info="timing_effect">
                <dl className="grid grid-cols-[1fr_auto] gap-y-1.5 text-sm">
                  <dt className="text-gray-400">Your profit</dt>
                  <dd className={`text-right ${getChangeColor(timing.profit)}`}>{signed(timing.profit)}</dd>
                  <dt className="text-gray-400">Same deposits at a steady rate</dt>
                  <dd className={`text-right ${getChangeColor(timing.steady_profit)}`}>{signed(timing.steady_profit)}</dd>
                  <dt className="text-gray-300 font-medium">Timing effect</dt>
                  <dd className={`text-right font-medium ${getChangeColor(timing.timing_effect)}`}>
                    {signed(timing.timing_effect)}
                  </dd>
                </dl>
                <p className="mt-3 text-xs text-gray-500">
                  {timing.timing_effect >= 0
                    ? "More of your money was invested before the better days than a steady path would assume."
                    : "More of your money arrived before weaker days (or left before stronger ones) than a steady path would assume."}
                </p>
              </Card>
            )}
            {fx && (
              <Card title="Currency" info="currency_effect">
                {fx.by_currency.length === 0 ? (
                  <p className="text-sm text-gray-400">
                    Every holding is quoted in {data.currency}, so exchange rates played no part.
                  </p>
                ) : (
                  <>
                    <dl className="grid grid-cols-[1fr_auto] gap-y-1.5 text-sm">
                      {fx.by_currency.map((row) => (
                        <Fragment key={row.currency}>
                          <dt className="text-gray-400">
                            {row.currency} → {data.currency}
                          </dt>
                          <dd className={`text-right ${getChangeColor(row.effect)}`}>{signed(row.effect)}</dd>
                        </Fragment>
                      ))}
                      <dt className="text-gray-300 font-medium">From prices and dividends</dt>
                      <dd className={`text-right font-medium ${getChangeColor(fx.profit - fx.total)}`}>
                        {signed(fx.profit - fx.total)}
                      </dd>
                    </dl>
                    <p className="mt-3 text-xs text-gray-500">
                      Of the period&apos;s profit of {signed(fx.profit)}, {signed(fx.total)} came from exchange rates.
                    </p>
                  </>
                )}
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioInsight;
