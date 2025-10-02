import {
  AreaSeries,
  CandlestickSeries,
  LineSeries,
  createChart,
} from "lightweight-charts";
import {
  BarChart3,
  Maximize2,
  Minimize2,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { statisticalIndicatorsAPI } from "../../services/api";

const Chart = ({
  data = [],
  symbol = "",
  period = "30d",
  onPeriodChange,
  height = 400,
  loading = false,
  onRefresh,
  showControls = true,
  showPeriodSelector = true,
  chartType = "candlestick",
  theme = "dark",
  className = "",
  enableFullscreen = false,
  onFullscreenToggle,
  showReturns = false,
  showIndicators = false,
  selectedIndicators = [],
  onIndicatorsChange,
  isPortfolioChart = false,
  portfolioData = null,
  showComparisonLine = false,
  comparisonLineName = "Comparison",
}) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [returnsData, setReturnsData] = useState({});
  const [showReturnsPanel, setShowReturnsPanel] = useState(false);
  const [indicatorData, setIndicatorData] = useState({});
  const [loadingIndicators, setLoadingIndicators] = useState(false);
  const [availableIndicators, setAvailableIndicators] = useState([]);
  const [showIndicatorsPanel, setShowIndicatorsPanel] = useState(false);

  const loadAvailableIndicators = async () => {
    try {
      const response = await statisticalIndicatorsAPI.getAvailableIndicators();
      setAvailableIndicators(response.indicators || []);
    } catch (error) {
      console.error("Failed to load available indicators:", error);
    }
  };

  const loadIndicatorData = useCallback(async () => {
    if (!symbol) return;
    try {
      setLoadingIndicators(true);
      const response = await statisticalIndicatorsAPI.calculateIndicators({
        symbol: symbol,
        period: period,
        interval: "1d",
        indicators: selectedIndicators.map((indicatorName) => ({
          indicator_name: indicatorName,
          parameters: {},
          enabled: true,
        })),
      });
      setIndicatorData(response?.indicator_series || {});
    } catch (error) {
      console.error("Failed to load indicator data:", error);
    } finally {
      setLoadingIndicators(false);
    }
  }, [symbol, period, selectedIndicators]);

  const calculateReturns = useCallback(() => {
    if (!data || data.length === 0) return;
    const sortedData = [...data].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
    const firstPrice = sortedData[0]?.close || 0;
    const lastPrice = sortedData[sortedData.length - 1]?.close || 0;
    const highPrice = Math.max(...sortedData.map((d) => d.high));
    const lowPrice = Math.min(...sortedData.map((d) => d.low));
    const totalReturn =
      firstPrice > 0 ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;
    const maxGain =
      firstPrice > 0 ? ((highPrice - firstPrice) / firstPrice) * 100 : 0;
    const maxLoss =
      firstPrice > 0 ? ((lowPrice - firstPrice) / firstPrice) * 100 : 0;
    setReturnsData({
      totalReturn,
      maxGain,
      maxLoss,
      highPrice,
      lowPrice,
      firstPrice,
      lastPrice,
    });
  }, [data]);

  const { candlestickData, portfolioLineData, comparisonLineData } =
    useMemo(() => {
      if (isPortfolioChart && portfolioData) {
        const sortedData = [...portfolioData].sort(
          (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
        );

        const uniqueDataMap = new Map();
        sortedData.forEach((item) => {
          uniqueDataMap.set(new Date(item.date).getTime(), item);
        });
        const uniqueSortedData = Array.from(uniqueDataMap.values());

        const processedPortfolioData = uniqueSortedData
          .map((item) => ({
            time: new Date(item.date).getTime() / 1000,
            value: Number(item.value) || 0,
          }))
          .filter((item) => !isNaN(item.value));

        const processedComparisonData = showComparisonLine
          ? uniqueSortedData
              .map((item) => ({
                time: new Date(item.date).getTime() / 1000,
                value: Number(item.cost_basis) || 0,
              }))
              .filter((item) => !isNaN(item.value))
          : [];

        return {
          candlestickData: [],
          portfolioLineData: processedPortfolioData,
          comparisonLineData: processedComparisonData,
        };
      }

      if (!data || data.length === 0) {
        return {
          candlestickData: [],
          portfolioLineData: [],
          comparisonLineData: [],
        };
      }
      const sortedData = [...data].sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      );

      const uniqueDataMap = new Map();
      sortedData.forEach((item) => {
        uniqueDataMap.set(new Date(item.date).getTime(), item);
      });
      const uniqueSortedData = Array.from(uniqueDataMap.values());

      const cData = uniqueSortedData
        .map((item) => {
          const open = Number(item.open);
          const high = Number(item.high);
          const low = Number(item.low);
          const close = Number(item.close);
          if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close)) {
            console.warn("Invalid data point:", item);
            return null;
          }
          return {
            time: new Date(item.date).getTime() / 1000,
            open,
            high,
            low,
            close,
          };
        })
        .filter(Boolean);

      return {
        candlestickData: cData,
        portfolioLineData: [],
        comparisonLineData: [],
      };
    }, [data, isPortfolioChart, portfolioData, showComparisonLine]);

  useEffect(() => {
    if (showReturns && data && data.length > 0) {
      calculateReturns();
    }
  }, [data, showReturns, calculateReturns]);

  useEffect(() => {
    if (showIndicators) {
      loadAvailableIndicators();
    }
  }, [showIndicators]);

  useEffect(() => {
    if (
      showIndicators &&
      selectedIndicators.length > 0 &&
      symbol &&
      data.length > 0
    ) {
      loadIndicatorData();
    }
  }, [selectedIndicators, symbol, data, showIndicators, loadIndicatorData]);

  useEffect(() => {
    const hasData = isPortfolioChart
      ? portfolioLineData.length > 0
      : candlestickData.length > 0;

    if (
      !chartContainerRef.current ||
      chartContainerRef.current.clientWidth === 0 ||
      !hasData
    ) {
      return;
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: theme === "dark" ? "#020617" : "#ffffff" },
        textColor: theme === "dark" ? "#f1f5f9" : "#191919",
      },
      grid: {
        vertLines: { color: theme === "dark" ? "#334155" : "#e1e3e6" },
        horzLines: { color: theme === "dark" ? "#334155" : "#e1e3e6" },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: theme === "dark" ? "#475569" : "#cccccc",
          width: 1,
          style: 2,
        },
        horzLine: {
          color: theme === "dark" ? "#475569" : "#cccccc",
          width: 1,
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: theme === "dark" ? "#475569" : "#cccccc",
        textColor: theme === "dark" ? "#cbd5e1" : "#191919",
      },
      timeScale: {
        borderColor: theme === "dark" ? "#475569" : "#cccccc",
        timeVisible: true,
        secondsVisible: false,
        textColor: theme === "dark" ? "#cbd5e1" : "#191919",
      },
    });

    chartRef.current = chart;

    if (!chart) {
      console.error("Failed to create chart");
      return;
    }

    let priceSeries;
    let comparisonSeries = null;

    if (isPortfolioChart) {
      priceSeries = chart.addSeries(LineSeries, {
        color: "#0ea5e9",
        lineWidth: 2,
        title: "Portfolio Value",
      });
      priceSeries.setData(portfolioLineData);

      if (showComparisonLine && comparisonLineData.length > 0) {
        comparisonSeries = chart.addSeries(LineSeries, {
          color: "#6b7280",
          lineWidth: 2,
          lineStyle: 2,
          title: comparisonLineName,
        });
        comparisonSeries.setData(comparisonLineData);
      }
    } else {
      if (chartType === "candlestick") {
        priceSeries = chart.addSeries(CandlestickSeries, {
          upColor: "#22c55e",
          downColor: "#ef4444",
          borderDownColor: "#dc2626",
          borderUpColor: "#16a34a",
          wickDownColor: "#dc2626",
          wickUpColor: "#16a34a",
        });
        priceSeries.setData(candlestickData);
      } else if (chartType === "line" || chartType === "area") {
        const lineData = candlestickData.map((d) => ({
          time: d.time,
          value: d.close,
        }));
        if (chartType === "area") {
          priceSeries = chart.addSeries(AreaSeries, {
            topColor: "rgba(14, 165, 233, 0.3)",
            bottomColor: "rgba(14, 165, 233, 0.0)",
            lineColor: "#0ea5e9",
            lineWidth: 2,
          });
        } else {
          priceSeries = chart.addSeries(LineSeries, {
            color: "#0ea5e9",
            lineWidth: 2,
          });
        }
        priceSeries.setData(lineData);
      }
    }

    if (
      showIndicators &&
      Array.isArray(indicatorData) &&
      indicatorData.length > 0
    ) {
      indicatorData.forEach((indicatorSeries) => {
        if (indicatorSeries.data && indicatorSeries.data.length > 0) {
          const seriesData = indicatorSeries.data.map((point) => ({
            time: new Date(point.date).getTime() / 1000,
            value: point.value,
          }));
          const series = chart.addSeries(LineSeries, {
            color:
              indicatorSeries.color ||
              getIndicatorColor(indicatorSeries.indicator_name),
            lineWidth: indicatorSeries.line_width || 2,
            priceLineVisible: false,
            lastValueVisible: false,
          });
          series.setData(seriesData);
        }
      });
    }

    chart.timeScale().fitContent();

    const tooltip = document.createElement("div");
    tooltip.className =
      "absolute bg-dark-800 border border-dark-600 rounded-lg p-3 shadow-xl z-50 pointer-events-none opacity-0 transition-opacity duration-200";
    tooltip.style.fontSize = "12px";
    tooltip.style.fontFamily = "Inter, system-ui, sans-serif";
    chartContainerRef.current.appendChild(tooltip);

    const updateTooltip = (param) => {
      if (!param.point || !param.time || !chartContainerRef.current) {
        tooltip.style.opacity = "0";
        return;
      }
      const data = param.seriesData.get(priceSeries);
      if (!data) {
        tooltip.style.opacity = "0";
        return;
      }
      const date = new Date(data.time * 1000).toLocaleDateString();
      const time = new Date(data.time * 1000).toLocaleTimeString();
      let tooltipContent = "";

      if (isPortfolioChart) {
        const portfolioValue = data.value;
        const comparisonValue = comparisonSeries
          ? param.seriesData.get(comparisonSeries)?.value
          : null;

        tooltipContent = `
          <div class="text-gray-100 font-semibold mb-2">Portfolio Performance - ${date}</div>
          <div class="space-y-1 text-xs">
              <div class="flex justify-between"><span class="text-gray-400">Time:</span><span class="text-gray-200">${time}</span></div>
              <div class="flex justify-between"><span class="text-gray-400">Portfolio Value:</span><span class="text-primary-400">$${
                portfolioValue?.toFixed(2) || "N/A"
              }</span></div>
              ${
                comparisonValue !== null && comparisonValue !== undefined
                  ? `
                  <div class="flex justify-between"><span class="text-gray-400">${comparisonLineName}:</span><span class="text-gray-300">$${comparisonValue.toFixed(
                    2
                  )}</span></div>
                  <div class="flex justify-between"><span class="text-gray-400">Unrealized P/L:</span><span class="${
                    portfolioValue >= comparisonValue
                      ? "text-success-400"
                      : "text-danger-400"
                  }">$${(portfolioValue - comparisonValue).toFixed(
                      2
                    )}</span></div>
              `
                  : ""
              }
          </div>
        `;
      } else {
        if (chartType === "candlestick") {
          tooltipContent = `
            <div class="text-gray-100 font-semibold mb-2">${
              symbol || "Asset"
            } - ${date}</div>
            <div class="space-y-1 text-xs">
                <div class="flex justify-between"><span class="text-gray-400">Open:</span><span class="text-gray-200">$${
                  data.open?.toFixed(2) || "N/A"
                }</span></div>
                <div class="flex justify-between"><span class="text-gray-400">High:</span><span class="text-success-400">$${
                  data.high?.toFixed(2) || "N/A"
                }</span></div>
                <div class="flex justify-between"><span class="text-gray-400">Low:</span><span class="text-danger-400">$${
                  data.low?.toFixed(2) || "N/A"
                }</span></div>
                <div class="flex justify-between"><span class="text-gray-400">Close:</span><span class="text-gray-200">$${
                  data.close?.toFixed(2) || "N/A"
                }</span></div>
                <div class="flex justify-between"><span class="text-gray-400">Change:</span><span class="${
                  data.close >= data.open
                    ? "text-success-400"
                    : "text-danger-400"
                }">${
            data.close && data.open
              ? (((data.close - data.open) / data.open) * 100).toFixed(2) + "%"
              : "N/A"
          }</span></div>
            </div>
          `;
        } else {
          tooltipContent = `
            <div class="text-gray-100 font-semibold mb-2">${
              symbol || "Asset"
            } - ${date}</div>
            <div class="space-y-1 text-xs">
                <div class="flex justify-between"><span class="text-gray-400">Time:</span><span class="text-gray-200">${time}</span></div>
                <div class="flex justify-between"><span class="text-gray-400">Price:</span><span class="text-primary-400">$${
                  data.value?.toFixed(2) || "N/A"
                }</span></div>
            </div>
          `;
        }
      }
      tooltip.innerHTML = tooltipContent;

      const container = chartContainerRef.current;
      const tooltipWidth = tooltip.offsetWidth;
      const tooltipHeight = tooltip.offsetHeight;
      const margin = 15;
      let left = param.point.x + margin;
      if (left + tooltipWidth > container.clientWidth) {
        left = param.point.x - tooltipWidth - margin;
      }
      let top = param.point.y - tooltipHeight - margin;
      if (top < 0) {
        top = param.point.y + margin;
      }
      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
      tooltip.style.opacity = "1";
    };

    chart.subscribeCrosshairMove(updateTooltip);

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (tooltip && tooltip.parentNode) {
        tooltip.parentNode.removeChild(tooltip);
      }
      chart.remove();
      chartRef.current = null;
    };
  }, [
    candlestickData,
    portfolioLineData,
    comparisonLineData,
    theme,
    height,
    chartType,
    symbol,
    showIndicators,
    indicatorData,
    isPortfolioChart,
    showComparisonLine,
    comparisonLineName,
  ]);

  const getIndicatorColor = (indicatorName) => {
    const colors = {
      SMA: "#ff6b6b", EMA: "#4ecdc4", RSI: "#45b7d1", MACD: "#96ceb4",
      BB: "#feca57", STOCH: "#ff9ff3", ADX: "#54a0ff", CCI: "#5f27cd",
      WILLR: "#00d2d3", ATR: "#ff9f43",
    };
    return colors[indicatorName] || "#8884d8";
  };

  const handleFullscreenToggle = () => {
    const newFullscreenState = !isFullscreen;
    setIsFullscreen(newFullscreenState);
    if (onFullscreenToggle) {
      onFullscreenToggle(newFullscreenState);
    }
  };

  const periods = [
    { value: "30d", label: "30 Days" }, { value: "3mo", label: "3 Months" },
    { value: "6mo", label: "6 Months" }, { value: "ytd", label: "YTD" },
    { value: "1y", label: "1 Year" }, { value: "2y", label: "2 Years" },
    { value: "3y", label: "3 Years" }, { value: "4y", label: "4 Years" },
    { value: "5y", label: "5 Years" }, { value: "max", label: "All" },
  ];

  if (loading) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        style={{ height }}
      >
        <div className="flex flex-col items-center space-y-2">
          <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
          <p className="text-gray-400">Loading chart data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {showControls && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            {showPeriodSelector &&
              periods.map((periodOption) => (
                <button
                  key={periodOption.value}
                  onClick={() => onPeriodChange(periodOption.value)}
                  className={`px-3 py-1 text-xs rounded-md transition-colors ${
                    period === periodOption.value
                      ? "bg-primary-600 text-white font-semibold"
                      : "bg-dark-800 text-gray-400 hover:bg-dark-700"
                  }`}
                >
                  {periodOption.label}
                </button>
              ))}
          </div>
          <div className="flex items-center space-x-2">
            {showReturns && (
              <button
                onClick={() => setShowReturnsPanel(!showReturnsPanel)}
                className="btn-outline flex items-center space-x-2"
              >
                <TrendingUp size={16} />
                <span>Returns</span>
              </button>
            )}
            {showIndicators && (
              <button
                onClick={() => setShowIndicatorsPanel(!showIndicatorsPanel)}
                className="btn-outline flex items-center space-x-2"
              >
                <BarChart3 size={16} />
                <span>Indicators</span>
              </button>
            )}

            {enableFullscreen && (
              <button
                onClick={handleFullscreenToggle}
                className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-700 rounded transition-colors"
                title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
              >
                {isFullscreen ? (
                  <Minimize2 size={16} />
                ) : (
                  <Maximize2 size={16} />
                )}
              </button>
            )}
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-700 rounded transition-colors"
                title="Refresh data"
              >
                <RefreshCw size={16} />
              </button>
            )}
          </div>
        </div>
      )}
      
      {/* Returns and Indicators panels remain unchanged */}

      <div
        ref={chartContainerRef}
        style={{ height: `${height}px`, width: "100%", position: "relative" }}
        className="bg-dark-950 rounded-lg border border-dark-700 overflow-hidden"
      />

      {((!isPortfolioChart && (!data || data.length === 0)) ||
        (isPortfolioChart && (!portfolioData || portfolioData.length === 0))) &&
        !loading && (
          <div
            className="absolute inset-0 flex items-center justify-center pointer-events-none"
            style={{ height }}
          >
            <div className="flex flex-col items-center space-y-2">
              <BarChart3 className="w-8 h-8 text-gray-500" />
              <p className="text-gray-500">
                {isPortfolioChart
                  ? "No portfolio data available for this period."
                  : "No chart data available for this period."}
              </p>
            </div>
          </div>
        )}
    </div>
  );
};

Chart.propTypes = {
  data: PropTypes.array,
  symbol: PropTypes.string,
  period: PropTypes.string,
  onPeriodChange: PropTypes.func,
  height: PropTypes.number,
  loading: PropTypes.bool,
  onRefresh: PropTypes.func,
  showControls: PropTypes.bool,
  showPeriodSelector: PropTypes.bool,
  chartType: PropTypes.string,
  theme: PropTypes.string,
  className: PropTypes.string,
  enableFullscreen: PropTypes.bool,
  onFullscreenToggle: PropTypes.func,
  showReturns: PropTypes.bool,
  showIndicators: PropTypes.bool,
  selectedIndicators: PropTypes.array,
  onIndicatorsChange: PropTypes.func,
  isPortfolioChart: PropTypes.bool,
  portfolioData: PropTypes.array,
  showComparisonLine: PropTypes.bool,
  comparisonLineName: PropTypes.string,
};

export default Chart;