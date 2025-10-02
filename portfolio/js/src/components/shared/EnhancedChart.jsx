import {
  AreaSeries,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createChart,
} from "lightweight-charts";
import {
  Activity,
  BarChart3,
  ChevronDown,
  Maximize2,
  Minimize2,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  X,
} from "lucide-react";
import PropTypes from "prop-types";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { statisticalIndicatorsAPI } from "../../services/api";
import {
  formatCurrency,
  formatPercentage,
  formatVolume,
} from "../../utils/formatters.jsx";

const EnhancedChart = ({
  data = [],
  symbol = "",
  period = "30d",
  onPeriodChange = () => {},
  height = 400,
  showVolume = true,
  loading = false,
  onRefresh,
  showControls = true,
  showPeriodSelector = true,
  chartType = "candlestick",
  theme = "dark",
  className = "",
  enableFullscreen = false,
  onFullscreenToggle,
  showIndicators = true,
  enableIndicatorConfig = true,
  defaultIndicators = ["SMA", "EMA", "RSI"],
  onIndicatorsChange,
  assetId = null,
  showReturns = true,
  indicatorOverlayData = null,
}) => {
  const chartContainerRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [availableIndicators, setAvailableIndicators] = useState([]);
  const [, setIndicatorConfigurations] = useState([]);
  const [selectedIndicators, setSelectedIndicators] =
    useState(defaultIndicators);
  const [indicatorData, setIndicatorData] = useState({});
  const [showIndicatorPanel, setShowIndicatorPanel] = useState(false);
  const [showReturnsPanel, setShowReturnsPanel] = useState(true);
  const [metricsData, setMetricsData] = useState({});
  const [loadingIndicators, setLoadingIndicators] = useState(false);

  useEffect(() => {
    if (showIndicators && enableIndicatorConfig) {
      loadIndicatorsData();
    }
  }, [showIndicators, enableIndicatorConfig]);

  const loadIndicatorData = useCallback(async () => {
    if (!assetId || indicatorOverlayData) return;

    try {
      setLoadingIndicators(true);
      const response = await statisticalIndicatorsAPI.calculateIndicators(
        assetId,
        selectedIndicators,
        { period, interval: "1d" }
      );
      setIndicatorData(response || {});
    } catch (error) {
      console.error("Failed to load indicator data:", error);
    } finally {
      setLoadingIndicators(false);
    }
  }, [assetId, indicatorOverlayData, selectedIndicators, period]);

  useEffect(() => {
    if (indicatorOverlayData) {
      const transformedData = {};
      if (Array.isArray(indicatorOverlayData)) {
        indicatorOverlayData.forEach((series) => {
          if (series.data && Array.isArray(series.data)) {
            const chartData = series.data
              .map((item) => ({
                time: new Date(item.date).getTime() / 1000,
                value: item.value,
              }))
              .sort((a, b) => a.time - b.time);
            transformedData[series.indicator_name] = chartData;
          }
        });
      }
      setIndicatorData(transformedData);
      return;
    }
    if (selectedIndicators.length > 0 && assetId && data.length > 0) {
      loadIndicatorData();
    }
  }, [
    selectedIndicators,
    assetId,
    data,
    indicatorOverlayData,
    loadIndicatorData,
  ]);

  const getObvTrendDetails = (trend) => {
    switch (trend) {
      case "Rising OBV":
        return {
          text: "Rising (Confirmation)",
          className: "text-success-400",
          Icon: TrendingUp,
        };
      case "Falling OBV":
        return {
          text: "Falling (Confirmation)",
          className: "text-danger-400",
          Icon: TrendingDown,
        };
      case "Bearish Divergence":
        return {
          text: "Bearish Divergence",
          className: "text-danger-400",
          Icon: TrendingDown,
        };
      case "Bullish Divergence":
        return {
          text: "Bullish Divergence",
          className: "text-success-400",
          Icon: TrendingUp,
        };
      default:
        return {
          text: "Inconsistent",
          className: "text-gray-400",
          Icon: null,
        };
    }
  };

  const calculateMetrics = useCallback(() => {
    if (!data || data.length < 2) return;

    const sortedData = [...data].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const dataWithReturns = sortedData.map((d, i) => {
      if (i === 0) return { ...d, dailyReturn: 0 };
      const yesterdayClose = sortedData[i - 1].close;
      const dailyReturn =
        yesterdayClose > 0
          ? ((d.close - yesterdayClose) / yesterdayClose) * 100
          : 0;
      return { ...d, dailyReturn };
    });

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

    const dailyReturns = dataWithReturns.slice(1).map((d) => d.dailyReturn);
    const avgReturn =
      dailyReturns.reduce((sum, val) => sum + val, 0) / dailyReturns.length;
    const variance =
      dailyReturns.reduce((sum, val) => sum + Math.pow(val - avgReturn, 2), 0) /
      dailyReturns.length;
    const volatility = Math.sqrt(variance);

    let peak = -Infinity;
    let maxDrawdown = 0;
    sortedData.forEach((d) => {
      if (d.high > peak) {
        peak = d.high;
      }
      const drawdown = peak > 0 ? ((peak - d.low) / peak) * 100 : 0;
      if (drawdown > maxDrawdown) {
        maxDrawdown = drawdown;
      }
    });

    let trueRanges = [];
    for (let i = 1; i < sortedData.length; i++) {
      const prev = sortedData[i - 1];
      const curr = sortedData[i];
      const tr1 = curr.high - curr.low;
      const tr2 = Math.abs(curr.high - prev.close);
      const tr3 = Math.abs(curr.low - prev.close);
      trueRanges.push(Math.max(tr1, tr2, tr3));
    }
    const atr =
      trueRanges.length > 0
        ? trueRanges.slice(-14).reduce((sum, val) => sum + val, 0) /
          Math.min(trueRanges.length, 14)
        : 0;

    let obvTrend = "Inconsistent";
    const obvValues = [];
    let cumulativeObv = 0;

    for (let i = 1; i < sortedData.length; i++) {
      const prev = sortedData[i - 1];
      const curr = sortedData[i];
      if (curr.close > prev.close) {
        cumulativeObv += curr.volume;
      } else if (curr.close < prev.close) {
        cumulativeObv -= curr.volume;
      }
      obvValues.push({ x: i, y: cumulativeObv });
    }

    if (obvValues.length > 1) {
      const n = obvValues.length;
      const lastObv = obvValues[n - 1].y;
      const firstObv = obvValues[0].y;
      const obvSlope = lastObv - firstObv;
      const priceSlope = lastPrice - firstPrice;

      if (priceSlope > 0 && obvSlope > 0) {
        obvTrend = "Rising OBV";
      } else if (priceSlope < 0 && obvSlope < 0) {
        obvTrend = "Falling OBV";
      } else if (priceSlope > 0 && obvSlope < 0) {
        obvTrend = "Bearish Divergence";
      } else if (priceSlope < 0 && obvSlope > 0) {
        obvTrend = "Bullish Divergence";
      }
    }

    const {
      text: obvTrendText,
      className: obvTrendClassName,
      Icon: obvTrendIcon,
    } = getObvTrendDetails(obvTrend);

    setMetricsData({
      totalReturn,
      maxGain,
      maxLoss,
      highPrice,
      lowPrice,
      firstPrice,
      lastPrice,
      volatility,
      maxDrawdown,
      atr,
      obvTrendText,
      obvTrendClassName,
      obvTrendIcon,
    });
  }, [data]);

  useEffect(() => {
    if (showReturns && data.length > 0) {
      calculateMetrics();
    }
  }, [data, period, showReturns, calculateMetrics]);

  const loadIndicatorsData = async () => {
    try {
      const [indicatorResponse, configurations] = await Promise.all([
        statisticalIndicatorsAPI.getAvailableIndicators(),
        statisticalIndicatorsAPI.getConfigurations(),
      ]);
      setAvailableIndicators(indicatorResponse?.indicators || []);
      setIndicatorConfigurations(configurations || []);
    } catch (error) {
      console.error("Failed to load indicators data:", error);
    }
  };

  const { candlestickData, volumeData } = useMemo(() => {
    if (!data || data.length === 0) {
      return { candlestickData: [], volumeData: [] };
    }
    const sortedData = [...data].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    const cData = sortedData
      .map((item) => {
        const open = Number(item.open);
        const high = Number(item.high);
        const low = Number(item.low);
        const close = Number(item.close);
        const volume = Number(item.Volume);

        if (
          isNaN(open) ||
          isNaN(high) ||
          isNaN(low) ||
          isNaN(close) ||
          isNaN(volume)
        ) {
          console.warn("Invalid data point:", item);
          return null;
        }

        return {
          time: new Date(item.date).getTime() / 1000,
          open,
          high,
          low,
          close,
          volume,
        };
      })
      .filter(Boolean);

    const vData = sortedData
      .map((item) => {
        const volume = Number(item.volume);
        const close = Number(item.close);
        const open = Number(item.open);

        if (isNaN(volume) || isNaN(close) || isNaN(open)) {
          return null;
        }

        return {
          time: new Date(item.date).getTime() / 1000,
          value: volume,
          color:
            close >= open ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
        };
      })
      .filter(Boolean);

    return { candlestickData: cData, volumeData: vData };
  }, [data]);

  useEffect(() => {
    if (
      !chartContainerRef.current ||
      chartContainerRef.current.clientWidth === 0 ||
      candlestickData.length === 0
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
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: theme === "dark" ? "#475569" : "#cccccc",
        timeVisible: true,
        secondsVisible: false,
        textColor: theme === "dark" ? "#cbd5e1" : "#191919",
      },
    });

    if (!chart) {
      console.error("Failed to create chart");
      return;
    }

    let priceSeries;

    // *** FIX: Reverted all series creation to the original chart.addSeries pattern ***
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

    if (showIndicators && Object.keys(indicatorData).length > 0) {
      Object.entries(indicatorData).forEach(
        ([indicatorName, indicatorValues]) => {
          if (indicatorValues && indicatorValues.length > 0) {
            const isSecondaryAxis = isSecondaryAxisIndicator(indicatorName);

            const series = chart.addSeries(LineSeries, {
              color: getIndicatorColor(indicatorName),
              lineWidth: 2,
              priceLineVisible: false,
              lastValueVisible: true,
              priceScaleId: isSecondaryAxis ? "right" : "left",
            });
            series.setData(indicatorValues);

            if (indicatorName.toLowerCase().includes("rsi")) {
              series.createPriceLine({
                price: 70,
                color: "#ef4444",
                lineWidth: 1,
                lineStyle: 2,
                axisLabelVisible: true,
                title: "Overbought (70)",
              });
              series.createPriceLine({
                price: 30,
                color: "#22c55e",
                lineWidth: 1,
                lineStyle: 2,
                axisLabelVisible: true,
                title: "Oversold (30)",
              });
            }
          }
        }
      );
    }

    if (showVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volumeSeries.setData(volumeData);
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

      const originalData = candlestickData.find(
        (item) => item.time === data.time
      );
      const volume = originalData ? originalData.volume : null;

      const date = new Date(data.time * 1000).toLocaleDateString();
      const time = new Date(data.time * 1000).toLocaleTimeString();
      let tooltipContent = "";

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
            <div class="flex justify-between"><span class="text-gray-400">Volume:</span><span class="text-gray-200">${formatVolume(
              volume
            )}</span></div>
            <div class="flex justify-between"><span class="text-gray-400">Change:</span><span class="${
              data.close >= data.open
                ? "text-success-400"
                : "text-danger-400"
            }">${
          data.close && data.open
            ? (((data.close - data.open) / data.open) * 100).toFixed(2) + "%"
            : "N/A"
        }</span></div>
          </div>`;
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
            <div class="flex justify-between"><span class="text-gray-400">Volume:</span><span class="text-gray-200">${formatVolume(
              volume
            )}</span></div>
          </div>`;
      }

      if (showIndicators && Object.keys(indicatorData).length > 0) {
        tooltipContent += '<div class="border-t border-gray-600 mt-2 pt-2">';
        tooltipContent +=
          '<div class="text-gray-300 font-medium mb-1">Indicators:</div>';

        Object.entries(indicatorData).forEach(
          ([indicatorName, indicatorValues]) => {
            if (indicatorValues && indicatorValues.length > 0) {
              const indicatorValue = indicatorValues.find(
                (item) => item.time === data.time
              );
              if (indicatorValue) {
                const color = getIndicatorColor(indicatorName);
                const displayName = indicatorName
                  .replace("_indicator", "")
                  .toUpperCase();
                tooltipContent += `
                  <div class="flex justify-between items-center">
                    <span class="text-gray-400">${displayName}:</span>
                    <span class="font-medium" style="color: ${color}">${
                  indicatorValue.value?.toFixed(2) || "N/A"
                }</span>
                  </div>`;
              }
            }
          }
        );
        tooltipContent += "</div>";
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
    };
  }, [
    candlestickData,
    volumeData,
    theme,
    height,
    showVolume,
    chartType,
    symbol,
    showIndicators,
    indicatorData,
  ]);

  const getIndicatorColor = (indicatorName) => {
    const colors = {
      sma: "#ff6b6b",
      ema: "#4ecdc4",
      rsi_indicator: "#45b7d1",
      macd_indicator: "#96ceb4",
      bollinger_bands_indicator: "#feca57",
      stoch_oscillator_indicator: "#ff9ff3",
      adx_indicator: "#54a0ff",
      cci_indicator: "#5f27cd",
      roc_indicator: "#00d2d3",
      average_true_range_indicator: "#ff9f43",
    };
    return (
      colors[indicatorName] || colors[indicatorName.toLowerCase()] || "#8884d8"
    );
  };

  const isSecondaryAxisIndicator = (indicatorName) => {
    const secondaryAxisIndicators = [
      "rsi",
      "stoch",
      "cci",
      "roc",
      "williams",
      "momentum",
    ];
    const lowerName = indicatorName.toLowerCase();
    return secondaryAxisIndicators.some((indicator) =>
      lowerName.includes(indicator)
    );
  };

  const handleIndicatorToggle = (indicator) => {
    const newIndicators = selectedIndicators.includes(indicator)
      ? selectedIndicators.filter((i) => i !== indicator)
      : [...selectedIndicators, indicator];
    setSelectedIndicators(newIndicators);
    if (onIndicatorsChange) {
      onIndicatorsChange(newIndicators);
    }
  };

  const handleFullscreenToggle = () => {
    const newFullscreenState = !isFullscreen;
    setIsFullscreen(newFullscreenState);
    if (onFullscreenToggle) {
      onFullscreenToggle(newFullscreenState);
    }
  };

  const formatIndicatorDescription = (description) => {
    if (!description) return "";
    return description.replace(/ indicator$/i, "").trim();
  };

  const periods = [
    { value: "30d", label: "30 Days" },
    { value: "3mo", label: "3 Months" },
    { value: "6mo", label: "6 Months" },
    { value: "ytd", label: "YTD" },
    { value: "1y", label: "1 Year" },
    { value: "2y", label: "2 Years" },
    { value: "3y", label: "3 Years" },
    { value: "4y", label: "4 Years" },
    { value: "5y", label: "5 Years" },
    { value: "max", label: "All" },
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
                onClick={() => setShowIndicatorPanel(!showIndicatorPanel)}
                className="btn-outline flex items-center space-x-2"
              >
                <Activity size={16} />
                <span>Indicators</span>
                <ChevronDown
                  size={14}
                  className={`transition-transform ${
                    showIndicatorPanel ? "rotate-180" : ""
                  }`}
                />
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

      {showReturnsPanel && showReturns && (
        <div className="card p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-100 flex items-center">
              <TrendingUp className="w-5 h-5 mr-2 text-primary-400" />
              Performance Metrics
            </h3>
            <button
              onClick={() => setShowReturnsPanel(false)}
              className="text-gray-400 hover:text-gray-100"
            >
              <X size={16} />
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-sm text-gray-400">Total Return</p>
              <p
                className={`text-lg font-bold ${
                  metricsData.totalReturn >= 0
                    ? "text-success-400"
                    : "text-danger-400"
                }`}
              >
                {formatPercentage(metricsData.totalReturn || 0)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Max Gain</p>
              <p className="text-lg font-bold text-success-400">
                {formatPercentage(metricsData.maxGain || 0)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Max Loss vs Start</p>
              <p className="text-lg font-bold text-danger-400">
                {formatPercentage(metricsData.maxLoss || 0)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Price Range</p>
              <p className="text-sm font-medium text-gray-200">
                {formatCurrency(metricsData.lowPrice || 0)} -{" "}
                {formatCurrency(metricsData.highPrice || 0)}
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
                -{formatPercentage(metricsData.maxDrawdown || 0)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">Avg. True Range (ATR)</p>
              <p className="text-lg font-bold text-gray-200">
                {formatCurrency(metricsData.atr || 0)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-400">OBV Trend</p>
              <div
                className={`flex items-center justify-center text-lg font-bold ${metricsData.obvTrendClassName}`}
              >
                {metricsData.obvTrendIcon && (
                  <metricsData.obvTrendIcon
                    className="mr-1 h-5 w-5"
                    size={16}
                  />
                )}
                <span>{metricsData.obvTrendText}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {showIndicatorPanel && showIndicators && (
        <div className="card p-4 mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-gray-100 flex items-center">
              <Activity className="w-5 h-5 mr-2 text-primary-400" />
              Technical Indicators
            </h3>
            <button
              onClick={() => setShowIndicatorPanel(false)}
              className="text-gray-400 hover:text-gray-100"
            >
              <X size={16} />
            </button>
          </div>

          {loadingIndicators && (
            <div className="flex items-center justify-center py-4">
              <RefreshCw className="w-4 h-4 text-primary-400 animate-spin mr-2" />
              <span className="text-sm text-gray-400">
                Loading indicators...
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {availableIndicators.map((indicator) => (
              <button
                key={indicator.name}
                onClick={() => handleIndicatorToggle(indicator.name)}
                className={`p-2 rounded-lg text-sm transition-colors flex items-center space-x-2 ${
                  selectedIndicators.includes(indicator.name)
                    ? "bg-primary-600 text-white"
                    : "bg-dark-700 text-gray-300 hover:bg-dark-600"
                }`}
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: getIndicatorColor(indicator.name) }}
                />
                <span>{formatIndicatorDescription(indicator.description)}</span>
              </button>
            ))}
          </div>

          {selectedIndicators.length > 0 && (
            <div className="mt-4 pt-4 border-t border-dark-600">
              <p className="text-sm text-gray-400 mb-2">Active Indicators:</p>
              <div className="flex flex-wrap gap-2">
                {selectedIndicators.map((indicatorName) => {
                  const indicator = availableIndicators.find(
                    (i) => i.name === indicatorName
                  );
                  return (
                    <span
                      key={indicatorName}
                      className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full flex items-center space-x-1"
                    >
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{
                          backgroundColor: getIndicatorColor(indicatorName),
                        }}
                      />
                      <span>
                        {indicator
                          ? formatIndicatorDescription(indicator.description)
                          : indicatorName}
                      </span>
                      <button
                        onClick={() => handleIndicatorToggle(indicatorName)}
                        className="ml-1 hover:text-primary-300"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <div
        ref={chartContainerRef}
        style={{
          height: `${height}px`,
          width: "100%",
          position: "relative",
        }}
        className="bg-dark-950 rounded-lg border border-dark-700 overflow-hidden"
      />

      {showIndicators && Object.keys(indicatorData).length > 0 && (
        <div className="mt-4 p-3 bg-dark-800 rounded-lg border border-dark-600">
          <h4 className="text-sm font-medium text-gray-300 mb-2">
            Active Indicators
          </h4>
          <div className="flex flex-wrap gap-2">
            {Object.entries(indicatorData).map(
              ([indicatorName, indicatorValues]) => {
                if (indicatorValues && indicatorValues.length > 0) {
                  const latestValue =
                    indicatorValues[indicatorValues.length - 1];
                  const color = getIndicatorColor(indicatorName);
                  const displayName = indicatorName
                    .replace("_indicator", "")
                    .toUpperCase();

                  return (
                    <div
                      key={indicatorName}
                      className="flex items-center space-x-2 px-2 py-1 bg-dark-700 rounded text-xs"
                    >
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-gray-300">{displayName}</span>
                      <span className="text-gray-400">
                        {latestValue?.value?.toFixed(2) || "N/A"}
                      </span>
                    </div>
                  );
                }
                return null;
              }
            )}
          </div>
        </div>
      )}

      {(!data || data.length === 0) && !loading && (
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          style={{ height }}
        >
          <div className="flex flex-col items-center space-y-2">
            <BarChart3 className="w-8 h-8 text-gray-500" />
            <p className="text-gray-500">
              No chart data available for this period.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

EnhancedChart.propTypes = {
  data: PropTypes.array,
  symbol: PropTypes.string,
  period: PropTypes.string,
  onPeriodChange: PropTypes.func,
  height: PropTypes.number,
  showVolume: PropTypes.bool,
  loading: PropTypes.bool,
  onRefresh: PropTypes.func,
  showControls: PropTypes.bool,
  showPeriodSelector: PropTypes.bool,
  chartType: PropTypes.string,
  theme: PropTypes.string,
  className: PropTypes.string,
  enableFullscreen: PropTypes.bool,
  onFullscreenToggle: PropTypes.func,
  showIndicators: PropTypes.bool,
  enableIndicatorConfig: PropTypes.bool,
  defaultIndicators: PropTypes.array,
  onIndicatorsChange: PropTypes.func,
  assetId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  showReturns: PropTypes.bool,
  indicatorOverlayData: PropTypes.array,
};

export default EnhancedChart;