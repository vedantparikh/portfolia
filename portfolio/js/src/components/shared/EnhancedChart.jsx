import {
    AreaSeries,
    CandlestickSeries,
    HistogramSeries,
    LineSeries,
    createChart
} from 'lightweight-charts';
import { 
    BarChart3, 
    Maximize2, 
    Minimize2, 
    RefreshCw, 
    Settings, 
    TrendingUp, 
    Activity,
    Plus,
    X,
    ChevronDown
} from 'lucide-react';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { formatVolume, formatPercentage } from '../../utils/formatters.jsx';
import { statisticalIndicatorsAPI } from '../../services/api';

const EnhancedChart = ({
    data = [],
    symbol = '',
    period = '30d',
    onPeriodChange = () => {}, // <-- FIX 1
    height = 400,
    showVolume = true,
    loading = false,
    onRefresh,
    showControls = true,
    showPeriodSelector = true,
    chartType = 'candlestick',
    theme = 'dark',
    className = '',
    enableFullscreen = false,
    onFullscreenToggle,
    // New props for statistical indicators
    showIndicators = true,
    enableIndicatorConfig = true,
    defaultIndicators = ['SMA', 'EMA', 'RSI'],
    onIndicatorsChange,
    assetId = null,
    showReturns = true,
    enableAnalysis = true,
}) => {
    const chartContainerRef = useRef(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [availableIndicators, setAvailableIndicators] = useState([]);
    const [indicatorConfigurations, setIndicatorConfigurations] = useState([]);
    const [selectedIndicators, setSelectedIndicators] = useState(defaultIndicators);
    const [indicatorData, setIndicatorData] = useState({});
    const [showIndicatorPanel, setShowIndicatorPanel] = useState(false);
    const [showReturnsPanel, setShowReturnsPanel] = useState(false);
    const [returnsData, setReturnsData] = useState({});
    const [loadingIndicators, setLoadingIndicators] = useState(false);

    // Load available indicators and configurations on mount
    useEffect(() => {
        if (showIndicators && enableIndicatorConfig) {
            loadIndicatorsData();
        }
    }, [showIndicators, enableIndicatorConfig]);

    // Load indicator data when selected indicators change
    useEffect(() => {
        if (selectedIndicators.length > 0 && assetId && data.length > 0) {
            loadIndicatorData();
        }
    }, [selectedIndicators, assetId, data]);

    // Calculate returns data when period changes
    useEffect(() => {
        if (showReturns && data.length > 0) {
            calculateReturns();
        }
    }, [data, period, showReturns]);

    const loadIndicatorsData = async () => {
        try {
            const [indicators, configurations] = await Promise.all([
                statisticalIndicatorsAPI.getAvailableIndicators(),
                statisticalIndicatorsAPI.getConfigurations()
            ]);
            setAvailableIndicators(indicators || []);
            setIndicatorConfigurations(configurations || []);
        } catch (error) {
            console.error('Failed to load indicators data:', error);
        }
    };

    const loadIndicatorData = async () => {
        if (!assetId) return;
        
        try {
            setLoadingIndicators(true);
            const response = await statisticalIndicatorsAPI.calculateIndicators(
                assetId,
                selectedIndicators,
                { period, interval: '1d' }
            );
            setIndicatorData(response || {});
        } catch (error) {
            console.error('Failed to load indicator data:', error);
        } finally {
            setLoadingIndicators(false);
        }
    };

    const calculateReturns = () => {
        if (!data || data.length === 0) return;

        const sortedData = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        const firstPrice = sortedData[0]?.close || 0;
        const lastPrice = sortedData[sortedData.length - 1]?.close || 0;
        const highPrice = Math.max(...sortedData.map(d => d.high));
        const lowPrice = Math.min(...sortedData.map(d => d.low));

        const totalReturn = firstPrice > 0 ? ((lastPrice - firstPrice) / firstPrice) * 100 : 0;
        const maxGain = firstPrice > 0 ? ((highPrice - firstPrice) / firstPrice) * 100 : 0;
        const maxLoss = firstPrice > 0 ? ((lowPrice - firstPrice) / firstPrice) * 100 : 0;

        setReturnsData({
            totalReturn,
            maxGain,
            maxLoss,
            highPrice,
            lowPrice,
            firstPrice,
            lastPrice
        });
    };

    const { candlestickData, volumeData } = useMemo(() => {
        if (!data || data.length === 0) {
            return { candlestickData: [], volumeData: [] };
        }
        const sortedData = [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        const cData = sortedData.map(item => {
            const open = Number(item.open);
            const high = Number(item.high);
            const low = Number(item.low);
            const close = Number(item.close);
            const volume = Number(item.volume);
            
            if (isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close) || isNaN(volume)) {
                console.warn('Invalid data point:', item);
                return null;
            }
            
            return {
                time: new Date(item.date).getTime() / 1000,
                open: open,
                high: high,
                low: low,
                close: close,
                volume: volume,
            };
        }).filter(Boolean);

        const vData = sortedData.map(item => {
            const volume = Number(item.volume);
            const close = Number(item.close);
            const open = Number(item.open);
            
            if (isNaN(volume) || isNaN(close) || isNaN(open)) {
                return null;
            }
            
            return {
                time: new Date(item.date).getTime() / 1000,
                value: volume,
                color: close >= open ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            };
        }).filter(Boolean);

        return { candlestickData: cData, volumeData: vData };
    }, [data]);

    useEffect(() => {
        if (!chartContainerRef.current || chartContainerRef.current.clientWidth === 0 || candlestickData.length === 0) {
            return;
        }

        const chart = createChart(chartContainerRef.current, {
            width: chartContainerRef.current.clientWidth,
            height: height,
            layout: {
                background: { color: theme === 'dark' ? '#020617' : '#ffffff' },
                textColor: theme === 'dark' ? '#f1f5f9' : '#191919',
            },
            grid: {
                vertLines: { color: theme === 'dark' ? '#334155' : '#e1e3e6' },
                horzLines: { color: theme === 'dark' ? '#334155' : '#e1e3e6' },
            },
            crosshair: {
                mode: 1,
                vertLine: {
                    color: theme === 'dark' ? '#475569' : '#cccccc',
                    width: 1,
                    style: 2,
                },
                horzLine: {
                    color: theme === 'dark' ? '#475569' : '#cccccc',
                    width: 1,
                    style: 2,
                },
            },
            rightPriceScale: {
                borderColor: theme === 'dark' ? '#475569' : '#cccccc',
                textColor: theme === 'dark' ? '#cbd5e1' : '#191919',
            },
            timeScale: {
                borderColor: theme === 'dark' ? '#475569' : '#cccccc',
                timeVisible: true,
                secondsVisible: false,
                textColor: theme === 'dark' ? '#cbd5e1' : '#191919',
            },
        });

        if (!chart) {
            console.error('Failed to create chart');
            return;
        }

        let priceSeries;

        if (chartType === 'candlestick') {
            priceSeries = chart.addSeries(CandlestickSeries, {
                upColor: '#22c55e',
                downColor: '#ef4444',
                borderDownColor: '#dc2626',
                borderUpColor: '#16a34a',
                wickDownColor: '#dc2626',
                wickUpColor: '#16a34a',
            });
            priceSeries.setData(candlestickData);
        } else if (chartType === 'line' || chartType === 'area') {
            const lineData = candlestickData.map(d => ({ time: d.time, value: d.close }));
            if (chartType === 'area') {
                priceSeries = chart.addSeries(AreaSeries, {
                    topColor: 'rgba(14, 165, 233, 0.3)',
                    bottomColor: 'rgba(14, 165, 233, 0.0)',
                    lineColor: '#0ea5e9',
                    lineWidth: 2,
                });
            } else {
                priceSeries = chart.addSeries(LineSeries, {
                    color: '#0ea5e9',
                    lineWidth: 2
                });
            }
            priceSeries.setData(lineData);
        }

        // Add indicator overlays
        if (showIndicators && Object.keys(indicatorData).length > 0) {
            Object.entries(indicatorData).forEach(([indicatorName, indicatorValues]) => {
                if (indicatorValues && indicatorValues.length > 0) {
                    const series = chart.addSeries(LineSeries, {
                        color: getIndicatorColor(indicatorName),
                        lineWidth: 2,
                        priceLineVisible: false,
                        lastValueVisible: false,
                    });
                    series.setData(indicatorValues);
                }
            });
        }

        if (showVolume) {
            const volumeSeries = chart.addSeries(HistogramSeries, {
                priceFormat: { type: 'volume' },
                priceScaleId: '',
                scaleMargins: { top: 0.8, bottom: 0 },
            });
            volumeSeries.setData(volumeData);
        }

        chart.timeScale().fitContent();

        const tooltip = document.createElement('div');
        tooltip.className = 'absolute bg-dark-800 border border-dark-600 rounded-lg p-3 shadow-xl z-50 pointer-events-none opacity-0 transition-opacity duration-200';
        tooltip.style.fontSize = '12px';
        tooltip.style.fontFamily = 'Inter, system-ui, sans-serif';
        chartContainerRef.current.appendChild(tooltip);

        const updateTooltip = (param) => {
            if (!param.point || !param.time || !chartContainerRef.current) {
                tooltip.style.opacity = '0';
                return;
            }

            const data = param.seriesData.get(priceSeries);
            if (!data) {
                tooltip.style.opacity = '0';
                return;
            }

            const originalData = candlestickData.find(item => item.time === data.time);
            const volume = originalData ? originalData.volume : null;

            const date = new Date(data.time * 1000).toLocaleDateString();
            const time = new Date(data.time * 1000).toLocaleTimeString();
            let tooltipContent = '';
            
            if (chartType === 'candlestick') {
                tooltipContent = `
                    <div class="text-gray-100 font-semibold mb-2">${symbol || 'Asset'} - ${date}</div>
                    <div class="space-y-1 text-xs">
                        <div class="flex justify-between"><span class="text-gray-400">Open:</span><span class="text-gray-200">$${data.open?.toFixed(2) || 'N/A'}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">High:</span><span class="text-success-400">$${data.high?.toFixed(2) || 'N/A'}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">Low:</span><span class="text-danger-400">$${data.low?.toFixed(2) || 'N/A'}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">Close:</span><span class="text-gray-200">$${data.close?.toFixed(2) || 'N/A'}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">Volume:</span><span class="text-gray-200">${formatVolume(volume)}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">Change:</span><span class="${data.close >= data.open ? 'text-success-400' : 'text-danger-400'}">${data.close && data.open ? ((data.close - data.open) / data.open * 100).toFixed(2) + '%' : 'N/A'}</span></div>
                    </div>
                `;
            } else {
                tooltipContent = `
                    <div class="text-gray-100 font-semibold mb-2">${symbol || 'Asset'} - ${date}</div>
                    <div class="space-y-1 text-xs">
                        <div class="flex justify-between"><span class="text-gray-400">Time:</span><span class="text-gray-200">${time}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">Price:</span><span class="text-primary-400">$${data.value?.toFixed(2) || 'N/A'}</span></div>
                        <div class="flex justify-between"><span class="text-gray-400">Volume:</span><span class="text-gray-200">${formatVolume(volume)}</span></div>
                    </div>
                `;
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
            tooltip.style.opacity = '1';
        };

        chart.subscribeCrosshairMove(updateTooltip);

        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            if (tooltip && tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
            chart.remove();
        };

    }, [candlestickData, volumeData, theme, height, showVolume, chartType, symbol, showIndicators, indicatorData]);

    const getIndicatorColor = (indicatorName) => {
        const colors = {
            'SMA': '#ff6b6b',
            'EMA': '#4ecdc4',
            'RSI': '#45b7d1',
            'MACD': '#96ceb4',
            'BB': '#feca57',
            'STOCH': '#ff9ff3',
            'ADX': '#54a0ff',
            'CCI': '#5f27cd',
            'WILLR': '#00d2d3',
            'ATR': '#ff9f43'
        };
        return colors[indicatorName] || '#8884d8';
    };

    const handleIndicatorToggle = (indicator) => {
        const newIndicators = selectedIndicators.includes(indicator)
            ? selectedIndicators.filter(i => i !== indicator)
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

    const periods = [
        { value: '30d', label: '30 Days' },
        { value: '3mo', label: '3 Months' },
        { value: '6mo', label: '6 Months' },
        { value: 'ytd', label: 'YTD' }, // <-- FIX 2
        { value: '1y', label: '1 Year' },
        { value: '5y', label: '5 Years' },
        { value: 'max', label: 'All' }
    ];

    if (loading) {
        return (
            <div className={`flex items-center justify-center ${className}`} style={{ height }}>
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
                        {showPeriodSelector && periods.map(periodOption => (
                            <button
                                key={periodOption.value}
                                onClick={() => onPeriodChange(periodOption.value)}
                                className={`px-3 py-1 text-xs rounded-md transition-colors ${period === periodOption.value
                                    ? 'bg-primary-600 text-white font-semibold'
                                    : 'bg-dark-800 text-gray-400 hover:bg-dark-700'
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
                                <ChevronDown size={14} className={`transition-transform ${showIndicatorPanel ? 'rotate-180' : ''}`} />
                            </button>
                        )}
                        {enableFullscreen && (
                            <button
                                onClick={handleFullscreenToggle}
                                className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-700 rounded transition-colors"
                                title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
                            >
                                {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
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

            {/* Returns Panel */}
            {showReturnsPanel && showReturns && (
                <div className="card p-4 mb-4">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-lg font-semibold text-gray-100 flex items-center">
                            <TrendingUp className="w-5 h-5 mr-2 text-primary-400" />
                            Performance Returns
                        </h3>
                        <button
                            onClick={() => setShowReturnsPanel(false)}
                            className="text-gray-400 hover:text-gray-100"
                        >
                            <X size={16} />
                        </button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Total Return</p>
                            <p className={`text-lg font-bold ${returnsData.totalReturn >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {formatPercentage(returnsData.totalReturn || 0)}
                            </p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Max Gain</p>
                            <p className="text-lg font-bold text-success-400">
                                {formatPercentage(returnsData.maxGain || 0)}
                            </p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Max Loss</p>
                            <p className="text-lg font-bold text-danger-400">
                                {formatPercentage(returnsData.maxLoss || 0)}
                            </p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Price Range</p>
                            <p className="text-sm font-medium text-gray-200">
                                ${returnsData.lowPrice?.toFixed(2) || '0'} - ${returnsData.highPrice?.toFixed(2) || '0'}
                            </p> 
                        </div>
                    </div>
                </div>
            )}

            {/* Indicators Panel */}
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
                            <span className="text-sm text-gray-400">Loading indicators...</span>
                        </div>
                    )}

                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                        {availableIndicators.map((indicator) => (
                            <button
                                key={indicator.name}
                                onClick={() => handleIndicatorToggle(indicator.name)}
                                className={`p-2 rounded-lg text-sm transition-colors flex items-center space-x-2 ${
                                    selectedIndicators.includes(indicator.name)
                                        ? 'bg-primary-600 text-white'
                                        : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
                                }`}
                            >
                                <div 
                                    className="w-3 h-3 rounded-full" 
                                    style={{ backgroundColor: getIndicatorColor(indicator.name) }}
                                />
                                <span>{indicator.name}</span>
                            </button>
                        ))}
                    </div>

                    {selectedIndicators.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-dark-600">
                            <p className="text-sm text-gray-400 mb-2">Active Indicators:</p>
                            <div className="flex flex-wrap gap-2">
                                {selectedIndicators.map((indicator) => (
                                    <span
                                        key={indicator}
                                        className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full flex items-center space-x-1"
                                    >
                                        <div 
                                            className="w-2 h-2 rounded-full" 
                                            style={{ backgroundColor: getIndicatorColor(indicator) }}
                                        />
                                        <span>{indicator}</span>
                                        <button
                                            onClick={() => handleIndicatorToggle(indicator)}
                                            className="ml-1 hover:text-primary-300"
                                        >
                                            <X size={12} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            <div
                ref={chartContainerRef}
                style={{
                    height: `${height}px`,
                    width: '100%',
                    position: 'relative'
                }}
                className="bg-dark-950 rounded-lg border border-dark-700 overflow-hidden"
            />

            {(!data || data.length === 0) && !loading && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none" style={{ height }}>
                    <div className="flex flex-col items-center space-y-2">
                        <BarChart3 className="w-8 h-8 text-gray-500" />
                        <p className="text-gray-500">No chart data available for this period.</p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default EnhancedChart;