import {
    BarChart3,
    RefreshCw,
    Shield,
    Target,
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

            const [riskMetrics, advanceRiskMetrics] = await Promise.allSettled([
                analyticsAPI.getPortfolioRiskMetrics(portfolioId),
                analyticsAPI.getPortfolioAdvanceRiskMetrics(portfolioId),
            ]);

            const analytics = {
                riskMetrics: riskMetrics.status === 'fulfilled' ? riskMetrics.value : null,
                advanceRiskMetrics: advanceRiskMetrics.status === 'fulfilled' ? advanceRiskMetrics.value : null,
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
                <LoadingSpinner type="quantum" size="lg" text="Loading analytics..." />
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

    const { riskMetrics, advanceRiskMetrics } = analyticsData;

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
                                <span className="text-sm text-gray-400">CVaR (95%)</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {riskMetrics.metrics.cvar_95 ? formatPercentage(parseFloat(riskMetrics.metrics.cvar_95)) : 'N/A'}
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
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Sortino Ratio</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {riskMetrics.metrics.sortino_ratio ? parseFloat(riskMetrics.metrics.sortino_ratio).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Calmar Ratio</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {riskMetrics.metrics.calmar_ratio ? parseFloat(riskMetrics.metrics.calmar_ratio).toFixed(2) : 'N/A'}
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
                                    {advanceRiskMetrics.metrics?.beta ? parseFloat(advanceRiskMetrics.metrics.beta).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Alpha</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {advanceRiskMetrics.metrics?.jensens_alpha_pct ? formatPercentage(parseFloat(advanceRiskMetrics.metrics.jensens_alpha_pct)) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Concentration Risk</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {advanceRiskMetrics.metrics?.concentration_risk_hhi ? formatPercentage(parseFloat(advanceRiskMetrics.metrics.concentration_risk_hhi)) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Diversification Ratio</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {advanceRiskMetrics.metrics?.diversification_ratio ? parseFloat(advanceRiskMetrics.metrics.diversification_ratio).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Effective Assets</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {advanceRiskMetrics.metrics?.effective_number_of_assets ? parseFloat(advanceRiskMetrics.metrics.effective_number_of_assets).toFixed(1) : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PortfolioAnalytics;
