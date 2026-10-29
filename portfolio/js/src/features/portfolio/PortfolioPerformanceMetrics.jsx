import { useMoney } from "../../hooks/useMoney";
import {
  BarChart3,
  Calculator,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  RefreshCw,
  TrendingUp,
  X
} from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  useCalculationPeriods,
  useMultiPeriodPerformance,
  usePortfolioPerformance,
} from "./queries";
import { formatMetricValue, getMetricColor } from "../../utils/formatters.jsx";
import LoadingSpinner from "../../shared/ui/Spinner";
import StatCard from "../../components/shared/StatCard";

const calculationState = (query) =>
  query.isFetching
    ? "calculating"
    : query.isError
      ? "error"
      : query.data
        ? "completed"
        : null;

const PortfolioPerformanceMetrics = ({ portfolio }) => {
  const money = useMoney();
  const [selectedPeriod, setSelectedPeriod] = useState("inception");
  const [expandedMetrics, setExpandedMetrics] = useState(false);
  const [showMultiPeriod, setShowMultiPeriod] = useState(false);

  const { data: availablePeriods = [] } = useCalculationPeriods();
  const performance = usePortfolioPerformance(portfolio?.id, selectedPeriod);
  const multiPeriod = useMultiPeriodPerformance(portfolio?.id, {
    enabled: showMultiPeriod,
  });

  const performanceData = performance.data ?? null;
  const loading = performance.isFetching;
  const calculationStatus = calculationState(performance);
  const calculationMessage = {
    calculating:
      "Calculating portfolio performance metrics... This may take a moment for complex calculations.",
    completed: "Performance metrics calculated successfully!",
    error: "Failed to calculate performance metrics. Please try again.",
  }[calculationStatus] ?? "";
  const loadPerformanceData = () => performance.refetch();

  const multiPeriodData = multiPeriod.data ?? null;
  const multiPeriodLoading = multiPeriod.isFetching;
  const multiPeriodCalculationStatus = calculationState(multiPeriod);
  const multiPeriodCalculationMessage = {
    calculating:
      "Calculating multi-period performance metrics... This may take a moment for complex calculations.",
    completed: "Multi-period performance metrics calculated successfully!",
    error: "Failed to calculate multi-period performance metrics. Please try again.",
  }[multiPeriodCalculationStatus] ?? "";
  const loadMultiPeriodData = () => multiPeriod.refetch();

  useEffect(() => {
    if (performance.isError) toast.error("Failed to load performance metrics");
  }, [performance.isError, performance.errorUpdatedAt]);

  const handleMultiPeriodToggle = () => {
    setShowMultiPeriod(!showMultiPeriod);
  };

  if (!portfolio) {
    return (
      <div className="card p-6 text-center">
        <p className="text-gray-400">No portfolio selected</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-100 flex items-center space-x-2">
            <Calculator size={20} />
            <span>Performance Metrics</span>
          </h3>
          <div className="flex items-center space-x-3">
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(e.target.value)}
              className="input-field text-sm"
            >
              {availablePeriods.map((period) => (
                <option key={period.period_code} value={period.period_code}>
                  {period.period_name}
                </option>
              ))}
            </select>
            <button
              onClick={loadPerformanceData}
              disabled={loading}
              className="btn-outline text-sm flex items-center space-x-2"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Period Description */}
        {availablePeriods.find((p) => p.period_code === selectedPeriod) && (
          <p className="text-sm text-gray-400 mb-4">
            {
              availablePeriods.find((p) => p.period_code === selectedPeriod)
                .description
            }
          </p>
        )}

        {/* Calculation Status for Main Performance */}
        {calculationStatus && calculationStatus !== "completed" && (
          <div
            className={`p-4 rounded-lg mb-4 ${calculationStatus === "calculating"
              ? "bg-warning-600/20 border border-warning-600/30"
              : calculationStatus === "completed"
                ? "bg-success-600/20 border border-success-600/30"
                : "bg-danger-600/20 border border-danger-600/30"
              }`}
          >
            <div className="flex items-center space-x-3">
              {calculationStatus === "calculating" && (
                <RefreshCw className="w-5 h-5 text-warning-400 animate-spin" />
              )}
              {calculationStatus === "completed" && (
                <TrendingUp className="w-5 h-5 text-success-400" />
              )}
              {calculationStatus === "error" && (
                <X className="w-5 h-5 text-danger-400" />
              )}
              <div>
                <p
                  className={`text-sm font-medium ${calculationStatus === "calculating"
                    ? "text-warning-400"
                    : calculationStatus === "completed"
                      ? "text-success-400"
                      : "text-danger-400"
                    }`}
                >
                  {calculationStatus === "calculating" &&
                    "Calculating Performance Metrics"}
                  {calculationStatus === "completed" &&
                    "Performance Metrics Ready"}
                  {calculationStatus === "error" && "Calculation Failed"}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {calculationMessage}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Performance Metrics Grid */}
      {performanceData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            label="CAGR" info="cagr"
            value={formatMetricValue(performanceData.metrics?.cagr, true)}
            valueClassName={getMetricColor(performanceData.metrics?.cagr)}
            sub="Time-weighted, per year"
          />
          <StatCard
            label="XIRR" info="xirr"
            value={formatMetricValue(performanceData.metrics?.xirr, true)}
            valueClassName={getMetricColor(performanceData.metrics?.xirr)}
            sub="Money-weighted, per year"
          />
          <StatCard
            label="TWR" info="twr"
            value={formatMetricValue(performanceData.metrics?.twr, true)}
            valueClassName={getMetricColor(performanceData.metrics?.twr)}
            sub="Time-weighted, this period"
          />
          <StatCard
            label="MWR" info="mwr"
            value={formatMetricValue(performanceData.metrics?.mwr, true)}
            valueClassName={getMetricColor(performanceData.metrics?.mwr)}
            sub="Money-weighted, this period"
          />
        </div>
      )}
      {/* Investment Timing Insight Card */}
      {performanceData?.metrics?.twr != null &&
        performanceData?.metrics?.mwr != null && (
          <div className="card p-6">
            <div className="flex items-center space-x-2 mb-3">
              <Lightbulb size={20} className="text-primary-400" />
              <h4 className="text-lg font-semibold text-gray-100">
                Investment Timing Insight
              </h4>
            </div>
            {/* Dynamic Insight Message */}
            {performanceData.metrics.mwr > performanceData.metrics.twr ? (
              <div className="mb-3">
                <p className="font-semibold text-success-400">
                  Your investment timing has been beneficial.
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Your Money-Weighted Return (MWR) is higher than your
                  Time-Weighted Return (TWR), which suggests you have
                  successfully added capital at opportune times (e.g., buying
                  during market dips).
                </p>
              </div>
            ) : performanceData.metrics.twr > performanceData.metrics.mwr ? (
              <div className="mb-3">
                <p className="font-semibold text-warning-400">
                  Your investment timing may have been suboptimal.
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Your Time-Weighted Return (TWR) is higher than your
                  Money-Weighted Return (MWR). This might indicate that you
                  invested more just before a market downturn or withdrew funds
                  before a rally.
                </p>
              </div>
            ) : (
              <div className="mb-3">
                <p className="font-semibold text-gray-300">
                  Your timing has had a neutral impact.
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Your Money-Weighted and Time-Weighted returns are equal,
                  indicating that the timing of your cash flows did not
                  significantly influence your performance relative to the
                  underlying investments.
                </p>
              </div>
            )}

            <div className="text-xs text-gray-500 border-t border-dark-700 pt-2">
              <strong>Rule of Thumb:</strong> Comparing TWR (pure investment
              performance) and MWR (performance including cash flow timing)
              reveals the impact of your market timing decisions.
            </div>
          </div>
        )}

      {/* Additional Metrics */}
      {performanceData && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-gray-100">
              Additional Metrics
            </h4>
            <button
              onClick={() => setExpandedMetrics(!expandedMetrics)}
              className="btn-outline text-sm flex items-center space-x-2"
            >
              {expandedMetrics ? (
                <>
                  <ChevronUp size={16} />
                  <span>Show Less</span>
                </>
              ) : (
                <>
                  <ChevronDown size={16} />
                  <span>Show More</span>
                </>
              )}
            </button>
          </div>

          <div
            className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 transition-all duration-300 ${expandedMetrics
              ? "max-h-96 opacity-100"
              : "max-h-0 opacity-0 overflow-hidden"
              }`}
          >
            {/* Volatility */}
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-gray-400">Volatility</h5>
              <p
                className={`text-lg font-semibold ${getMetricColor(
                  performanceData.metrics?.volatility
                )}`}
              >
                {formatMetricValue(performanceData.metrics?.volatility, true)}
              </p>
            </div>

            {/* Sharpe Ratio */}
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-gray-400">
                Sharpe Ratio
              </h5>
              <p
                className={`text-lg font-semibold ${getMetricColor(
                  performanceData.metrics?.sharpe_ratio
                )}`}
              >
                {formatMetricValue(performanceData.metrics?.sharpe_ratio)}
              </p>
            </div>

            {/* Max Drawdown */}
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-gray-400">
                Max Drawdown
              </h5>
              <p
                className={`text-lg font-semibold ${getMetricColor(
                  performanceData.metrics?.max_drawdown
                )}`}
              >
                {formatMetricValue(performanceData.metrics?.max_drawdown, true)}
              </p>
            </div>

            {/* Current Value */}
            <div className="space-y-1">
              <h5 className="text-sm font-medium text-gray-400">
                Current Value
              </h5>
              <p className="text-lg font-semibold text-gray-100">
                {money(performanceData.current_value)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Period Performance */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-gray-100">
            Multi-Period Performance
          </h4>
          <button
            onClick={handleMultiPeriodToggle}
            disabled={multiPeriodLoading}
            className="btn-outline text-sm flex items-center space-x-2"
          >
            {multiPeriodLoading ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                <span>Calculating...</span>
              </>
            ) : (
              <>
                <ChevronDown
                  size={16}
                  className={`transition-transform ${showMultiPeriod ? "rotate-180" : ""
                    }`}
                />
                <span>{showMultiPeriod ? "Hide Details" : "Show Details"}</span>
              </>
            )}
          </button>
        </div>

        {/* Multi-Period Content */}
        {showMultiPeriod && (
          <div className="space-y-4">
            {/* Multi-Period Calculation Status */}
            {multiPeriodCalculationStatus && multiPeriodCalculationStatus !== "completed" && (
              <div
                className={`p-4 rounded-lg ${multiPeriodCalculationStatus === "calculating"
                  ? "bg-warning-600/20 border border-warning-600/30"
                  : multiPeriodCalculationStatus === "completed"
                    ? "bg-success-600/20 border border-success-600/30"
                    : "bg-danger-600/20 border border-danger-600/30"
                  }`}
              >
                <div className="flex items-center space-x-3">
                  {multiPeriodCalculationStatus === "calculating" && (
                    <RefreshCw className="w-5 h-5 text-warning-400 animate-spin" />
                  )}
                  {multiPeriodCalculationStatus === "completed" && (
                    <TrendingUp className="w-5 h-5 text-success-400" />
                  )}
                  {multiPeriodCalculationStatus === "error" && (
                    <X className="w-5 h-5 text-danger-400" />
                  )}
                  <div>
                    <p
                      className={`text-sm font-medium ${multiPeriodCalculationStatus === "calculating"
                        ? "text-warning-400"
                        : multiPeriodCalculationStatus === "completed"
                          ? "text-success-400"
                          : "text-danger-400"
                        }`}
                    >
                      {multiPeriodCalculationStatus === "calculating" &&
                        "Calculating Multi-Period Metrics"}
                      {multiPeriodCalculationStatus === "completed" &&
                        "Multi-Period Metrics Ready"}
                      {multiPeriodCalculationStatus === "error" &&
                        "Multi-Period Calculation Failed"}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {multiPeriodCalculationMessage}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Loading State */}
            {multiPeriodLoading && (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <LoadingSpinner type="quantum" size="lg" centered />
                  <p className="text-gray-400 mt-4">
                    Calculating multi-period performance metrics...
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    This may take a moment for complex calculations.
                  </p>
                </div>
              </div>
            )}

            {/* Multi-Period Data */}
            {!multiPeriodLoading && multiPeriodData && (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-dark-700">
                      <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">
                        Period
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                        CAGR
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                        XIRR
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                        TWR
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                        MWR
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {multiPeriodData.periods?.map((period, index) => (
                      <tr
                        key={index}
                        className="border-b border-dark-800 hover:bg-dark-800/50 transition-colors"
                      >
                        <td className="py-3 px-4">
                          <span className="font-medium text-gray-100">
                            {period.period_name}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span
                            className={getMetricColor(period.metrics?.cagr)}
                          >
                            {formatMetricValue(period.metrics?.cagr, true)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span
                            className={getMetricColor(period.metrics?.xirr)}
                          >
                            {formatMetricValue(period.metrics?.xirr, true)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={getMetricColor(period.metrics?.twr)}>
                            {formatMetricValue(period.metrics?.twr, true)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={getMetricColor(period.metrics?.mwr)}>
                            {formatMetricValue(period.metrics?.mwr, true)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Error State */}
            {!multiPeriodLoading &&
              !multiPeriodData &&
              multiPeriodCalculationStatus === "error" && (
                <div className="text-center py-8">
                  <div className="text-danger-400 mb-2">
                    <X size={32} className="mx-auto" />
                  </div>
                  <p className="text-gray-400">
                    Failed to load multi-period performance data
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    {multiPeriodCalculationMessage}
                  </p>
                  <button
                    onClick={loadMultiPeriodData}
                    className="btn-outline text-sm mt-2"
                  >
                    Try Again
                  </button>
                </div>
              )}
          </div>
        )}
      </div>

      <div className="card p-6 flex items-start gap-4">
        <BarChart3 className="w-5 h-5 mt-0.5 text-gray-500 shrink-0" />
        <div>
          <p className="font-medium text-gray-200">Benchmark comparison</p>
          <p className="text-sm text-gray-400 mt-1">
            Open the Performance Chart view and choose &quot;Compare with&quot; to see what the
            same deposits and withdrawals would have earned in an index.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PortfolioPerformanceMetrics;
