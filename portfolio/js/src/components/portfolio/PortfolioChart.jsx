import {
  Activity,
  BarChart3,
  Download,
  PieChart,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import PropTypes from "prop-types";
import { useCallback, useEffect, useState } from "react";
import { analyticsAPI, portfolioAPI } from "../../services/api";
import {
  formatCurrency,
  formatMetricValue,
  formatPercentage,
  getChangeColor,
} from "../../utils/formatters.jsx";
import Chart from "../shared/Chart";

/**
 * Calculates the number of days from the start of the current year to today.
 * @returns {number} The day number of the year (e.g., 1 for Jan 1st, 365 for Dec 31st).
 */
const getYtdDays = () => {
  const today = new Date();
  const startOfYear = new Date(today.getFullYear(), 0, 1); // Month is 0-indexed
  const diffInMilliseconds = today - startOfYear;
  const oneDayInMilliseconds = 1000 * 60 * 60 * 24;

  // Add 1 because we want to include the current day
  const dayOfYear = Math.floor(diffInMilliseconds / oneDayInMilliseconds) + 1;

  return dayOfYear;
};

// We add the 'days' property for the API call logic.
const chartPeriods = [
  { value: "30d", label: "30 Days", days: 30 },
  { value: "3mo", label: "3 Months", days: 90 },
  { value: "6mo", label: "6 Months", days: 180 },
  { value: "ytd", label: "YTD", days: getYtdDays() },
  { value: "1y", label: "1 Year", days: 365 },
  { value: "2y", label: "2 Years", days: 730 },
  { value: "3y", label: "3 Years", days: 1095 },
  { value: "4y", label: "4 Years", days: 1460 },
  { value: "5y", label: "5 Years", days: 1825 },
  { value: "max", label: "All", days: 9999 },
];

const PortfolioChart = ({ portfolio, stats }) => {
  const [chartData, setChartData] = useState(null);
  const [allocationData, setAllocationData] = useState(null);
  const [loading, setLoading] = useState(false);

  const [timeRange, setTimeRange] = useState("30d");
  const [chartType, setChartType] = useState("line");

  const chartTypes = [
    { value: "line", label: "Line Chart", icon: TrendingUp },
    { value: "pie", label: "Allocation", icon: PieChart },
  ];

  const loadChartData = useCallback(async () => {
    if (!portfolio?.id) return;

    try {
      setLoading(true);
      setChartData(null);
      console.log(
        "[PortfolioChart] Loading chart data for portfolio:",
        portfolio.id,
        "timeRange:",
        timeRange
      );

      // Use the updated chartPeriods array to find the duration in days
      const currentTimeRange = chartPeriods.find(
        (tr) => tr.value === timeRange
      );
      const days = currentTimeRange?.days || 30; // Default to 30

      try {
        const historyResponse =
          await analyticsAPI.getPortfolioPerformanceHistory(portfolio.id, days);
        console.log(
          "[PortfolioChart] Performance history response:",
          historyResponse
        );

        if (historyResponse?.history && historyResponse.history.length > 0) {
          const processedData = processHistoryData(historyResponse.history);
          setChartData(processedData);
          return;
        }
      } catch (historyError) {
        console.warn(
          "[PortfolioChart] Failed to load performance history:",
          historyError
        );
      }

      console.log(
        "[PortfolioChart] No performance history data found or API failed."
      );
    } catch (error) {
      console.error("[PortfolioChart] Failed to load chart data:", error);
    } finally {
      setLoading(false);
    }
  }, [portfolio, timeRange]);

  const loadAllocationData = useCallback(async () => {
    if (!portfolio?.id) return;

    try {
      setAllocationData(null);
      console.log(
        "[PortfolioChart] Loading allocation data for portfolio:",
        portfolio.id
      );
      try {
        const holdingsResponse = await portfolioAPI.getPortfolioHoldings(
          portfolio.id
        );
        console.log("[PortfolioChart] Holdings response:", holdingsResponse);

        if (holdingsResponse && holdingsResponse.length > 0) {
          const totalValue = holdingsResponse.reduce(
            (sum, holding) => sum + (parseFloat(holding.current_value) || 0),
            0
          );
          const allocations = holdingsResponse.map((holding) => ({
            asset_id: holding.asset_id,
            asset_symbol: holding.symbol,
            asset_name: holding.name,
            current_percentage:
              totalValue > 0
                ? ((parseFloat(holding.current_value) || 0) / totalValue) * 100
                : 0,
            current_value: parseFloat(holding.current_value) || 0,
          }));

          setAllocationData(allocations);
          return;
        }
      } catch (holdingsError) {
        console.warn(
          "[PortfolioChart] Failed to load holdings:",
          holdingsError
        );
      }
    } catch (error) {
      console.error("[PortfolioChart] Failed to load allocation data:", error);
    }
  }, [portfolio]);

  const processHistoryData = (historyData) => {
    if (!historyData || historyData.length === 0) return null;

    const performanceData = historyData.map((item) => ({
      date:
        item.snapshot_date?.split("T")[0] ||
        new Date().toISOString().split("T")[0],
      value: parseFloat(item.total_value) || 0,
      benchmark: parseFloat(item.total_cost_basis) || 0,
    }));

    const firstValue = performanceData[0]?.value || 0;
    const lastValue = performanceData[performanceData.length - 1]?.value || 0;
    const totalReturn =
      firstValue > 0 ? ((lastValue - firstValue) / firstValue) * 100 : 0;

    return {
      performance_data: performanceData,
      total_return: totalReturn,
      benchmark_return:
        performanceData[performanceData.length - 1]?.benchmark || 0,
      volatility:
        parseFloat(historyData[historyData.length - 1]?.volatility) || 0,
      sharpe_ratio:
        parseFloat(historyData[historyData.length - 1]?.sharpe_ratio) || 0,
      max_drawdown:
        parseFloat(historyData[historyData.length - 1]?.max_drawdown) || 0,
    };
  };
  useEffect(() => {
    if (portfolio?.id) {
      loadChartData();
      loadAllocationData();
    }
  }, [portfolio, timeRange, loadChartData, loadAllocationData]);

  const renderPieChart = () => {
    const allocations = allocationData;
    const colors = [
      "#4a90e2",
      "#50e3c2",
      "#f5a623",
      "#bd10e0",
      "#e86060",
      "#51af39",
      "#ffcd45",
      "#7ed321",
      "#4a4ae2",
      "#e24a90",
      "#a16b3f",
      "#42c2ea",
      "#9b9b9b",
      "#ff784f",
      "#8f55e0",
      "#33d9b2",
      "#f7d730",
      "#6a4aeb",
      "#ff6f61",
      "#00c7b6",
    ];

    const pieData =
      allocations && allocations.length > 0
        ? allocations
            .map((allocation, index) => ({
              name: allocation.asset_name || `Asset ${index + 1}`,
              value: parseFloat(allocation.current_percentage) || 0,
              color: colors[index % colors.length],
              symbol: allocation.asset_symbol || "",
              value_amount: parseFloat(allocation.current_value) || 0,
            }))
            .filter((item) => item.value > 0)
        : [];

    if (pieData.length === 0) {
      return (
        <div className="h-80 flex items-center justify-center">
          <div className="text-center">
            <PieChart size={48} className="text-gray-500 mx-auto mb-4" />
            <p className="text-gray-400">No allocation data available</p>
          </div>
        </div>
      );
    }

    let cumulativePercentage = 0;
    const gradientStops = pieData
      .map((allocation) => {
        const start = cumulativePercentage;
        const end = cumulativePercentage + allocation.value;
        cumulativePercentage = end;
        return `${allocation.color} ${start}% ${end}%`;
      })
      .join(", ");

    const pieStyle = {
      background: `conic-gradient(${gradientStops})`,
    };

    return (
      <div className="h-80 flex items-center justify-center">
        <div className="relative w-64 h-64">
          <div className="w-full h-full rounded-full" style={pieStyle} />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-40 h-40 bg-dark-800 rounded-full flex items-center justify-center">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-100">
                  {formatCurrency(stats?.totalValue || 0)}
                </div>
                <div className="text-sm text-gray-400">Total Value</div>
              </div>
            </div>
          </div>
        </div>
        <div className="ml-8 space-y-2 max-h-64 overflow-y-auto">
          {pieData.map((allocation, index) => (
            <div key={index} className="flex items-center space-x-3">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: allocation.color }}
              ></div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-gray-300 truncate">
                  {allocation.name}
                </div>
                {allocation.symbol && (
                  <div className="text-xs text-gray-500">
                    {allocation.symbol}
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-gray-100">
                  {allocation.value.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500">
                  {formatCurrency(allocation.value_amount)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderChart = () => {
    switch (chartType) {
      case "line":
        return (
          <Chart
            isPortfolioChart={true}
            portfolioData={chartData?.performance_data || []}
            period={timeRange} // Pass the current timeRange as period
            onPeriodChange={setTimeRange} // Pass the setter function
            height={320}
            showVolume={false}
            // We are creating our own controls, so these are false
            showControls={false}
            showPeriodSelector={false}
            showBenchmark={true}
            yAxisMin={0}
            theme="dark"
            className="w-full"
          />
        );
      case "pie":
        return renderPieChart();
      default:
        return (
          <Chart
            isPortfolioChart={true}
            portfolioData={chartData?.performance_data || []}
            period={timeRange}
            onPeriodChange={setTimeRange}
            height={320}
            showVolume={false}
            showControls={false}
            showPeriodSelector={false}
            showBenchmark={true}
            yAxisMin={0}
            theme="dark"
            className="w-full"
          />
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-100">
            Portfolio Performance
          </h3>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                loadChartData();
                loadAllocationData();
              }}
              disabled={loading}
              className="btn-outline text-sm flex items-center space-x-2"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
              <span>Refresh</span>
            </button>
            <button className="btn-outline text-sm flex items-center space-x-2">
              <Download size={16} />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex items-center space-x-2 mb-6">
          {chartPeriods.map((periodOption) => (
            <button
              key={periodOption.value}
              onClick={() => setTimeRange(periodOption.value)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                timeRange === periodOption.value
                  ? "bg-primary-600 text-white font-semibold"
                  : "bg-dark-800 text-gray-400 hover:bg-dark-700"
              }`}
            >
              {periodOption.label}
            </button>
          ))}
        </div>

        {/* Chart Type Selector */}
        <div className="flex items-center space-x-2 mb-6">
          <span className="text-sm text-gray-400">Chart Type:</span>
          {chartTypes.map((type) => {
            const Icon = type.icon;
            return (
              <button
                key={type.value}
                onClick={() => setChartType(type.value)}
                className={`flex items-center space-x-2 px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                  chartType === type.value
                    ? "bg-primary-600 text-white"
                    : "bg-dark-700 text-gray-300 hover:bg-dark-600"
                }`}
              >
                <Icon size={16} />
                <span>{type.label}</span>
              </button>
            );
          })}
        </div>

        {/* Chart */}
        <div className="bg-dark-800 rounded-lg p-4">
          {loading ? (
            <div className="flex items-center justify-center h-80">
              <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
              <span className="ml-2 text-gray-400">Loading chart data...</span>
            </div>
          ) : chartData ? (
            renderChart()
          ) : (
            <div className="flex items-center justify-center h-80">
              <div className="text-center">
                <BarChart3 size={48} className="text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400">No chart data available</p>
                <button
                  onClick={loadChartData}
                  className="mt-2 text-primary-400 hover:text-primary-300 text-sm"
                >
                  Try again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {chartData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Total Return</p>
                <p
                  className={`text-2xl font-bold ${getChangeColor(
                    chartData.total_return || 0
                  )}`}
                >
                  {formatPercentage(chartData.total_return || 0)}
                </p>
              </div>
              <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                <TrendingUp size={24} className="text-primary-400" />
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Volatility</p>
                <p className="text-2xl font-bold text-gray-100">
                  {formatPercentage(chartData.volatility || 0, {
                    precision: 1,
                  })}
                </p>
              </div>
              <div className="w-12 h-12 bg-warning-600/20 rounded-lg flex items-center justify-center">
                <Activity size={24} className="text-warning-400" />
              </div>
            </div>
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">Sharpe Ratio</p>
                <p className="text-2xl font-bold text-gray-100">
                  {formatMetricValue(chartData.sharpe_ratio || 0)}
                </p>
              </div>
              <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                <TrendingUp size={24} className="text-success-400" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

PortfolioChart.propTypes = {
  portfolio: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  }),
  stats: PropTypes.shape({
    totalValue: PropTypes.number,
  }),
};

export default PortfolioChart;
