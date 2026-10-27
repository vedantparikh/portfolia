import { Bell, CheckCheck } from "lucide-react";
import { formatDateTime, formatDecimal } from "../../utils/formatters.jsx";

const describe = (a) => {
  const at = formatDecimal(a.triggered_value);
  const threshold = formatDecimal(a.threshold_value);
  if (a.alert_type === "percent_change") {
    return `moved ${a.condition === "above" ? "up" : "down"} ${threshold}% or more since added (at ${at})`;
  }
  return a.condition === "above"
    ? `reached ${at} (alert at ${threshold})`
    : `fell to ${at} (alert at ${threshold})`;
};

const WatchlistAlerts = ({ alerts, unreadCount, onAcknowledge, onOpenWatchlist }) => {
  if (!alerts?.length) return null;
  return (
    <div className="card p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="flex items-center gap-2 font-semibold text-gray-100">
          <Bell size={18} className={unreadCount ? "text-warning-400" : "text-gray-400"} />
          Alerts
          {unreadCount > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-warning-500/20 text-warning-300">
              {unreadCount} new
            </span>
          )}
        </h3>
        {unreadCount > 0 && (
          <button
            onClick={() => onAcknowledge(null)}
            className="btn-outline text-xs px-2 py-1 flex items-center gap-1"
          >
            <CheckCheck size={14} /> Mark all read
          </button>
        )}
      </div>
      <p className="text-xs text-gray-500 mb-2">
        Checked in the background every few minutes. An alert fires once when its threshold is
        reached and again only after the price has moved back.
      </p>
      <ul className="divide-y divide-dark-700">
        {alerts.slice(0, 8).map((a) => (
          <li key={a.id} className="py-2 flex items-start gap-3 text-sm">
            <span
              className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                a.acknowledged_at ? "bg-transparent" : "bg-warning-400"
              }`}
            />
            <div className="min-w-0 flex-1">
              <p className="text-gray-200">
                <button
                  onClick={() => onOpenWatchlist(a.watchlist_id)}
                  className="font-semibold hover:underline"
                >
                  {a.symbol}
                </button>{" "}
                {describe(a)}
              </p>
              <p className="text-xs text-gray-500">
                {a.watchlist_name} · {formatDateTime(a.triggered_at)}
                {a.still_true && <span className="ml-2 text-warning-400">still true</span>}
              </p>
            </div>
            {!a.acknowledged_at && (
              <button
                onClick={() => onAcknowledge([a.id])}
                className="text-xs text-gray-400 hover:text-gray-200 shrink-0"
              >
                Mark read
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default WatchlistAlerts;
