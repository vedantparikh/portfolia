import {
    BarChart3,
    RefreshCw,
    Shield,
    Target,
    TrendingDown,
    TrendingUp,
    XCircle
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import { formatCurrency, formatPercentage } from '../../utils/formatters.jsx';
import LoadingSpinner from '../shared/LoadingSpinner';

const PortfolioAnalytics = ({ portfolioId }) => {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        if (portfolioId) {
            loadAnalyticsData();
        }
    }, [portfolioId]);

    const loadAnalyticsData = async (forceRefresh = true) => {
        try {
            if (forceRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            setError(null);

            const [summary, riskMetrics, performanceSnapshot] = await Promise.allSettled([
                analyticsAPI.getPortfolioAnalyticsSummary(portfolioId),
                analyticsAPI.getPortfolioRiskMetrics(portfolioId),
                analyticsAPI.getPerformanceSnapshot(portfolioId, forceRefresh)
            ]);

            const analytics = {
                summary: summary.status === 'fulfilled' ? summary.value : null,
                riskMetrics: riskMetrics.status === 'fulfilled' ? riskMetrics.value : null,
                performanceSnapshot: performanceSnapshot.status === 'fulfilled' ? performanceSnapshot.value : null,
            };

            setAnalyticsData(analytics);
        } catch (err) {
            console.error('Failed to load analytics data:', err);
            setError('Failed to load analytics data');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleRefresh = () => {
        loadAnalyticsData(true);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <LoadingSpinner type="analyst" size="lg" text="Loading analytics..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <XCircle className="w-16 h-16 text-danger-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">Error Loading Analytics</h3>
                <p className="text-gray-500 mb-4">{error}</p>
                <button onClick={handleRefresh} className="btn-primary">
                    Try Again
                </button>
            </div>
        );
    }

    if (!analyticsData) {
        return (
            <div className="text-center py-12">
                <BarChart3 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">No Analytics Data</h3>
                <p className="text-gray-500">Analytics data is not available for this portfolio.</p>
            </div>
        );
    }

    const { summary, riskMetrics, performanceSnapshot } = analyticsData;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100">Portfolio Analytics</h2>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="btn-outline flex items-center space-x-2"
                >
                    <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
                    <span>Refresh</span>
                </button>
            </div>

            {/* Performance Overview */}
            {performanceSnapshot && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Total Value</p>
                                <p className="text-2xl font-bold text-gray-100">
                                    {formatCurrency(parseFloat(performanceSnapshot.total_value))}
                                </p>
                            </div>
                            <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                <TrendingUp size={24} className="text-primary-400" />
                            </div>
                        </div>
                        <div className="mt-4">
                            <p className="text-sm text-gray-400">Cost Basis</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {formatCurrency(parseFloat(performanceSnapshot.total_cost_basis))}
                            </p>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Unrealized P&L</p>
                                <p className={`text-2xl font-bold ${parseFloat(performanceSnapshot.total_unrealized_pnl) >= 0
                                    ? 'text-success-400'
                                    : 'text-danger-400'
                                    }`}>
                                    {parseFloat(performanceSnapshot.total_unrealized_pnl) >= 0 ? '+' : ''}
                                    {formatCurrency(parseFloat(performanceSnapshot.total_unrealized_pnl))}
                                </p>
                            </div>
                            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${parseFloat(performanceSnapshot.total_unrealized_pnl) >= 0
                                ? 'bg-success-600/20'
                                : 'bg-danger-600/20'
                                }`}>
                                {parseFloat(performanceSnapshot.total_unrealized_pnl) >= 0 ? (
                                    <TrendingUp size={24} className="text-success-400" />
                                ) : (
                                    <TrendingDown size={24} className="text-danger-400" />
                                )}
                            </div>
                        </div>
                        <div className="mt-4">
                            <p className="text-sm text-gray-400">Return %</p>
                            <p className={`text-lg font-semibold ${parseFloat(performanceSnapshot.total_unrealized_pnl_percent) >= 0
                                ? 'text-success-400'
                                : 'text-danger-400'
                                }`}>
                                {parseFloat(performanceSnapshot.total_unrealized_pnl_percent) >= 0 ? '+' : ''}
                                {formatPercentage(parseFloat(performanceSnapshot.total_unrealized_pnl_percent))}
                            </p>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Total Return</p>
                                <p className={`text-2xl font-bold ${summary?.total_return && parseFloat(summary.total_return) >= 0
                                    ? 'text-success-400'
                                    : 'text-danger-400'
                                    }`}>
                                    {summary?.total_return ? formatPercentage(parseFloat(summary.total_return)) : 'N/A'}
                                </p>
                            </div>
                            <div className="w-12 h-12 bg-warning-600/20 rounded-lg flex items-center justify-center">
                                <BarChart3 size={24} className="text-warning-400" />
                            </div>
                        </div>
                        <div className="mt-4">
                            <p className="text-sm text-gray-400">Annualized</p>
                            <p className={`text-lg font-semibold ${summary?.annualized_return && parseFloat(summary.annualized_return) >= 0
                                ? 'text-success-400'
                                : 'text-danger-400'
                                }`}>
                                {summary?.annualized_return ? formatPercentage(parseFloat(summary.annualized_return)) : 'N/A'}
                            </p>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Volatility</p>
                                <p className="text-2xl font-bold text-gray-100">
                                    {summary?.volatility ? formatPercentage(parseFloat(summary.volatility)) : 'N/A'}
                                </p>
                            </div>
                            <div className="w-12 h-12 bg-gray-600/20 rounded-lg flex items-center justify-center">
                                <Shield size={24} className="text-gray-400" />
                            </div>
                        </div>
                        <div className="mt-4">
                            <p className="text-sm text-gray-400">Sharpe Ratio</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {summary?.sharpe_ratio ? parseFloat(summary.sharpe_ratio).toFixed(2) : 'N/A'}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Risk Analysis */}
            {riskMetrics && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                            <Shield className="w-5 h-5 mr-2 text-primary-400" />
                            Risk Metrics
                        </h3>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Risk Level</span>
                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${riskMetrics.risk_level === 'low' ? 'bg-success-400/20 text-success-400' :
                                    riskMetrics.risk_level === 'moderate' ? 'bg-warning-400/20 text-warning-400' :
                                        riskMetrics.risk_level === 'high' ? 'bg-danger-400/20 text-danger-400' :
                                            'bg-gray-400/20 text-gray-400'
                                    }`}>
                                    {riskMetrics.risk_level?.replace('_', ' ').toUpperCase()}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Portfolio Volatility</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {formatPercentage(parseFloat(riskMetrics.metrics.annualized_volatility_pct))}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">VaR (95%)</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {formatCurrency(parseFloat(riskMetrics.metrics.value_at_risk_95_pct))}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">VaR (99%)</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {formatCurrency(parseFloat(riskMetrics.metrics.value_at_risk_99_pct))}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Max Drawdown</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {riskMetrics.metrics.max_drawdown ? formatPercentage(parseFloat(riskMetrics.metrics.max_drawdown)) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Sharpe Ratio</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {riskMetrics.metrics.sharpe_ratio ? parseFloat(riskMetrics.metrics.sharpe_ratio).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                            <Target className="w-5 h-5 mr-2 text-primary-400" />
                            Advanced Metrics
                        </h3>
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Beta</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {summary?.beta ? parseFloat(summary.beta).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Alpha</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {summary?.alpha ? formatPercentage(parseFloat(summary.alpha)) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Concentration Risk</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {summary?.concentration_risk ? formatPercentage(parseFloat(summary.concentration_risk)) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Diversification Ratio</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {summary?.diversification_ratio ? parseFloat(summary.diversification_ratio).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Effective Assets</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {summary?.effective_number_of_assets ? parseFloat(summary.effective_number_of_assets).toFixed(1) : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Benchmark Comparison */}
            {summary?.benchmark_name && (
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <BarChart3 className="w-5 h-5 mr-2 text-primary-400" />
                        Benchmark Comparison
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Benchmark</p>
                            <p className="text-lg font-semibold text-gray-100">{summary.benchmark_name}</p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Excess Return</p>
                            <p className={`text-lg font-semibold ${summary.excess_return && parseFloat(summary.excess_return) >= 0
                                ? 'text-success-400'
                                : 'text-danger-400'
                                }`}>
                                {summary.excess_return ? formatPercentage(parseFloat(summary.excess_return)) : 'N/A'}
                            </p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Information Ratio</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {summary.information_ratio ? parseFloat(summary.information_ratio).toFixed(2) : 'N/A'}
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PortfolioAnalytics;
