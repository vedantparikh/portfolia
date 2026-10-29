import {
  Activity,
  AlertTriangle,
  BarChart3,
  RefreshCw,
  Settings,
  Target,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  useIndicatorCalculation,
  useIndicatorConfigurations,
  useStrategyBacktests,
} from "./queries";
import EnhancedChart from "../../components/shared/EnhancedChart";
import StrategyBacktests from "./StrategyBacktests";
import StrategySignals from "./StrategySignals";
import { chartPeriodFor, strategyMarkers } from "./strategyMarkers";
import { seriesLabel } from "../../utils/indicatorLabels";
import LoadingSpinner from "../../shared/ui/Spinner";
import { formatRatio } from "../../utils/formatters.jsx";
import { ErrorState } from "../../shared/ui";

const DEFAULT_INDICATORS = ["rsi_indicator", "macd_indicator"];

const AssetAnalyticsView = ({ asset, onRefresh, selectedConfiguration = null, height = 500 }) => {
  const [period, setPeriod] = useState("30d");
  const [selectedIndicators, setSelectedIndicators] = useState(DEFAULT_INDICATORS);
  const [activeConfiguration, setActiveConfiguration] = useState(selectedConfiguration);
  const [showAdvancedAnalysis, setShowAdvancedAnalysis] = useState(false);
  const [backtestYears, setBacktestYears] = useState(5);
  const [chartStrategy, setChartStrategy] = useState(null);
  const chartCard = useRef(null);
  const backtests = useStrategyBacktests(asset?.symbol, backtestYears);
  const markedRow = backtests.data?.strategies.find((row) => row.strategy === chartStrategy);
  const markers = useMemo(() => strategyMarkers(markedRow), [markedRow]);

  // A saved configuration is calculated server-side with its own parameters
  const calculation = useIndicatorCalculation({
    symbol: asset?.symbol,
    period: period,
    interval: "1d",
    ...(activeConfiguration
      ? { configuration_id: activeConfiguration.id }
      : {
          indicators: selectedIndicators.map((indicatorName) => ({
            indicator_name: indicatorName,
            parameters: {},
            enabled: true,
          })),
        }),
  });
  const response = calculation.data;
  const chartData = response?.data || [];
  const analysisData = response
    ? {
        indicators: response.indicator_series || [],
        indicatorPanelData: response.indicator_series || [],
        fullResponse: response,
      }
    : null;
  const loading = calculation.isFetching;
  const error = calculation.isError ? "Failed to load analysis data" : null;
  const { data: indicatorConfigurations = [] } = useIndicatorConfigurations({
    enabled: Boolean(asset?.symbol),
  });

  useEffect(() => {
    setActiveConfiguration(selectedConfiguration);
    if (selectedConfiguration?.indicators?.length) {
      setSelectedIndicators(selectedConfiguration.indicators.map((i) => i.indicator_name));
    }
  }, [selectedConfiguration]);

  const applyConfiguration = (config) => {
    setActiveConfiguration(config);
    setSelectedIndicators((config.indicators || []).map((i) => i.indicator_name));
  };

  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);
  };

  // Marking a rule widens the chart to its backtest window
  const showStrategy = (strategy) => {
    setChartStrategy(strategy);
    if (!strategy) return;
    setPeriod(chartPeriodFor(backtestYears));
    chartCard.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  };

  const changeBacktestYears = (years) => {
    setBacktestYears(years);
    if (chartStrategy) setPeriod(chartPeriodFor(years));
  };

  // Toggling indicators by hand leaves the saved configuration
  const handleIndicatorChange = (newIndicators) => {
    setActiveConfiguration(null);
    setSelectedIndicators(newIndicators);
  };

  const handleRefresh = () => {
    calculation.refetch();
    if (onRefresh) {
      onRefresh();
    }
  };

  if (loading && chartData.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner type="analyst" size="lg" text="Loading analysis..." />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState icon={AlertTriangle} title="Analysis Error" message={error} onRetry={handleRefresh} />
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
      <div ref={chartCard} className="card p-6 scroll-mt-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-100 mb-2 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2 text-primary-400" />
            Price Chart with Indicators
          </h3>
          <p className="text-sm text-gray-400">
            Interactive chart with technical indicators and analysis tools
          </p>
          {markedRow && (
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-dark-800 px-3 py-2 text-sm">
              <span className="text-gray-300">
                Marked: <span className="font-medium text-gray-100">{markedRow.name}</span>, last{" "}
                {backtestYears} {backtestYears === 1 ? "year" : "years"}
              </span>
              <span className="text-xs text-gray-400">
                <span className="text-success-400">▲ Buy</span> and <span className="text-danger-400">▼ Sell</span> at
                the close; a circle is a latest signal the rule did not trade
              </span>
              <button
                type="button"
                onClick={() => setChartStrategy(null)}
                aria-label="Remove strategy markers"
                className="ml-auto text-gray-400 hover:text-gray-200"
              >
                <X size={16} />
              </button>
            </div>
          )}
        </div>

        <EnhancedChart
          data={chartData}
          period={period}
          onPeriodChange={handlePeriodChange}
          symbol={asset?.symbol}
          currency={asset?.currency}
          assetId={asset?.id}
          height={height}
          loading={loading}
          showIndicators={true}
          enableIndicatorConfig={true}
          defaultIndicators={selectedIndicators}
          onIndicatorsChange={handleIndicatorChange}
          indicatorOverlayData={analysisData?.indicators}
          markers={markers}
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
                            {seriesLabel(indicatorSeries)}
                          </h4>
                          <span
                            className={`text-sm font-semibold ${isOverbought
                              ? "text-danger-400"
                              : isOversold
                                ? "text-success-400"
                                : "text-gray-400"
                              }`}
                          >
                            {formatRatio(value)}
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

      <StrategySignals symbol={asset?.symbol} currency={asset?.currency} />
      <StrategyBacktests
        symbol={asset?.symbol}
        currency={asset?.currency}
        years={backtestYears}
        onYearsChange={changeBacktestYears}
        shown={chartStrategy}
        onShow={showStrategy}
      />

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
                  {config.indicators?.map((indicator, i) => (
                    <span
                      key={indicator.id ?? `${indicator.indicator_name}-${i}`}
                      className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full"
                    >
                      {indicator.indicator_name}
                    </span>
                  ))}
                </div>

                <button
                  onClick={() => applyConfiguration(config)}
                  className={`w-full text-sm ${
                    activeConfiguration?.id === config.id ? "btn-primary" : "btn-outline"
                  }`}
                >
                  {activeConfiguration?.id === config.id ? "Applied" : "Apply Configuration"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AssetAnalyticsView;
