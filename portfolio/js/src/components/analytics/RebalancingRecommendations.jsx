import {
    AlertTriangle,
    ArrowRight,
    CheckCircle,
    Clock,
    DollarSign,
    RefreshCw,
    Target,
    TrendingDown,
    TrendingUp
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import { formatCurrency, formatPercentage } from '../../utils/formatters.jsx';
import LoadingSpinner from '../shared/LoadingSpinner';

const RebalancingRecommendations = ({ portfolioId }) => {
    const [recommendations, setRecommendations] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        if (portfolioId) {
            loadRecommendations();
        }
    }, [portfolioId]);

    const loadRecommendations = async (forceRefresh = false) => {
        try {
            if (forceRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            setError(null);

            const response = await analyticsAPI.getRebalancingRecommendations(portfolioId);
            setRecommendations(response);
        } catch (err) {
            console.error('Failed to load rebalancing recommendations:', err);
            setError('Failed to load rebalancing recommendations');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleRefresh = () => {
        loadRecommendations(true);
    };

    const getPriorityColor = (priority) => {
        switch (priority?.toLowerCase()) {
            case 'high':
                return 'text-danger-400 bg-danger-400/20';
            case 'medium':
                return 'text-warning-400 bg-warning-400/20';
            case 'low':
                return 'text-success-400 bg-success-400/20';
            default:
                return 'text-gray-400 bg-gray-400/20';
        }
    };

    const getUrgencyScore = (score) => {
        if (score >= 80) return 'text-danger-400';
        if (score >= 60) return 'text-warning-400';
        if (score >= 40) return 'text-primary-400';
        return 'text-success-400';
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="lg" text="Loading recommendations..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <AlertTriangle className="w-16 h-16 text-danger-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">Error Loading Recommendations</h3>
                <p className="text-gray-500 mb-4">{error}</p>
                <button onClick={handleRefresh} className="btn-primary">
                    Try Again
                </button>
            </div>
        );
    }

    if (!recommendations) {
        return (
            <div className="text-center py-12">
                <Target className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">No Recommendations</h3>
                <p className="text-gray-500">No rebalancing recommendations available for this portfolio.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100">Rebalancing Recommendations</h2>
                <button
                    onClick={handleRefresh}
                    disabled={refreshing}
                    className="btn-outline flex items-center space-x-2"
                >
                    <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
                    <span>Refresh</span>
                </button>
            </div>

            {/* Recommendation Summary */}
            <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                    <Target className="w-5 h-5 mr-2 text-primary-400" />
                    Recommendation Summary
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                    <div className="text-center">
                        <p className="text-sm text-gray-400">Priority</p>
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getPriorityColor(recommendations.priority)}`}>
                            {recommendations.priority?.toUpperCase()}
                        </span>
                    </div>

                    <div className="text-center">
                        <p className="text-sm text-gray-400">Current Drift</p>
                        <p className="text-lg font-semibold text-gray-100">
                            {formatPercentage(parseFloat(recommendations.current_drift))}
                        </p>
                    </div>

                    <div className="text-center">
                        <p className="text-sm text-gray-400">Urgency Score</p>
                        <p className={`text-lg font-semibold ${getUrgencyScore(parseFloat(recommendations.urgency_score || 0))}`}>
                            {recommendations.urgency_score ? parseFloat(recommendations.urgency_score).toFixed(0) : 'N/A'}
                        </p>
                    </div>

                    <div className="text-center">
                        <p className="text-sm text-gray-400">Recommendation Date</p>
                        <p className="text-lg font-semibold text-gray-100">
                            {new Date(recommendations.recommendation_date).toLocaleDateString()}
                        </p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div>
                        <p className="text-sm text-gray-400 mb-2">Trigger Reason</p>
                        <p className="text-gray-100">{recommendations.trigger_reason}</p>
                    </div>

                    <div>
                        <p className="text-sm text-gray-400 mb-2">Recommended Timing</p>
                        <div className="flex items-center space-x-2">
                            <Clock size={16} className="text-primary-400" />
                            <span className="text-gray-100">{recommendations.recommended_timing}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Rebalancing Actions */}
            {recommendations.rebalancing_actions && recommendations.rebalancing_actions.length > 0 && (
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <ArrowRight className="w-5 h-5 mr-2 text-primary-400" />
                        Recommended Actions
                    </h3>

                    <div className="space-y-4">
                        {recommendations.rebalancing_actions.map((action, index) => (
                            <div key={index} className="flex items-center justify-between p-4 bg-dark-800 rounded-lg">
                                <div className="flex items-center space-x-4">
                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${action.action_type === 'buy'
                                        ? 'bg-success-600/20'
                                        : action.action_type === 'sell'
                                            ? 'bg-danger-600/20'
                                            : 'bg-primary-600/20'
                                        }`}>
                                        {action.action_type === 'buy' ? (
                                            <TrendingUp size={20} className="text-success-400" />
                                        ) : action.action_type === 'sell' ? (
                                            <TrendingDown size={20} className="text-danger-400" />
                                        ) : (
                                            <Target size={20} className="text-primary-400" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-100">
                                            {action.action_type?.toUpperCase()} {action.symbol}
                                        </p>
                                        <p className="text-sm text-gray-400">
                                            Quantity: {action.quantity} | Price: {formatCurrency(action.price)}
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className={`font-medium ${action.action_type === 'buy'
                                        ? 'text-success-400'
                                        : action.action_type === 'sell'
                                            ? 'text-danger-400'
                                            : 'text-gray-100'
                                        }`}>
                                        {action.action_type === 'buy' ? '+' : action.action_type === 'sell' ? '-' : ''}
                                        {formatCurrency(action.total_value)}
                                    </p>
                                    <p className="text-sm text-gray-400">
                                        {action.reason || 'Rebalancing'}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Expected Allocations */}
            {recommendations.expected_allocations && recommendations.expected_allocations.length > 0 && (
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <Target className="w-5 h-5 mr-2 text-primary-400" />
                        Expected Post-Rebalancing Allocations
                    </h3>

                    <div className="space-y-3">
                        {recommendations.expected_allocations.map((allocation, index) => (
                            <div key={index} className="flex items-center justify-between p-3 bg-dark-800 rounded-lg">
                                <div className="flex items-center space-x-3">
                                    <div className="w-8 h-8 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                        <Target size={16} className="text-primary-400" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-100">{allocation.symbol}</p>
                                        <p className="text-sm text-gray-400">{allocation.name}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="font-medium text-gray-100">
                                        {formatPercentage(parseFloat(allocation.target_percentage))}
                                    </p>
                                    <p className="text-sm text-gray-400">
                                        {formatCurrency(parseFloat(allocation.expected_value))}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Cost and Impact Analysis */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <DollarSign className="w-5 h-5 mr-2 text-primary-400" />
                        Cost Analysis
                    </h3>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Estimated Transaction Costs</span>
                            <span className="text-sm font-medium text-gray-100">
                                {recommendations.estimated_cost ? formatCurrency(parseFloat(recommendations.estimated_cost)) : 'N/A'}
                            </span>
                        </div>

                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Tax Impact</span>
                            <span className="text-sm font-medium text-gray-100">
                                {recommendations.tax_impact ? formatCurrency(parseFloat(recommendations.tax_impact)) : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <TrendingUp className="w-5 h-5 mr-2 text-primary-400" />
                        Expected Impact
                    </h3>

                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Risk Reduction</span>
                            <span className="text-sm font-medium text-gray-100">
                                {recommendations.expected_risk_reduction ? formatPercentage(parseFloat(recommendations.expected_risk_reduction)) : 'N/A'}
                            </span>
                        </div>

                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Return Impact</span>
                            <span className="text-sm font-medium text-gray-100">
                                {recommendations.expected_return_impact ? formatPercentage(parseFloat(recommendations.expected_return_impact)) : 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-center space-x-4">
                <button className="btn-outline">
                    <Clock size={16} className="mr-2" />
                    Schedule Rebalancing
                </button>
                <button className="btn-primary">
                    <CheckCircle size={16} className="mr-2" />
                    Execute Now
                </button>
            </div>
        </div>
    );
};

export default RebalancingRecommendations;
