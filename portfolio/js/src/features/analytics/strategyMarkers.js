const BUY = "#22c55e";
const SELL = "#ef4444";

// Chart markers for one backtest row: an arrow for each trade's buy and sell, and a
// label on the rule's latest call (labels on every trade overlap when trades cluster)
export const strategyMarkers = (row) => {
  if (!row || row.error) return [];
  const markers = [];
  for (const trade of row.trades) {
    markers.push({ date: trade.entry_date, position: "belowBar", shape: "arrowUp", color: BUY });
    if (!trade.open) {
      markers.push({ date: trade.exit_date, position: "aboveBar", shape: "arrowDown", color: SELL });
    }
  }
  const latest = row.last_signal;
  if (latest) {
    const buy = latest.action === "buy";
    const arrow = buy ? "arrowUp" : "arrowDown";
    const traded = markers.find((marker) => marker.date === latest.date && marker.shape === arrow);
    if (traded) {
      traded.text = `${buy ? "Buy" : "Sell"} (latest)`;
    } else {
      markers.push({
        date: latest.date,
        position: buy ? "belowBar" : "aboveBar",
        shape: "circle",
        color: buy ? BUY : SELL,
        text: `${buy ? "Buy" : "Sell"} signal (latest)`,
      });
    }
  }
  return markers;
};

// Chart period that covers a backtest window of `years`
export const chartPeriodFor = (years) => ({ 1: "1y", 3: "3y", 5: "5y" })[years] ?? "max";
