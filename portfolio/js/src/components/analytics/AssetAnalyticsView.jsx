import {
  Activity,
  AlertTriangle,
  BarChart3,
  RefreshCw,
  Settings,
  Target,
  TrendingUp,
} from "lucide-react";
import PropTypes from "prop-types";
import { useCallback, useEffect, useState } from "react";
import { statisticalIndicatorsAPI } from "../../services/api";
import EnhancedChart from "../shared/EnhancedChart";

const AssetAnalyticsView = ({ asset, onRefresh, height = 500 }) => {
  const [period, setPeriod] = useState("30d");
  const [chartData, setChartData] = useState([]);
  const [analysisData, setAnalysisData] = useState(null);
  const [indicatorConfigurations, setIndicatorConfigurations] = useState([]);
  const [selectedIndicators, setSelectedIndicators] = useState([
    "rsi_indicator",
    "macd_indicator",
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showAdvancedAnalysis, setShowAdvancedAnalysis] = useState(false);

  // FIX: `loadData` function is now defined BEFORE it is used in the useEffect hook.
  const loadData = useCallback(async () => {
    if (!asset?.symbol) return;

    try {
      setLoading(true);
      setError(null);

      const response = await statisticalIndicatorsAPI.calculateIndicators({
        symbol: asset.symbol,
        period: period,
        interval: "1d",
        indicators: selectedIndicators.map((indicatorName) => ({
          indicator_name: indicatorName,
          parameters: {},
          enabled: true,
        })),
      });

      setChartData(response.data || []);
      setAnalysisData({
        indicators: response.indicator_series || [],
        performance: {
          volatility: 0,
          sharpe_ratio: 0,
          max_drawdown: 0,
          beta: 0,
        },
        indicatorPanelData: response.indicator_series || [],
        fullResponse: response,
      });
    } catch (err) {
      console.error("Failed to load analysis data:", err);
      setError("Failed to load analysis data");
    } finally {
      setLoading(false);
    }
  }, [asset?.symbol, period, selectedIndicators]);

  // Load configurations only once when asset changes
  useEffect(() => {
    if (asset?.symbol) {
      loadIndicatorConfigurations();
    }
  }, [asset?.symbol]);

  // Load analysis AND chart data when asset, period, or indicators change
  useEffect(() => {
    if (asset?.symbol) {
      loadData();
    }
  }, [asset?.symbol, period, selectedIndicators, loadData]); // Now this works correctly

  const loadIndicatorConfigurations = async () => {
    try {
      const configurations = await statisticalIndicatorsAPI.getConfigurations();
      setIndicatorConfigurations(configurations || []);
    } catch (err) {
      console.error("Failed to load indicator configurations:", err);
    }
  };

  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);
  };

  const handleIndicatorChange = (newIndicators) => {
    setSelectedIndicators(newIndicators);
  };

  const handleRefresh = () => {
    loadData();
    if (onRefresh) {
      onRefresh();
    }
  };

  if (loading && chartData.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
        <span className="ml-3 text-gray-400">Loading analysis...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="w-16 h-16 text-danger-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-300 mb-2">
          Analysis Error
        </h3>
        <p className="text-gray-500 mb-4">{error}</p>
        <button onClick={handleRefresh} className="btn-primary">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">
            {asset?.symbol || "Asset"} Analysis
          </h2>
          <p className="text-gray-400">
            {asset?.name || "Asset Name"} - Technical Analysis & Indicators
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowAdvancedAnalysis(!showAdvancedAnalysis)}
            className="btn-outline flex items-center space-x-2"
          >
            <Settings size={16} />
            <span>Advanced</span>
          </button>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="btn-primary flex items-center space-x-2"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Enhanced Chart */}
      <div className="card p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-100 mb-2 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2 text-primary-400" />
            Price Chart with Indicators
          </h3>
          <p className="text-sm text-gray-400">
            Interactive chart with technical indicators and analysis tools
          </p>
        </div>

        <EnhancedChart
          data={chartData}
          period={period}
          onPeriodChange={handlePeriodChange}
          symbol={asset?.symbol}
          assetId={asset?.id}
          height={height}
          loading={loading}
          showIndicators={true}
          enableIndicatorConfig={true}
          defaultIndicators={selectedIndicators}
          onIndicatorsChange={handleIndicatorChange}
          indicatorOverlayData={analysisData?.indicators}
          showReturns={true}
          enableAnalysis={true}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Analysis Summary */}
      {analysisData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Trading Signals */}
          {analysisData.signals && (
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                <Target className="w-5 h-5 mr-2 text-primary-400" />
                Trading Signals
              </h3>
              {/* ... same as before ... */}
            </div>
          )}

          {/* Technical Indicators */}
          {analysisData.indicatorPanelData &&
            analysisData.indicatorPanelData.length > 0 && (
              <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-primary-400" />
                  Technical Indicators
                </h3>

                <div className="space-y-4">
                  {analysisData.indicatorPanelData.map((indicatorSeries) => {
                    const latestData =
                      indicatorSeries.data && indicatorSeries.data.length > 0
                        ? indicatorSeries.data[indicatorSeries.data.length - 1]
                        : null;

                    if (!latestData) return null;

                    const indicatorName =
                      indicatorSeries.indicator_name ||
                      indicatorSeries.display_name ||
                      "Unknown";
                    const value = latestData.value;

                    const isRSI = indicatorName.toLowerCase().includes("rsi");
                    const isOverbought = isRSI && value > 70;
                    const isOversold = isRSI && value < 30;

                    return (
                      <div
                        key={indicatorSeries.id || indicatorName}
                        className="p-3 bg-dark-800 rounded-lg"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-100">
                            {indicatorName
                              .replace("_indicator", "")
                              .toUpperCase()}
                          </h4>
                          <span
                            className={`text-sm font-semibold ${
                              isOverbought
                                ? "text-danger-400"
                                : isOversold
                                ? "text-success-400"
                                : "text-gray-400"
                            }`}
                          >
                            {value?.toFixed(2) || "N/A"}
                          </span>
                        </div>

                        {isRSI && (
                          <div className="text-xs text-gray-500">
                            {isOverbought && (
                              <span className="text-danger-400">
                                Overbought (&gt;70)
                              </span>
                            )}
                            {isOversold && (
                              <span className="text-success-400">
                                Oversold (&lt;30)
                              </span>
                            )}
                            {!isOverbought && !isOversold && (
                              <span className="text-gray-400">
                                Neutral (30-70)
                              </span>
                            )}
                          </div>
                        )}

                        {indicatorSeries.parameters &&
                          Object.keys(indicatorSeries.parameters).length >
                            0 && (
                            <div className="text-xs text-gray-500 mt-1">
                              Parameters:{" "}
                              {Object.entries(indicatorSeries.parameters)
                                .map(([key, val]) => `${key}: ${val}`)
                                .join(", ")}
                            </div>
                          )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
        </div>
      )}

      {/* Advanced Analysis */}
      {showAdvancedAnalysis && analysisData?.advanced && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
            <Settings className="w-5 h-5 mr-2 text-primary-400" />
            Advanced Analysis
          </h3>
          {/* ... same as before ... */}
        </div>
      )}

      {/* Indicator Configurations */}
      {indicatorConfigurations.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
            <Settings className="w-5 h-5 mr-2 text-primary-400" />
            Saved Indicator Configurations
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {indicatorConfigurations.map((config) => (
              <div key={config.id} className="p-4 bg-dark-800 rounded-lg">
                <h4 className="font-medium text-gray-100 mb-2">
                  {config.name}
                </h4>
                <p className="text-sm text-gray-400 mb-3">
                  {config.description}
                </p>

                <div className="flex flex-wrap gap-1 mb-3">
                  {config.indicators?.map((indicator) => (
                    <span
                      key={indicator}
                      className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full"
                    >
                      {indicator}
                    </span>
                  ))}
                </div>

                <button
                  onClick={() => setSelectedIndicators(config.indicators || [])}
                  className="btn-outline w-full text-sm"
                >
                  Apply Configuration
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

AssetAnalyticsView.propTypes = {
  asset: PropTypes.shape({
    symbol: PropTypes.string,
    name: PropTypes.string,
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  }),
  onRefresh: PropTypes.func,
  height: PropTypes.number,
};

export default AssetAnalyticsView;
