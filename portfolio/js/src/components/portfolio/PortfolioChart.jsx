import {
    Activity,
    Download,
    PieChart,
    RefreshCw,
    TrendingUp
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { analyticsAPI, portfolioAPI } from '../../services/api';
import {
    formatCurrency,
    formatMetricValue,
    formatPercentage,
    getChangeColor
} from '../../utils/formatters.jsx';

const PortfolioChart = ({ portfolio, stats }) => {
    const [chartData, setChartData] = useState(null);
    const [allocationData, setAllocationData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [timeRange, setTimeRange] = useState('1mo');
    const [chartType, setChartType] = useState('line');

    const timeRanges = [
        { value: '1d', label: '1 Day', days: 1 },
        { value: '5d', label: '5 Days', days: 5 },
        { value: '1mo', label: '1 Month', days: 30 },
        { value: '3mo', label: '3 Months', days: 90 },
        { value: '6mo', label: '6 Months', days: 180 },
        { value: '1y', label: '1 Year', days: 365 },
        { value: 'ytd', label: 'YTD', days: 365 },
        { value: 'max', label: 'All Time', days: 9999 }
    ];

    const chartTypes = [
        { value: 'line', label: 'Line Chart', icon: TrendingUp },
        { value: 'pie', label: 'Allocation', icon: PieChart }
    ];

    useEffect(() => {
        if (portfolio?.id) {
            loadChartData();
            loadAllocationData();
        }
    }, [portfolio, timeRange]);

    const loadChartData = async () => {
        if (!portfolio?.id) return;

        try {
            setLoading(true);
            setChartData(null); // Clear previous data
            console.log('[PortfolioChart] Loading chart data for portfolio:', portfolio.id, 'timeRange:', timeRange);

            // Get the current time range configuration
            const currentTimeRange = timeRanges.find(tr => tr.value === timeRange);
            const days = currentTimeRange?.days || 30;

            // Try to get performance history first
            try {
                const historyResponse = await analyticsAPI.getPortfolioPerformanceHistory(portfolio.id, days);
                console.log('[PortfolioChart] Performance history response:', historyResponse);

                if (historyResponse?.history && historyResponse.history.length > 0) {
                    // Process the history data for chart display
                    const processedData = processHistoryData(historyResponse.history);
                    setChartData(processedData);
                    return; // Successfully loaded data
                }
            } catch (historyError) {
                console.warn('[PortfolioChart] Failed to load performance history:', historyError);
                // Do not load mock data, let it be null
            }

            // If API fails or returns no data, chartData remains null
            console.log('[PortfolioChart] No performance history data found or API failed.');

        } catch (error) {
            console.error('[PortfolioChart] Failed to load chart data:', error);
            // Do not load mock data, chartData will be null
        } finally {
            setLoading(false);
        }
    };

    const loadAllocationData = async () => {
        if (!portfolio?.id) return;

        try {
            setAllocationData(null); // Clear previous data
            console.log('[PortfolioChart] Loading allocation data for portfolio:', portfolio.id);
            try {
                const holdingsResponse = await portfolioAPI.getPortfolioHoldings(portfolio.id);
                console.log('[PortfolioChart] Holdings response:', holdingsResponse);

                if (holdingsResponse && holdingsResponse.length > 0) {
                    // Convert holdings to allocation format
                    const totalValue = holdingsResponse.reduce((sum, holding) => sum + (parseFloat(holding.current_value) || 0), 0);
                    const allocations = holdingsResponse.map(holding => ({
                        asset_id: holding.asset_id,
                        asset_symbol: holding.symbol,
                        asset_name: holding.name,
                        current_percentage: totalValue > 0 ? ((parseFloat(holding.current_value) || 0) / totalValue) * 100 : 0,
                        current_value: parseFloat(holding.current_value) || 0
                    }));

                    setAllocationData(allocations);
                    return; // Successfully loaded data
                }
            } catch (holdingsError) {
                console.warn('[PortfolioChart] Failed to load holdings:', holdingsError);
                // Do not load mock data, let it be null
            }
        } catch (error) {
            console.error('[PortfolioChart] Failed to load allocation data:', error);
            // Do not load mock data, allocationData will be null
        }
    };

    // Process performance history data for chart display
    const processHistoryData = (historyData) => {
        if (!historyData || historyData.length === 0) return null;

        const performanceData = historyData.map(item => ({
            date: item.snapshot_date?.split('T')[0] || new Date().toISOString().split('T')[0],
            value: parseFloat(item.total_value) || 0,
            benchmark: parseFloat(item.benchmark_return) || 0
        }));

        const firstValue = performanceData[0]?.value || 0;
        const lastValue = performanceData[performanceData.length - 1]?.value || 0;
        const totalReturn = firstValue > 0 ? ((lastValue - firstValue) / firstValue) * 100 : 0;

        return {
            performance_data: performanceData,
            total_return: totalReturn,
            benchmark_return: performanceData[performanceData.length - 1]?.benchmark || 0,
            volatility: parseFloat(historyData[historyData.length - 1]?.volatility) || 0,
            sharpe_ratio: parseFloat(historyData[historyData.length - 1]?.sharpe_ratio) || 0,
            max_drawdown: parseFloat(historyData[historyData.length - 1]?.max_drawdown) || 0
        };
    };

    // Process performance calculation data for chart display
    const processPerformanceData = (performanceData, period) => {
        if (!performanceData) return null;

        // For performance calculation, we'll generate a simple trend line
        const currentValue = parseFloat(performanceData.current_value) || stats?.totalValue || 100000;
        const totalReturn = performanceData.metrics?.cagr || performanceData.metrics?.total_return || 0;

        // Generate data points based on the period
        const currentTimeRange = timeRanges.find(tr => tr.value === timeRange);
        const days = currentTimeRange?.days || 30;
        const dataPoints = Math.min(days, 100); // Limit to 100 points for performance

        const data = [];
        const startValue = currentValue / (1 + totalReturn / 100);

        for (let i = 0; i < dataPoints; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (dataPoints - i));

            const progress = i / (dataPoints - 1);
            const value = startValue * (1 + (totalReturn / 100) * progress);

            data.push({
                date: date.toISOString().split('T')[0],
                value: value,
                benchmark: startValue * (1 + (totalReturn * 0.8 / 100) * progress) // Slightly lower benchmark
            });
        }

        return {
            performance_data: data,
            total_return: totalReturn,
            benchmark_return: totalReturn * 0.8, // Slightly lower benchmark
            volatility: performanceData.metrics?.volatility || 0,
            sharpe_ratio: performanceData.metrics?.sharpe_ratio || 0,
            max_drawdown: performanceData.metrics?.max_drawdown || 0
        };
    };

    const renderLineChart = () => {
        if (!chartData?.performance_data || chartData.performance_data.length === 0) {
            return (
                <div className="flex items-center justify-center h-80">
                    <div className="text-center">
                        <TrendingUp size={48} className="text-gray-500 mx-auto mb-4" />
                        <p className="text-gray-400">No performance data available</p>
                    </div>
                </div>
            );
        }

        const data = chartData.performance_data;
        const maxValue = Math.max(...data.map(d => Math.max(d.value || 0, d.benchmark || 0)));
        const minValue = Math.min(...data.map(d => Math.min(d.value || 0, d.benchmark || 0)));
        const range = maxValue - minValue || 1; // Avoid division by zero

        return (
            <div className="h-80 relative">
                <svg className="w-full h-full" viewBox="0 0 800 320">
                    {/* Grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => (
                        <g key={i}>
                            <line
                                x1="50"
                                y1={50 + ratio * 240}
                                x2="750"
                                y2={50 + ratio * 240}
                                stroke="currentColor"
                                strokeWidth="1"
                                className="text-dark-700"
                            />
                            <text
                                x="40"
                                y={50 + ratio * 240 + 4}
                                textAnchor="end"
                                className="text-xs fill-gray-500"
                            >
                                {formatCurrency(maxValue - (range * ratio))}
                            </text>
                        </g>
                    ))}

                    {/* Portfolio line */}
                    <polyline
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="text-primary-400"
                        points={data.map((d, i) =>
                            `${50 + (i / (data.length - 1)) * 700},${50 + ((maxValue - d.value) / range) * 240}`
                        ).join(' ')}
                    />

                    {/* Benchmark line */}
                    <polyline
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeDasharray="5,5"
                        className="text-gray-500"
                        points={data.map((d, i) =>
                            `${50 + (i / (data.length - 1)) * 700},${50 + ((maxValue - d.benchmark) / range) * 240}`
                        ).join(' ')}
                    />

                    {/* Data points */}
                    {data.map((d, i) => (
                        <circle
                            key={i}
                            cx={50 + (i / (data.length - 1)) * 700}
                            cy={50 + ((maxValue - d.value) / range) * 240}
                            r="3"
                            fill="currentColor"
                            className="text-primary-400"
                        />
                    ))}
                </svg>

                {/* Legend */}
                <div className="absolute top-4 right-4 flex space-x-4">
                    <div className="flex items-center space-x-2">
                        <div className="w-4 h-0.5 bg-primary-400"></div>
                        <span className="text-xs text-gray-300">Portfolio</span>
                    </div>
                    <div className="flex items-center space-x-2">
                        <div className="w-4 h-0.5 bg-gray-500 border-dashed border-t border-gray-500"></div>
                        <span className="text-xs text-gray-300">Benchmark</span>
                    </div>
                </div>
            </div>
        );
    };

    const renderPieChart = () => {
        // Use real allocation data
        const allocations = allocationData;

        // Extended color palette for more distinct colors on a dark background
        const colors = [
            '#4a90e2', // Bright Blue
            '#50e3c2', // Aqua Green
            '#f5a623', // Orange Yellow
            '#bd10e0', // Bright Purple
            '#e86060', // Soft Red
            '#51af39', // Darker Green
            '#ffcd45', // Golden Yellow
            '#7ed321', // Lime Green
            '#4a4ae2', // Indigo
            '#e24a90', // Pinkish Purple
            '#a16b3f', // Brownish Orange
            '#42c2ea', // Sky Blue
            '#9b9b9b', // Light Gray
            '#ff784f', // Coral
            '#8f55e0', // Medium Purple
            '#33d9b2', // Mint Green
            '#f7d730', // Vibrant Yellow
            '#6a4aeb', // Darker Violet
            '#ff6f61', // Light Red
            '#00c7b6', // Teal
        ];

        // Process allocation data for pie chart
        // Safely map only if allocations exist
        const pieData = (allocations && allocations.length > 0)
            ? allocations.map((allocation, index) => ({
                name: allocation.asset_name || `Asset ${index + 1}`,
                value: parseFloat(allocation.current_percentage) || 0,
                color: colors[index % colors.length],
                symbol: allocation.asset_symbol || '',
                value_amount: parseFloat(allocation.current_value) || 0
            })).filter(item => item.value > 0) // Only show assets with value
            : []; // Default to empty array if no allocations

        // Single check for no data (if API data is null, empty, or all values are 0)
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
        const gradientStops = pieData.map(allocation => {
            const start = cumulativePercentage;
            const end = cumulativePercentage + allocation.value;
            cumulativePercentage = end;
            return `${allocation.color} ${start}% ${end}%`;
        }).join(', ');

        const pieStyle = {
            background: `conic-gradient(${gradientStops})`,
        };

        return (
            <div className="h-80 flex items-center justify-center">
                <div className="relative w-64 h-64">
                    <div
                        className="w-full h-full rounded-full"
                        style={pieStyle}
                    />

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
                                <div className="text-sm text-gray-300 truncate">{allocation.name}</div>
                                {allocation.symbol && (
                                    <div className="text-xs text-gray-500">{allocation.symbol}</div>
                                )}
                            </div>
                            <div className="text-right">
                                <div className="text-sm font-medium text-gray-100">{allocation.value.toFixed(1)}%</div>
                                <div className="text-xs text-gray-500">{formatCurrency(allocation.value_amount)}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    const renderChart = () => {
        switch (chartType) {
            case 'line':
                return renderLineChart();
            case 'pie':
                return renderPieChart();
            default:
                return renderLineChart();
        }
    };

    return (
        <div className="space-y-6">
            {/* Chart Controls */}
            <div className="card p-6">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-gray-100">Portfolio Performance</h3>
                    <div className="flex items-center space-x-3">
                        <button
                            onClick={() => {
                                loadChartData();
                                loadAllocationData();
                            }}
                            disabled={loading}
                            className="btn-outline text-sm flex items-center space-x-2"
                        >
                            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
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
                    <span className="text-sm text-gray-400">Time Range:</span>
                    {timeRanges.map((range) => (
                        <button
                            key={range.value}
                            onClick={() => setTimeRange(range.value)}
                            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${timeRange === range.value
                                ? 'bg-primary-600 text-white'
                                : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
                                }`}
                        >
                            {range.label}
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
                                className={`flex items-center space-x-2 px-3 py-1 rounded-lg text-sm font-medium transition-colors ${chartType === type.value
                                    ? 'bg-primary-600 text-white'
                                    : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
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
                        // This block now correctly handles the null state for chartData
                        <div className="flex items-center justify-center h-80">
                            <div className="text-center">
                                <TrendingUp size={48} className="text-gray-500 mx-auto mb-4" />
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

            {/* Performance Metrics */}
            {/* This block will only render if chartData is successfully loaded */}
            {chartData && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Total Return</p>
                                <p className={`text-2xl font-bold ${getChangeColor(chartData.total_return || 0)}`}>
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
                                    {formatPercentage(chartData.volatility || 0, { precision: 1 })}
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

export default PortfolioChart;