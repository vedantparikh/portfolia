import {
  BarChart3,
  Calculator,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import PropTypes from "prop-types";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { marketAPI, portfolioCalculationsAPI } from "../../services/api";
import {
  formatCurrency,
  formatPercentage,
  formatMetricValue,
  getMetricColor,
  getMetricIcon,
} from "../../utils/formatters.jsx";
import SymbolSearch from "../shared/SymbolSearch";

const PortfolioPerformanceMetrics = ({ portfolio }) => {
  const [loading, setLoading] = useState(false);
  const [performanceData, setPerformanceData] = useState(null);
  const [multiPeriodData, setMultiPeriodData] = useState(null);
  const [availablePeriods, setAvailablePeriods] = useState([]);
  const [selectedPeriod, setSelectedPeriod] = useState("inception");
  const [benchmarkData, setBenchmarkData] = useState(null);
  const [showBenchmarkComparison, setShowBenchmarkComparison] = useState(false);
  const [benchmarkType, setBenchmarkType] = useState("index"); // 'index' or 'symbol'
  const [selectedBenchmark, setSelectedBenchmark] = useState(null);
  const [majorIndices, setMajorIndices] = useState([]);
  const [expandedMetrics, setExpandedMetrics] = useState(false);
  const [benchmarkPeriod, setBenchmarkPeriod] = useState("inception");
  const [benchmarkSearchValue, setBenchmarkSearchValue] = useState("");
  const [calculationStatus, setCalculationStatus] = useState(null); // null, 'calculating', 'completed', 'error'
  const [calculationMessage, setCalculationMessage] = useState("");
  const [showMultiPeriod, setShowMultiPeriod] = useState(false);
  const [multiPeriodLoading, setMultiPeriodLoading] = useState(false);
  const [multiPeriodCalculationStatus, setMultiPeriodCalculationStatus] =
    useState(null);
  const [multiPeriodCalculationMessage, setMultiPeriodCalculationMessage] =
    useState("");

  const loadAvailablePeriods = async () => {
    try {
      const response = await portfolioCalculationsAPI.getAvailablePeriods();
      setAvailablePeriods(response.periods || []);
    } catch (error) {
      console.error("Failed to load available periods:", error);
    }
  };

  const loadMajorIndices = async () => {
    try {
      const response = await marketAPI.getMajorIndices();
      setMajorIndices(response || []);
    } catch (error) {
      console.error("Failed to load major indices:", error);
    }
  };

  const loadPerformanceData = useCallback(async () => {
    if (!portfolio?.id) return;

    try {
      setLoading(true);
      setCalculationStatus("calculating");
      setCalculationMessage(
        "Calculating portfolio performance metrics... This may take a moment for complex calculations."
      );

      const response = await portfolioCalculationsAPI.getPortfolioPerformance(
        portfolio.id,
        selectedPeriod
      );
      setPerformanceData(response);
      setCalculationStatus("completed");
      setCalculationMessage("Performance metrics calculated successfully!");
    } catch (error) {
      console.error("Failed to load performance data:", error);
      setCalculationStatus("error");
      setCalculationMessage(
        "Failed to calculate performance metrics. Please try again."
      );
      toast.error("Failed to load performance metrics");
    } finally {
      setLoading(false);
    }
  }, [portfolio?.id, selectedPeriod]);

  const loadMultiPeriodData = useCallback(async () => {
    if (!portfolio?.id) return;

    try {
      setMultiPeriodLoading(true);
      setMultiPeriodCalculationStatus("calculating");
      setMultiPeriodCalculationMessage(
        "Calculating multi-period performance metrics... This may take a moment for complex calculations."
      );

      const response = await portfolioCalculationsAPI.getMultiPeriodPerformance(
        portfolio.id
      );
      setMultiPeriodData(response);
      setMultiPeriodCalculationStatus("completed");
      setMultiPeriodCalculationMessage(
        "Multi-period performance metrics calculated successfully!"
      );
    } catch (error) {
      console.error("Failed to load multi-period data:", error);
      setMultiPeriodCalculationStatus("error");
      setMultiPeriodCalculationMessage(
        "Failed to calculate multi-period performance metrics. Please try again."
      );
    } finally {
      setMultiPeriodLoading(false);
    }
  }, [portfolio?.id]);

  // Load initial data
  useEffect(() => {
    if (portfolio?.id) {
      loadAvailablePeriods();
      loadPerformanceData();
      loadMajorIndices();
    }
  }, [portfolio, loadPerformanceData]);

  // Load performance data when period changes
  useEffect(() => {
    if (portfolio?.id && selectedPeriod) {
      // Clear previous calculation status
      setCalculationStatus(null);
      setCalculationMessage("");
      loadPerformanceData();
    }
  }, [selectedPeriod, portfolio, loadPerformanceData]);

  const handleBenchmarkComparison = async () => {
    if (!selectedBenchmark || !portfolio?.id) {
      toast.error("Please select a benchmark");
      return;
    }

    try {
      setLoading(true);
      setCalculationStatus("calculating");
      setCalculationMessage(
        "Calculating benchmark comparison... This may take a moment for complex calculations."
      );

      const response =
        await portfolioCalculationsAPI.comparePortfolioToBenchmark(
          portfolio.id,
          selectedBenchmark.symbol,
          benchmarkPeriod
        );
      setBenchmarkData(response);
      setShowBenchmarkComparison(true);
      setCalculationStatus("completed");
      setCalculationMessage("Benchmark comparison completed successfully!");
      toast.success("Benchmark comparison completed");
    } catch (error) {
      console.error("Failed to load benchmark comparison:", error);
      setCalculationStatus("error");
      setCalculationMessage(
        "Failed to calculate benchmark comparison. Please try again."
      );
      toast.error("Failed to load benchmark comparison");
    } finally {
      setLoading(false);
    }
  };

  const handleSymbolSelect = (symbol) => {
    setSelectedBenchmark(symbol);
    setBenchmarkType("symbol");
    setBenchmarkSearchValue(symbol.symbol || symbol);
  };

  const handleIndexSelect = (index) => {
    setSelectedBenchmark(index);
    setBenchmarkType("index");
  };

  const handleSymbolSearchChange = (value) => {
    setBenchmarkSearchValue(value);
  };

  const handleStartBenchmarkComparison = () => {
    // Clear previous calculation status when starting new comparison
    setCalculationStatus(null);
    setCalculationMessage("");
    setBenchmarkData(null);
  };

  const handleMultiPeriodToggle = () => {
    if (!showMultiPeriod) {
      // Expanding - load data if not already loaded
      if (!multiPeriodData) {
        loadMultiPeriodData();
      }
    }
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
        {calculationStatus && !showBenchmarkComparison && (
          <div
            className={`p-4 rounded-lg mb-4 ${
              calculationStatus === "calculating"
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
                  className={`text-sm font-medium ${
                    calculationStatus === "calculating"
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
          {/* CAGR */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-400">CAGR</h4>
              {getMetricIcon(performanceData.metrics?.cagr)}
            </div>
            <p
              className={`text-2xl font-bold ${getMetricColor(
                performanceData.metrics?.cagr
              )}`}
            >
              {formatMetricValue(performanceData.metrics?.cagr, true)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Compound Annual Growth Rate
            </p>
          </div>

          {/* XIRR */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-400">XIRR</h4>
              {getMetricIcon(performanceData.metrics?.xirr)}
            </div>
            <p
              className={`text-2xl font-bold ${getMetricColor(
                performanceData.metrics?.xirr
              )}`}
            >
              {formatMetricValue(performanceData.metrics?.xirr, true)}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Extended Internal Rate of Return
            </p>
          </div>

          {/* TWR */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-400">TWR</h4>
              {getMetricIcon(performanceData.metrics?.twr)}
            </div>
            <p
              className={`text-2xl font-bold ${getMetricColor(
                performanceData.metrics?.twr
              )}`}
            >
              {formatMetricValue(performanceData.metrics?.twr, true)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Time-Weighted Return</p>
          </div>

          {/* MWR */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-400">MWR</h4>
              {getMetricIcon(performanceData.metrics?.mwr)}
            </div>
            <p
              className={`text-2xl font-bold ${getMetricColor(
                performanceData.metrics?.mwr
              )}`}
            >
              {formatMetricValue(performanceData.metrics?.mwr, true)}
            </p>
            <p className="text-xs text-gray-500 mt-1">Money-Weighted Return</p>
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
            className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 transition-all duration-300 ${
              expandedMetrics
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
                {formatCurrency(performanceData.current_value)}
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
                  className={`transition-transform ${
                    showMultiPeriod ? "rotate-180" : ""
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
            {multiPeriodCalculationStatus && (
              <div
                className={`p-4 rounded-lg ${
                  multiPeriodCalculationStatus === "calculating"
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
                      className={`text-sm font-medium ${
                        multiPeriodCalculationStatus === "calculating"
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
                  <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
                  <p className="text-gray-400">
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

      {/* Benchmark Comparison */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-semibold text-gray-100">
            Benchmark Comparison
          </h4>
          <button
            onClick={() => setShowBenchmarkComparison(!showBenchmarkComparison)}
            className="btn-outline text-sm"
          >
            {showBenchmarkComparison ? "Hide Comparison" : "Add Comparison"}
          </button>
        </div>

        {!showBenchmarkComparison ? (
          <div className="space-y-4">
            {/* Benchmark Type Selection */}
            <div className="flex space-x-4">
              <label className="flex items-center space-x-2">
                <input
                  type="radio"
                  value="index"
                  checked={benchmarkType === "index"}
                  onChange={(e) => {
                    setBenchmarkType(e.target.value);
                    setSelectedBenchmark(null); // Clear selection when switching types
                    setBenchmarkSearchValue(""); // Clear search value
                  }}
                  className="text-primary-400"
                />
                <span className="text-sm text-gray-300">
                  Compare with Index
                </span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="radio"
                  value="symbol"
                  checked={benchmarkType === "symbol"}
                  onChange={(e) => {
                    setBenchmarkType(e.target.value);
                    setSelectedBenchmark(null); // Clear selection when switching types
                    setBenchmarkSearchValue(""); // Clear search value
                  }}
                  className="text-primary-400"
                />
                <span className="text-sm text-gray-300">
                  Compare with Symbol
                </span>
              </label>
            </div>

            {/* Period and Benchmark Selection - Side by Side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Period Selection for Benchmark */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Comparison Period
                </label>
                <select
                  value={benchmarkPeriod}
                  onChange={(e) => setBenchmarkPeriod(e.target.value)}
                  className="input-field w-full"
                >
                  {availablePeriods.map((period) => (
                    <option key={period.period_code} value={period.period_code}>
                      {period.period_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Index Selection */}
              {benchmarkType === "index" && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Select Major Index
                  </label>
                  <select
                    value={selectedBenchmark?.symbol || ""}
                    onChange={(e) => {
                      const index = majorIndices.find(
                        (i) => i.symbol === e.target.value
                      );
                      handleIndexSelect(index);
                    }}
                    className="input-field w-full"
                  >
                    <option value="">Select an index...</option>
                    {majorIndices.map((index) => (
                      <option key={index.symbol} value={index.symbol}>
                        {index.name} ({index.symbol})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Symbol Selection */}
              {benchmarkType === "symbol" && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Search Symbol
                  </label>
                  <SymbolSearch
                    value={benchmarkSearchValue}
                    onChange={handleSymbolSearchChange}
                    onSelect={handleSymbolSelect}
                    placeholder="Search for a stock symbol..."
                  />
                </div>
              )}
            </div>

            {/* Selected Benchmark Display */}
            {selectedBenchmark && (
              <div className="p-3 bg-dark-800 rounded-lg border border-gray-600">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 bg-primary-600/20 rounded-lg flex items-center justify-center">
                      <TrendingUp size={16} className="text-primary-400" />
                    </div>
                    <div>
                      <div className="font-mono text-sm font-medium text-gray-100">
                        {selectedBenchmark.symbol}
                      </div>
                      <div className="text-xs text-gray-400">
                        {selectedBenchmark.name ||
                          selectedBenchmark.long_name ||
                          selectedBenchmark.short_name ||
                          selectedBenchmark.longname ||
                          selectedBenchmark.shortname}
                      </div>
                      <div className="text-xs text-gray-500">
                        {selectedBenchmark.exchange ||
                          selectedBenchmark.exchDisp}{" "}
                        •{" "}
                        {selectedBenchmark.quote_type ||
                          selectedBenchmark.typeDisp ||
                          selectedBenchmark.type ||
                          selectedBenchmark.asset_type ||
                          "EQUITY"}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="text-xs text-gray-400">
                      {benchmarkType === "index" ? "Index" : "Stock"}
                    </div>
                    <button
                      onClick={() => {
                        setSelectedBenchmark(null);
                        setBenchmarkSearchValue("");
                      }}
                      className="text-gray-400 hover:text-gray-300"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Compare Button */}
            <button
              onClick={() => {
                handleStartBenchmarkComparison();
                handleBenchmarkComparison();
              }}
              disabled={!selectedBenchmark || loading}
              className="btn-primary flex items-center space-x-2"
            >
              <BarChart3 size={16} />
              <span>{loading ? "Calculating..." : "Compare Performance"}</span>
            </button>

            {/* Calculation Status */}
            {calculationStatus && (
              <div
                className={`p-4 rounded-lg ${
                  calculationStatus === "calculating"
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
                      className={`text-sm font-medium ${
                        calculationStatus === "calculating"
                          ? "text-warning-400"
                          : calculationStatus === "completed"
                          ? "text-success-400"
                          : "text-danger-400"
                      }`}
                    >
                      {calculationStatus === "calculating" &&
                        "Calculation in Progress"}
                      {calculationStatus === "completed" &&
                        "Calculation Completed"}
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
        ) : (
          <div className="space-y-4">
            {/* Close Button */}
            <div className="flex justify-end">
              <button
                onClick={() => setShowBenchmarkComparison(false)}
                className="text-gray-400 hover:text-gray-300"
              >
                <X size={20} />
              </button>
            </div>

            {/* Benchmark Comparison Results */}
            {benchmarkData && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Portfolio Performance */}
                  <div className="space-y-4">
                    <h5 className="text-lg font-semibold text-gray-100">
                      Portfolio Performance
                    </h5>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">CAGR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.portfolio_performance.metrics?.cagr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.portfolio_performance.metrics?.cagr,
                            true
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">XIRR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.portfolio_performance.metrics?.xirr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.portfolio_performance.metrics?.xirr,
                            true
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">TWR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.portfolio_performance.metrics?.twr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.portfolio_performance.metrics?.twr,
                            true
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">MWR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.portfolio_performance.metrics?.mwr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.portfolio_performance.metrics?.mwr,
                            true
                          )}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Benchmark Performance */}
                  <div className="space-y-4">
                    <h5 className="text-lg font-semibold text-gray-100">
                      {selectedBenchmark?.name || selectedBenchmark?.symbol}{" "}
                      Performance
                    </h5>
                    <div className="space-y-3">
                      <div className="flex justify-between">
                        <span className="text-gray-400">CAGR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.benchmark_performance.metrics?.cagr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.benchmark_performance.metrics?.cagr,
                            true
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">XIRR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.benchmark_performance.metrics?.xirr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.benchmark_performance.metrics?.xirr,
                            true
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">TWR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.benchmark_performance.metrics?.twr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.benchmark_performance.metrics?.twr,
                            true
                          )}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">MWR:</span>
                        <span
                          className={getMetricColor(
                            benchmarkData.benchmark_performance.metrics?.mwr
                          )}
                        >
                          {formatMetricValue(
                            benchmarkData.benchmark_performance.metrics?.mwr,
                            true
                          )}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Comparison Summary */}
                {benchmarkData.comparison && (
                  <div className="border-t border-dark-700 pt-4">
                    <h5 className="text-lg font-semibold text-gray-100 mb-4">
                      Comparison Summary
                    </h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="text-center">
                        <p className="text-sm text-gray-400">CAGR Difference</p>
                        <p
                          className={`text-lg font-semibold ${getMetricColor(
                            benchmarkData.comparison?.cagr_difference
                          )}`}
                        >
                          {formatMetricValue(
                            benchmarkData.comparison?.cagr_difference,
                            true
                          )}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-400">XIRR Difference</p>
                        <p
                          className={`text-lg font-semibold ${getMetricColor(
                            benchmarkData.comparison?.xirr_difference
                          )}`}
                        >
                          {formatMetricValue(
                            benchmarkData.comparison?.xirr_difference,
                            true
                          )}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-400">TWR Difference</p>
                        <p
                          className={`text-lg font-semibold ${getMetricColor(
                            benchmarkData.comparison?.twr_difference
                          )}`}
                        >
                          {formatMetricValue(
                            benchmarkData.comparison?.twr_difference,
                            true
                          )}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-sm text-gray-400">MWR Difference</p>
                        <p
                          className={`text-lg font-semibold ${getMetricColor(
                            benchmarkData.comparison?.mwr_difference
                          )}`}
                        >
                          {formatMetricValue(
                            benchmarkData.comparison?.mwr_difference,
                            true
                          )}
                        </p>
                      </div>
                    </div>
                    <div className="text-center mt-4">
                      <p
                        className={`text-lg font-semibold ${
                          benchmarkData.comparison?.outperforming == null
                            ? "text-gray-400"
                            : benchmarkData.comparison?.outperforming
                            ? "text-success-400"
                            : "text-danger-400"
                        }`}
                      >
                        {benchmarkData.comparison?.outperforming == null
                          ? "Can not Compare"
                          : benchmarkData.comparison?.outperforming
                          ? "Portfolio is Outperforming"
                          : "Portfolio is Underperforming"}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="min-h-screen gradient-bg flex items-center justify-center">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
            <p className="text-gray-400">Loading performance metrics...</p>
          </div>
        </div>
      )}
    </div>
  );
};

PortfolioPerformanceMetrics.propTypes = {
  portfolio: PropTypes.object.isRequired,
};

export default PortfolioPerformanceMetrics;
