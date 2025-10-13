import {
    Activity,
    AlertTriangle,
    BarChart3,
    DollarSign,
    RefreshCw,
    Shield,
    Target,
    TrendingUp
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import { formatCurrency, formatPercentage } from '../../utils/formatters.jsx';
import LoadingSpinner from '../shared/LoadingSpinner';

const AnalyticsDashboard = () => {
    const [analyticsData, setAnalyticsData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        loadAnalyticsData();
    }, []);

    const loadAnalyticsData = async (forceRefresh = true) => {
        try {
            if (forceRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            setError(null);

            const [dashboardData, assetsData] = await Promise.allSettled([
                analyticsAPI.getUserAnalyticsDashboard(),
                analyticsAPI.getUserAssetsAnalytics()
            ]);

            setAnalyticsData({
                dashboard: dashboardData.status === 'fulfilled' ? dashboardData.value : null,
                assets: assetsData.status === 'fulfilled' ? assetsData.value : null,
            });
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
                <LoadingSpinner size="lg" text="Loading analytics..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <AlertTriangle className="w-16 h-16 text-danger-400 mx-auto mb-4" />
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
                <p className="text-gray-500">Analytics data is not available.</p>
            </div>
        );
    }

    const { dashboard, assets } = analyticsData;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100">Analytics Dashboard</h2>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="btn-outline flex items-center space-x-2"
                >
                    <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
                    <span>Refresh</span>
                </button>
            </div>

            {/* Portfolio Analytics Summary */}
            {dashboard?.portfolios && (
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <BarChart3 className="w-5 h-5 mr-2 text-primary-400" />
                        Portfolio Analytics Summary
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Total Portfolios</p>
                            <p className="text-2xl font-bold text-gray-100">
                                {dashboard.portfolios.total_portfolios || 0}
                            </p>
                        </div>

                        <div className="text-center">
                            <p className="text-sm text-gray-400">Active Portfolios</p>
                            <p className="text-2xl font-bold text-gray-100">
                                {dashboard.portfolios.active_portfolios || 0}
                            </p>
                        </div>

                        <div className="text-center">
                            <p className="text-sm text-gray-400">Total Assets</p>
                            <p className="text-2xl font-bold text-gray-100">
                                {dashboard.portfolios.total_assets || 0}
                            </p>
                        </div>

                        <div className="text-center">
                            <p className="text-sm text-gray-400">Total Value</p>
                            <p className="text-2xl font-bold text-gray-100">
                                {formatCurrency(dashboard.portfolios.total_value || 0)}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Assets Analytics */}
            {assets && (
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <Activity className="w-5 h-5 mr-2 text-primary-400" />
                        Assets Analytics
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Total Assets</p>
                            <p className="text-2xl font-bold text-gray-100">
                                {assets.total_assets || 0}
                            </p>
                        </div>

                        <div className="text-center">
                            <p className="text-sm text-gray-400">User ID</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {assets.user_id || 'N/A'}
                            </p>
                        </div>

                        <div className="text-center">
                            <p className="text-sm text-gray-400">Assets Data</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {assets.assets?.length || 0} items
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Analytics Summary */}
            {dashboard?.analytics && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                            <TrendingUp className="w-5 h-5 mr-2 text-primary-400" />
                            Performance Overview
                        </h3>

                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Summary Date</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {new Date(dashboard.analytics.summary_date).toLocaleDateString()}
                                </span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Total Return</span>
                                <span className={`text-sm font-medium ${dashboard.analytics.total_return && parseFloat(dashboard.analytics.total_return) >= 0
                                    ? 'text-success-400'
                                    : 'text-danger-400'
                                    }`}>
                                    {dashboard.analytics.total_return ? formatPercentage(parseFloat(dashboard.analytics.total_return)) : 'N/A'}
                                </span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Volatility</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {dashboard.analytics.volatility ? formatPercentage(parseFloat(dashboard.analytics.volatility)) : 'N/A'}
                                </span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Sharpe Ratio</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {dashboard.analytics.sharpe_ratio ? parseFloat(dashboard.analytics.sharpe_ratio).toFixed(2) : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                            <Shield className="w-5 h-5 mr-2 text-primary-400" />
                            Risk Metrics
                        </h3>

                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Risk Level</span>
                                <span className={`px-3 py-1 rounded-full text-sm font-medium ${dashboard.analytics.risk_level === 'low' ? 'bg-success-400/20 text-success-400' :
                                    dashboard.analytics.risk_level === 'moderate' ? 'bg-warning-400/20 text-warning-400' :
                                        dashboard.analytics.risk_level === 'high' ? 'bg-danger-400/20 text-danger-400' :
                                            'bg-gray-400/20 text-gray-400'
                                    }`}>
                                    {dashboard.analytics.risk_level?.replace('_', ' ').toUpperCase() || 'N/A'}
                                </span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Max Drawdown</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {dashboard.analytics.max_drawdown ? formatPercentage(parseFloat(dashboard.analytics.max_drawdown)) : 'N/A'}
                                </span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Beta</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {dashboard.analytics.beta ? parseFloat(dashboard.analytics.beta).toFixed(2) : 'N/A'}
                                </span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-400">Alpha</span>
                                <span className="text-sm font-medium text-gray-100">
                                    {dashboard.analytics.alpha ? formatPercentage(parseFloat(dashboard.analytics.alpha)) : 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Quick Actions */}
            <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Quick Actions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <button className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                        <BarChart3 className="w-8 h-8 text-primary-400 mx-auto mb-2" />
                        <h4 className="font-medium text-gray-100">View Analytics</h4>
                        <p className="text-sm text-gray-400">Detailed portfolio analytics</p>
                    </button>

                    <button className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                        <Target className="w-8 h-8 text-success-400 mx-auto mb-2" />
                        <h4 className="font-medium text-gray-100">Manage Allocations</h4>
                        <p className="text-sm text-gray-400">Set target allocations</p>
                    </button>

                    <button className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                        <Activity className="w-8 h-8 text-warning-400 mx-auto mb-2" />
                        <h4 className="font-medium text-gray-100">Rebalancing</h4>
                        <p className="text-sm text-gray-400">View recommendations</p>
                    </button>

                    <button className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                        <DollarSign className="w-8 h-8 text-danger-400 mx-auto mb-2" />
                        <h4 className="font-medium text-gray-100">Benchmarks</h4>
                        <p className="text-sm text-gray-400">Compare performance</p>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AnalyticsDashboard;
