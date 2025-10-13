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
} from "../../utils/formatters.jsx";
import Chart from "../shared/Chart";
import LoadingSpinner from "../shared/LoadingSpinner";

const getYtdDays = () => {
  const today = new Date();
  const startOfYear = new Date(today.getFullYear(), 0, 1);
  const diffInMilliseconds = today - startOfYear;
  const oneDayInMilliseconds = 1000 * 60 * 60 * 24;
  const dayOfYear = Math.floor(diffInMilliseconds / oneDayInMilliseconds) + 1;
  return dayOfYear;
};

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
  const [metricsData, setMetricsData] = useState(null);
  const [advancedMetrics, setAdvancedMetrics] = useState(null);
  const [showMetricsPanel, setShowMetricsPanel] = useState(true);
  const [portfolioConcentration, setPortfolioConcentration] = useState(null);


  const calculateAdvancedMetrics = (performanceData) => {
    if (!performanceData || performanceData.length < 2) {
      setAdvancedMetrics(null);
      return;
    }

    const sortedData = [...performanceData].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    // Daily returns for other calculations
    const dailyReturns = sortedData.slice(1).map((day, i) => {
      const yesterday = sortedData[i];
      return yesterday.value !== 0 ? (day.value - yesterday.value) / yesterday.value : 0;
    });

    if (dailyReturns.length === 0) {
      setAdvancedMetrics({ sortinoRatio: 0, winRate: 0 });
      return;
    }

    // Sortino Ratio
    const negativeReturns = dailyReturns.filter(r => r < 0);
    const avgReturn = dailyReturns.reduce((sum, val) => sum + val, 0) / dailyReturns.length;
    const negVariance = negativeReturns.reduce((sum, val) => sum + Math.pow(val, 2), 0) / dailyReturns.length;
    const downsideDeviation = Math.sqrt(negVariance);
    const sortinoRatio = downsideDeviation > 0 ? (avgReturn / downsideDeviation) * Math.sqrt(252) : Infinity; // Annualized

    // Win Rate
    const winRate = (dailyReturns.filter(r => r > 0).length / dailyReturns.length) * 100;

    setAdvancedMetrics({
      sortinoRatio,
      winRate,
    });
  };
  const calculatePerformanceMetrics = (performanceData) => {
    if (!performanceData || performanceData.length < 2) {
      setMetricsData(null);
      return;
    }

    const sortedData = [...performanceData].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const firstRecord = sortedData[0];
    const lastRecord = sortedData[sortedData.length - 1];

    const endingMarketValue = lastRecord.value;
    const beginningMarketValue = firstRecord.value;

    // Net Cash Flow: The total amount of money added or removed during the period.
    const cashFlow = lastRecord.cost_basis - firstRecord.cost_basis;

    const gainLoss = endingMarketValue - beginningMarketValue - cashFlow;
    const averageCapital = beginningMarketValue + (0.5 * cashFlow);

    let totalReturn = averageCapital !== 0 ? (gainLoss / averageCapital) * 100 : 0;

    const isUnstable = Math.abs(averageCapital) < (Math.abs(beginningMarketValue) * 0.05);
    if (isUnstable) {
      totalReturn = beginningMarketValue !== 0 ? ((endingMarketValue - beginningMarketValue) / beginningMarketValue) * 100 : 0;
    }

    const highValue = Math.max(...sortedData.map((d) => d.value));
    const lowValue = Math.min(...sortedData.map((d) => d.value));

    const dailyReturns = sortedData.slice(1).map((d, i) => {
      const yesterdayValue = sortedData[i].value;
      return yesterdayValue > 0 ? ((d.value - yesterdayValue) / yesterdayValue) * 100 : 0;
    });

    const avgReturn = dailyReturns.reduce((sum, val) => sum + val, 0) / dailyReturns.length;
    const variance = dailyReturns.reduce((sum, val) => sum + Math.pow(val - avgReturn, 2), 0) / dailyReturns.length;
    const volatility = Math.sqrt(variance);

    let peak = -Infinity;
    let maxDrawdown = 0;
    sortedData.forEach((d) => {
      if (d.value > peak) { peak = d.value; }
      const drawdown = peak > 0 ? ((peak - d.value) / peak) * 100 : 0;
      if (drawdown > maxDrawdown) { maxDrawdown = drawdown; }
    });

    setMetricsData({
      totalReturn,
      highValue,
      lowValue,
      volatility,
      maxDrawdown,
      netContributions: cashFlow,
    });
  };

  const chartTypes = [
    { value: "line", label: "Line Chart", icon: TrendingUp },
    { value: "pie", label: "Allocation", icon: PieChart },
  ];

  const loadChartData = useCallback(async () => {
    if (!portfolio?.id) return;

    try {
      setLoading(true);
      setChartData(null);
      const currentTimeRange = chartPeriods.find(
        (tr) => tr.value === timeRange
      );
      const days = currentTimeRange?.days || 30;

      try {
        const historyResponse =
          await analyticsAPI.getPortfolioPerformanceHistory(portfolio.id, days);
        if (historyResponse?.history && historyResponse.history.length > 0) {
          const processedData = processHistoryData([...historyResponse.history].reverse());
          setChartData(processedData);
        }
      } catch (historyError) {
        console.warn(
          "[PortfolioChart] Failed to load performance history:",
          historyError
        );
      }
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
      const holdingsResponse = await portfolioAPI.getPortfolioHoldings(
        portfolio.id
      );
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

        // --- Calculate Largest/Smallest Holding by allocation % ---
        if (allocations && allocations.length > 0) {
          // Filter out any holdings with 0% to find the smallest meaningful position
          const meaningfulAllocations = allocations.filter(h => h.current_percentage > 0);

          if (meaningfulAllocations.length > 0) {
            let largestHolding = meaningfulAllocations[0];
            let smallestHolding = meaningfulAllocations[0];

            for (const holding of meaningfulAllocations) {
              if (holding.current_percentage > largestHolding.current_percentage) {
                largestHolding = holding;
              }
              if (holding.current_percentage < smallestHolding.current_percentage) {
                smallestHolding = holding;
              }
            }
            setPortfolioConcentration({ largest: largestHolding, smallest: smallestHolding });
          } else {
            setPortfolioConcentration(null);
          }
        } else {
          setPortfolioConcentration(null);
        }

      } else {
        setPortfolioConcentration(null);
      }
    } catch (error) {
      console.error("[PortfolioChart] Failed to load allocation data:", error);
    }
  }, [portfolio]);


  const processHistoryData = (historyData) => {
    if (!historyData || historyData.length === 0) {
      setMetricsData(null);
      setAdvancedMetrics(null);
      return null;
    }

    const performanceData = historyData.map((item) => ({
      date: item.snapshot_date || new Date().toISOString(),
      value: parseFloat(item.total_value) || 0,
      cost_basis: parseFloat(item.total_cost_basis) || 0,
    }));

    // Trigger state updates with the processed data
    calculatePerformanceMetrics(performanceData);
    calculateAdvancedMetrics(performanceData);

    // Only return the data needed for the chart
    return {
      performance_data: performanceData,
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
      "#4a90e2", "#50e3c2", "#f5a623", "#bd10e0", "#e86060", "#51af39", "#ffcd45",
      "#7ed321", "#4a4ae2", "#e24a90", "#a16b3f", "#42c2ea", "#9b9b9b", "#ff784f",
      "#8f55e0", "#33d9b2", "#f7d730", "#6a4aeb", "#ff6f61", "#00c7b6",
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
          .sort((a, b) => b.value - a.value)
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
      <div className="h-80 flex flex-col md:flex-row items-center justify-center gap-8">
        <div className="relative w-64 h-64 flex-shrink-0">
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
        <div className="space-y-2 max-h-64 overflow-y-auto w-full md:w-auto">
          {pieData.map((allocation, index) => (
            <div key={index} className="flex items-center space-x-3">
              <div
                className="w-4 h-4 rounded flex-shrink-0"
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
    const commonChartProps = {
      isPortfolioChart: true,
      portfolioData: chartData?.performance_data || [],
      period: timeRange,
      onPeriodChange: setTimeRange,
      height: 320,
      showControls: false,
      showPeriodSelector: false,
      showComparisonLine: true,
      comparisonLineName: "Cost Basis",
      theme: "dark",
      className: "w-full",
    };

    switch (chartType) {
      case "line":
        return <Chart {...commonChartProps} />;
      case "pie":
        return renderPieChart();
      default:
        return <Chart {...commonChartProps} />;
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
            <button
              onClick={() => setShowMetricsPanel(!showMetricsPanel)}
              className="btn-outline text-sm flex items-center space-x-2"
            >
              <Activity size={16} />
              <span>Performance Metrics</span>
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-2 mb-6 overflow-x-auto pb-2">
          {chartPeriods.map((periodOption) => (
            <button
              key={periodOption.value}
              onClick={() => setTimeRange(periodOption.value)}
              className={`px-3 py-1 text-xs rounded-md transition-colors flex-shrink-0 ${timeRange === periodOption.value
                ? "bg-primary-600 text-white font-semibold"
                : "bg-dark-800 text-gray-400 hover:bg-dark-700"
                }`}
            >
              {periodOption.label}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2 mb-6">
          <span className="text-sm text-gray-400">Chart Type:</span>
          {chartTypes.map((type) => {
            const Icon = type.icon;
            return (
              <button
                key={type.value}
                onClick={() => setChartType(type.value)}
                className={`flex items-center space-x-2 px-3 py-1 rounded-lg text-sm font-medium transition-colors ${chartType === type.value
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

        {showMetricsPanel && metricsData && (
          <div className="card p-4 my-4 border border-dark-700">
            <h3 className="text-lg font-semibold text-gray-100 flex items-center mb-4">
              <Activity className="w-5 h-5 mr-2 text-primary-400" />
              Performance Metrics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <p className="text-sm text-gray-400">Total Return</p>
                <p className={`text-lg font-bold ${metricsData.totalReturn >= 0 ? "text-success-400" : "text-danger-400"}`}>
                  {formatPercentage(metricsData.totalReturn || 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Net Contributions</p>
                <p className={`text-lg font-bold ${metricsData.netContributions >= 0 ? "text-success-400" : "text-danger-400"}`}>
                  {formatCurrency(metricsData.netContributions || 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Sortino Ratio</p>
                <p className="text-lg font-bold text-gray-200">
                  {formatMetricValue(advancedMetrics?.sortinoRatio || 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Volatility (Daily)</p>
                <p className="text-lg font-bold text-gray-200">
                  {formatPercentage(metricsData.volatility || 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Max Drawdown</p>
                <p className="text-lg font-bold text-danger-400">
                  -{formatPercentage(metricsData.maxDrawdown || 0, { showSign: false })}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Win Rate</p>
                <p className={`text-lg font-bold ${advancedMetrics?.winRate > 50 ? "text-success-400" : "text-gray-200"}`}>
                  {formatPercentage(advancedMetrics?.winRate || 0)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Largest Holding</p>
                {portfolioConcentration?.largest ? (
                  <>
                    <p className="text-sm font-medium text-gray-200 truncate" title={portfolioConcentration.largest.asset_name}>
                      {portfolioConcentration.largest.asset_name}
                    </p>
                    <p className="text-lg font-bold text-gray-100">
                      {formatPercentage(portfolioConcentration.largest.current_percentage, 1)}
                    </p>
                  </>
                ) : <p className="text-lg font-bold text-gray-500">-</p>}
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-400">Smallest Holding</p>
                {portfolioConcentration?.smallest ? (
                  <>
                    <p className="text-sm font-medium text-gray-200 truncate" title={portfolioConcentration.smallest.asset_name}>
                      {portfolioConcentration.smallest.asset_name}
                    </p>
                    <p className="text-lg font-bold text-gray-100">
                      {formatPercentage(portfolioConcentration.smallest.current_percentage, 1)}
                    </p>
                  </>
                ) : <p className="text-lg font-bold text-gray-500">-</p>}
              </div>
            </div>
          </div>
        )}
        <div className="bg-dark-800 rounded-lg p-4">
          {loading ? (
            <div className="flex items-center justify-center h-80">
              <LoadingSpinner type="ticker" size="lg" text="Loading chart data..." />
            </div>
          ) : chartData ? (
            renderChart()
          ) : (
            <div className="flex items-center justify-center h-80">
              <div className="text-center">
                <BarChart3 size={48} className="text-gray-500 mx-auto mb-4" />
                <p className="text-gray-400">No chart data available for this period.</p>
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