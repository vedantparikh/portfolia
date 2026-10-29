import { useMoney } from "../../hooks/useMoney";
import InfoTip from "../../shared/ui/InfoTip";
import {
  formatPercentage,
  formatPercentagePoints,
  getChangeColor,
} from "../../utils/formatters.jsx";

const Versus = ({ label, info, hint, mine, theirs, diff, format, diffFormat = format, level = false }) => (
  <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-6 py-1.5">
    <div>
      <p className="text-sm text-gray-300">
        {label}
        {info && <InfoTip id={info} className="ml-1.5" />}
      </p>
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
      <h4 className="font-semibold text-gray-100">
        Versus {benchmark?.name || benchmark?.symbol}
        <InfoTip id="benchmark_comparison" className="ml-1.5" />
      </h4>
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
            <Versus label="Profit" info="profit" mine={p.profit} theirs={b.profit} diff={d?.profit} format={signed} />
            <Versus
              label="Return (TWR)" info="twr"
              hint="Ignores when money was added"
              mine={p.twr_pct}
              theirs={b.twr_pct}
              diff={d?.twr_pct}
              format={formatPercentage}
              diffFormat={formatPercentagePoints}
            />
            <Versus
              label="Return (money-weighted)" info="mwr"
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

export default BenchmarkCard;
