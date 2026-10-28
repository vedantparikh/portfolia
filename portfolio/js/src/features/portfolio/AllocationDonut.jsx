import { useMoney } from "../../hooks/useMoney";
import { useAllocationAnalysis } from "./queries";
import { formatPercentage } from "../../utils/formatters.jsx";
import LoadingSpinner from "../../shared/ui/Spinner";

const COLORS = [
  "#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa",
  "#2dd4bf", "#fb923c", "#60a5fa", "#a3e635", "#e879f9", "#94a3b8",
];

const Ring = ({ items, radius, width, valueKey }) => {
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  return items.map((item) => {
    const length = (item[valueKey] / 100) * circumference;
    const segment = (
      <circle
        key={item.asset_id}
        r={radius}
        cx="80"
        cy="80"
        fill="none"
        stroke={item.color}
        strokeWidth={width}
        strokeDasharray={`${Math.max(length - 1, 0)} ${circumference}`}
        strokeDashoffset={-offset}
      >
        <title>{`${item.asset_symbol}: ${formatPercentage(item[valueKey], { showSign: false, precision: 1 })}`}</title>
      </circle>
    );
    offset += length;
    return segment;
  });
};

const AllocationDonut = ({ portfolioId }) => {
  const money = useMoney();
  const query = useAllocationAnalysis(portfolioId);
  const analysis = query.data ?? null;

  if (query.isError) {
    return <p className="text-center text-gray-400 py-8">Allocation could not be loaded.</p>;
  }
  if (!analysis) {
    return <LoadingSpinner text="Loading allocation..." centered className="py-8" />;
  }

  const drift = new Map(
    (analysis.allocation_drift || []).map((d) => [d.asset_id, Number(d.drift_percentage)])
  );
  const items = (analysis.current_allocations || [])
    .map((a) => ({
      ...a,
      current: Number(a.current_percentage) || 0,
      target: Number(a.target_percentage) || 0,
      drift: drift.get(a.asset_id),
    }))
    .sort((a, b) => b.current - a.current)
    .map((a, i) => ({ ...a, color: COLORS[i % COLORS.length] }));
  const hasTargets = items.some((a) => a.target > 0);

  if (items.length === 0) {
    return <p className="text-center text-gray-400 py-8">No holdings to display allocation for</p>;
  }

  return (
    <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
      <div className="shrink-0 text-center">
        <svg width="160" height="160" viewBox="0 0 160 160" className="-rotate-90">
          <circle r="66" cx="80" cy="80" fill="none" stroke="currentColor" strokeWidth="18" className="text-dark-700" />
          <Ring items={items} radius={66} width={18} valueKey="current" />
          {hasTargets && <Ring items={items} radius={50} width={5} valueKey="target" />}
        </svg>
        {hasTargets && (
          <p className="text-xs text-gray-500 mt-2">Outer: current · Inner: target</p>
        )}
      </div>
      <div className="w-full min-w-0">
        <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 text-xs text-gray-500 pb-2 border-b border-dark-700">
          <span>Holding</span>
          <span className="text-right">Weight</span>
          <span className="text-right w-20">{hasTargets ? "vs target" : "Value"}</span>
        </div>
        {items.map((a) => (
          <div key={a.asset_id} className="grid grid-cols-[1fr_auto_auto] gap-x-4 items-center py-1.5 text-sm">
            <span className="flex items-center gap-2 min-w-0" title={a.asset_name}>
              <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: a.color }} />
              <span className="text-gray-100 font-medium">{a.asset_symbol}</span>
              <span className="text-gray-500 truncate hidden md:inline">{a.asset_name}</span>
            </span>
            <span className="text-right text-gray-100">
              {formatPercentage(a.current, { showSign: false, precision: 1 })}
            </span>
            <span className="text-right w-20 text-gray-400">
              {hasTargets
                ? a.drift != null
                  ? formatPercentage(a.drift, { precision: 1 })
                  : "—"
                : money(Number(a.current_value), { notation: "compact" })}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AllocationDonut;
