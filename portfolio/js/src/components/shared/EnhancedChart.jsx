import {
  createChart,
  AreaSeries,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { statisticalIndicatorsAPI } from "../../shared/api/indicators";
import {
  barChange,
  chartMoney,
  indicatorValue as formatIndicatorValue,
  renderTooltip,
} from "../../shared/ui/tooltipDom";
import { isFlagSeries, seriesLabel } from "../../utils/indicatorLabels";
import {
  formatCurrency,
  formatPercentage,
  formatVolume,
} from "../../utils/formatters.jsx";

const EnhancedChart = ({
  data = [],
  symbol = "",
  currency,
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
  const [indicatorFamilies, setIndicatorFamilies] = useState({});
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
      const families = {};
      if (Array.isArray(indicatorOverlayData)) {
        indicatorOverlayData.forEach((series) => {
          if (series.data && Array.isArray(series.data) && !isFlagSeries(series)) {
            const chartData = series.data
              .map((item) => ({
                time: new Date(item.date).getTime() / 1000,
                value: item.value,
              }))
              .sort((a, b) => a.time - b.time);
            const key = seriesLabel(series);
            transformedData[key] = chartData;
            families[key] = series.indicator_name;
          }
        });
      }
      setIndicatorData(transformedData);
      setIndicatorFamilies(families);
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
        const volume = Number(item.volume); // Corrected from item.Volume

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

    const vData = cData // Use cData to ensure alignment after filtering
      .map((item) => {
        return {
          time: item.time,
          value: item.volume,
          color:
            item.close >= item.open
              ? "rgba(34, 197, 94, 0.2)"
              : "rgba(239, 68, 68, 0.2)",
        };
      });

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
      // Each oscillator family (RSI, MACD, ADX, ...) gets its own pane below the price
      const paneOf = {};
      const paneFor = (name) => {
        if (!isOscillator(name)) return 0;
        const family = indicatorFamilies[name] || name;
        if (!(family in paneOf)) paneOf[family] = Object.keys(paneOf).length + 1;
        return paneOf[family];
      };
      Object.entries(indicatorData).forEach(
        ([indicatorName, indicatorValues]) => {
          if (indicatorValues && indicatorValues.length > 0) {
            // Oscillators (0-100 style) get their own pane below the price;
            // price-level overlays (SMA, EMA, ...) share the candles' scale
            const series = chart.addSeries(
              LineSeries,
              {
                color: getIndicatorColor(indicatorName),
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: true,
                ...(indicatorName.toLowerCase().includes("rsi") && {
                  // Fixed 0-100 so the 30/70 bands are always visible
                  autoscaleInfoProvider: () => ({
                    priceRange: { minValue: 0, maxValue: 100 },
                  }),
                }),
              },
              paneFor(indicatorName)
            );
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
      chart.panes().forEach((pane, i) => pane.setStretchFactor(i === 0 ? 1 : 0.35));
    }

    if (showVolume) {
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volumeSeries.priceScale().applyOptions({
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
      const title = `${symbol || "Asset"} - ${date}`;
      const rows =
        chartType === "candlestick"
          ? [
              { label: "Open:", value: chartMoney(data.open, currency), className: "text-gray-200" },
              { label: "High:", value: chartMoney(data.high, currency), className: "text-success-400" },
              { label: "Low:", value: chartMoney(data.low, currency), className: "text-danger-400" },
              { label: "Close:", value: chartMoney(data.close, currency), className: "text-gray-200" },
              { label: "Volume:", value: formatVolume(volume), className: "text-gray-200" },
              {
                label: "Change:",
                value: barChange(data.open, data.close),
                className:
                  data.close >= data.open ? "text-success-400" : "text-danger-400",
              },
            ]
          : [
              { label: "Time:", value: time, className: "text-gray-200" },
              {
                label: "Price:",
                value: chartMoney(data.value, currency),
                className: "text-primary-400",
              },
              { label: "Volume:", value: formatVolume(volume), className: "text-gray-200" },
            ];

      const indicatorRows = [];
      if (showIndicators && Object.keys(indicatorData).length > 0) {
        Object.entries(indicatorData).forEach(
          ([indicatorName, indicatorValues]) => {
            if (indicatorValues && indicatorValues.length > 0) {
              const indicatorValue = indicatorValues.find(
                (item) => item.time === data.time
              );
              if (indicatorValue) {
                indicatorRows.push({
                  label: `${indicatorName.replace("_indicator", "").toUpperCase()}:`,
                  value: formatIndicatorValue(indicatorValue.value),
                  className: "font-medium",
                  color: getIndicatorColor(indicatorName),
                });
              }
            }
          }
        );
      }

      renderTooltip(tooltip, {
        title,
        rows,
        sections: indicatorRows.length
          ? [{ title: "Indicators:", rows: indicatorRows }]
          : [],
      });

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
    currency,
    showIndicators,
    indicatorData,
    indicatorFamilies,
  ]);

  const getIndicatorColor = (indicatorName) => {
    const colors = {
      RSI: "#45b7d1",
      MACD: "#96ceb4",
      "MACD signal": "#feca57",
      "MACD histogram": "#94a3b8",
      "BOLLINGER BANDS bb bbm": "#feca57",
      ADX: "#54a0ff",
      CCI: "#5f27cd",
      ROC: "#00d2d3",
      "AVERAGE TRUE RANGE": "#ff9f43",
    };
    const palette = ["#ff6b6b", "#4ecdc4", "#ff9ff3", "#a29bfe", "#fd79a8", "#55efc4", "#fab1a0"];
    const hash = [...indicatorName].reduce((h, c) => h + c.charCodeAt(0), 0);
    return colors[indicatorName] || palette[hash % palette.length];
  };

  const isOscillator = (indicatorName) => {
    const oscillators = [
      "rsi",
      "stoch",
      "cci",
      "roc",
      "williams",
      "momentum",
      "macd",
      "adx",
      "aroon",
      "mfi",
    ];
    const lowerName = indicatorName.toLowerCase();
    return oscillators.some((indicator) =>
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
                className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-700 rounded-sm transition-colors"
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
                className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-700 rounded-sm transition-colors"
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
                -{formatPercentage(metricsData.maxDrawdown || 0, {showSign: false})}
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
                      className="flex items-center space-x-2 px-2 py-1 bg-dark-700 rounded-sm text-xs"
                    >
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: color }}
                      />
                      <span className="text-gray-300">{displayName}</span>
                      <span className="text-gray-400">
                        {formatIndicatorValue(latestValue?.value)}
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

export default EnhancedChart;