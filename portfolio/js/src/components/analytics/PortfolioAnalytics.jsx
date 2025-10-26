import {
    BarChart3,
    RefreshCw,
    Shield,
    Target,
    XCircle,
    Info,
    X,
} from 'lucide-react';
import PropTypes from 'prop-types';
import React, { useCallback, useEffect, useState } from 'react';
import { analyticsAPI, portfolioCalculationsAPI } from '../../services/api';
import { formatCurrency, formatPercentage } from '../../utils/formatters.jsx';
import LoadingSpinner from '../shared/LoadingSpinner';

const PortfolioAnalytics = ({ portfolioId }) => {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    const [availablePeriods, setAvailablePeriods] = useState([]);
    const [selectedPeriod, setSelectedPeriod] = useState("inception"); 
    
    const [showRiskModal, setShowRiskModal] = useState(false);

    const loadAvailablePeriods = async () => {
        try {
            const response = await portfolioCalculationsAPI.getAvailablePeriods();
            const periods = response.periods || [];
            setAvailablePeriods(periods);
            
            if (periods.length > 0 && !periods.find(p => p.period_code === 'inception')) {
                setSelectedPeriod(periods[0].period_code);
            }
        } catch (error) {
            console.error("Failed to load available periods:", error);
            setAvailablePeriods([{ period_code: 'inception', period_name: 'Since Inception' }]);
        }
    };

    const loadAnalyticsData = useCallback(async (forceRefresh = false) => {
        if (!portfolioId) return; 

        try {
            if (forceRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            setError(null);

            const [riskMetrics, advanceRiskMetrics] = await Promise.allSettled([
                analyticsAPI.getPortfolioRiskMetrics(portfolioId, selectedPeriod),
                analyticsAPI.getPortfolioAdvanceRiskMetrics(portfolioId, selectedPeriod),
            ]);

            const analytics = {
                riskMetrics: riskMetrics.status === 'fulfilled' ? riskMetrics.value : null,
                advanceRiskMetrics: advanceRiskMetrics.status === 'fulfilled' ? advanceRiskMetrics.value : null,
            };

            setAnalyticsData(analytics);
        } catch (err) {
            console.error('Failed to load analytics data:', err);
            setError('Failed to load analytics data. Please try again.');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [portfolioId, selectedPeriod]);


    useEffect(() => {
        if (portfolioId) {
            setLoading(true);
            loadAvailablePeriods();
        }
    }, [portfolioId]);

    useEffect(() => {
        if (portfolioId) {
            loadAnalyticsData();
        }
    }, [portfolioId, selectedPeriod, loadAnalyticsData]); 


    const handleRefresh = () => {
        loadAnalyticsData(true);
    };

    const getRiskLevelClass = (level) => {
        switch (level) {
            case 'low':
                return 'bg-success-400/20 text-success-400';
            case 'moderate':
                return 'bg-warning-400/20 text-warning-400';
            case 'high':
                return 'bg-danger-400/20 text-danger-400';
            case 'very_high':
                return 'bg-danger-700/30 text-danger-300';
            default:
                return 'bg-gray-400/20 text-gray-400';
        }
    };

    if (loading && !refreshing) {
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
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <h2 className="text-2xl font-bold text-gray-100">Portfolio Analytics</h2>
                <div className="flex items-center space-x-3">
                    <select
                        value={selectedPeriod}
                        onChange={(e) => setSelectedPeriod(e.target.value)}
                        className="input-field text-sm"
                        disabled={refreshing || loading}
                    >
                        {availablePeriods.map((period) => (
                            <option key={period.period_code} value={period.period_code}>
                                {period.period_name}
                            </option>
                        ))}
                    </select>

                    <button
                        onClick={handleRefresh}
                        disabled={refreshing || loading}
                        className="btn-outline flex items-center space-x-2"
                    >
                        <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
                        <span>Refresh</span>
                    </button>
                </div>
            </div>


            {/* Risk Analysis */}
            {!riskMetrics && !advanceRiskMetrics ? (
                <div className="card p-6 text-center">
                    <BarChart3 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-gray-300 mb-2">No Analytics Data Available</h3>
                    <p className="text-gray-500">Analytics data could not be calculated for the selected period.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Risk Metrics Card */}
                    {riskMetrics ? (
                        <div className="card p-6">
                            <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                                <Shield className="w-5 h-5 mr-2 text-primary-400" />
                                Risk Metrics
                            </h3>
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400 flex items-center">
                                        Risk Level
                                        {riskMetrics.risk_assessment && (
                                            <Info 
                                                size={14} 
                                                className="ml-1.5 text-gray-500 hover:text-gray-300 cursor-pointer"
                                                onClick={() => setShowRiskModal(true)} 
                                            />
                                        )}
                                    </span>
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                                        getRiskLevelClass(riskMetrics.risk_assessment?.level)
                                    }`}>
                                        {riskMetrics.risk_assessment?.level?.replace('_', ' ').toUpperCase() || 'N/A'}
                                    </span>
                                </div>

                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">Portfolio Volatility</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.annualized_volatility_pct ? formatPercentage(parseFloat(riskMetrics.metrics.annualized_volatility_pct)) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">VaR (95%)</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.value_at_risk_95_pct ? formatCurrency(parseFloat(riskMetrics.metrics.value_at_risk_95_pct)) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">VaR (99%)</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.value_at_risk_99_pct ? formatCurrency(parseFloat(riskMetrics.metrics.value_at_risk_99_pct)) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">CVaR (95%)</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.cvar_95 ? formatPercentage(parseFloat(riskMetrics.metrics.cvar_95)) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">Max Drawdown</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.max_drawdown ? formatPercentage(parseFloat(riskMetrics.metrics.max_drawdown)) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">Sharpe Ratio</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.sharpe_ratio ? parseFloat(riskMetrics.metrics.sharpe_ratio).toFixed(2) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">Sortino Ratio</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.sortino_ratio ? parseFloat(riskMetrics.metrics.sortino_ratio).toFixed(2) : 'N/A'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-400">Calmar Ratio</span>
                                    <span className="text-sm font-medium text-gray-100">
                                        {riskMetrics.metrics?.calmar_ratio ? parseFloat(riskMetrics.metrics.calmar_ratio).toFixed(2) : 'N/A'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="card p-6 flex flex-col items-center justify-center text-center">
                            <Shield className="w-8 h-8 mr-2 text-gray-600 mb-3" />
                            <h3 className="text-lg font-semibold text-gray-300 mb-2">Risk Metrics Unavailable</h3>
                            <p className="text-sm text-gray-500">Could not calculate standard risk metrics for this period.</p>
                        </div>
                    )}

                    {/* Advanced Metrics Card */}
                    {advanceRiskMetrics ? (
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
                    ) : (
                        <div className="card p-6 flex flex-col items-center justify-center text-center">
                            <Target className="w-8 h-8 mr-2 text-gray-600 mb-3" />
                            <h3 className="text-lg font-semibold text-gray-300 mb-2">Advanced Metrics Unavailable</h3>
                            <p className="text-sm text-gray-500">Could not calculate advanced metrics for this period.</p>
                        </div>
                    )}
                </div>
            )}

            {showRiskModal && riskMetrics?.risk_assessment && (
                <div 
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
                    onClick={() => setShowRiskModal(false)}
                >
                    <div 
                        className="card p-6 rounded-lg max-w-md w-full m-4 shadow-xl border border-dark-600"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-semibold text-gray-100 flex items-center">
                                <Shield className="w-5 h-5 mr-2 text-primary-400" />
                                Risk Level Analysis
                            </h4>
                            <button onClick={() => setShowRiskModal(false)} className="text-gray-400 hover:text-gray-300">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="space-y-4">
                            <p className="text-sm text-gray-300">
                                Your portfolio's risk level is assessed as:
                            </p>
                            <div className="text-center my-4">
                                <span className={`px-4 py-2 rounded-full text-lg font-medium ${
                                    getRiskLevelClass(riskMetrics.risk_assessment.level)
                                }`}>
                                    {riskMetrics.risk_assessment.level.replace('_', ' ').toUpperCase()}
                                </span>
                            </div>
                            <p className="text-sm font-semibold text-gray-100">Reasoning:</p>
                            <p 
                                className="text-sm text-gray-400 leading-relaxed"
                                dangerouslySetInnerHTML={{ __html: riskMetrics.risk_assessment.reasoning }}
                            />
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
};

PortfolioAnalytics.propTypes = {
    portfolioId: PropTypes.string.isRequired,
};

export default PortfolioAnalytics;