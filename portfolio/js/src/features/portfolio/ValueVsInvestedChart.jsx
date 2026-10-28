import { useEffect, useState } from "react";
import { portfolioCalculationsAPI } from "./api";
import LoadingSpinner from "../../shared/ui/Spinner";
import PerformanceSeriesChart from "./PerformanceSeriesChart";

const RANGES = [
  ["3M", "3m"],
  ["6M", "6m"],
  ["1Y", "1y"],
  ["All", "inception"],
];

const ValueVsInvestedChart = ({ portfolioId }) => {
  const [period, setPeriod] = useState("1y");
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!portfolioId) return;
    let cancelled = false;
    setData(null);
    portfolioCalculationsAPI
      .getPerformanceSeries(portfolioId, period)
      .then((res) => !cancelled && setData(res))
      .catch(() => !cancelled && setData({ points: [], error: "History could not be loaded." }));
    return () => {
      cancelled = true;
    };
  }, [portfolioId, period]);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-100">Value vs Invested</h3>
        <div className="flex gap-1">
          {RANGES.map(([label, code]) => (
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
      </div>
      {data === null ? (
        <LoadingSpinner text="Loading history..." centered className="h-80" />
      ) : data.points.length < 2 ? (
        <p className="h-80 flex items-center justify-center text-gray-400 text-center">
          {data.error || "No value history yet."}
        </p>
      ) : (
        <PerformanceSeriesChart points={data.points} />
      )}
    </div>
  );
};

export default ValueVsInvestedChart;
