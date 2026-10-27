import { useMoney } from "../../hooks/useMoney";
import {
    AlertTriangle,
    ArrowRight,
    Clock,
    RefreshCw,
    Target,
    TrendingDown,
    TrendingUp
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import { formatPercentage, formatQuantity } from '../../utils/formatters.jsx';
import LoadingSpinner from '../../components/shared/LoadingSpinner';

// "allocation_drift_exceeds_threshold_11.2%" -> "Allocation drift exceeds threshold 11.2%"
const humanize = (code) => {
    if (!code) return "";
    const text = String(code).replace(/_/g, " ");
    return text.charAt(0).toUpperCase() + text.slice(1);
};

const RebalancingRecommendations = ({ portfolioId }) => {
  const money = useMoney();
    const [recommendations, setRecommendations] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        if (portfolioId) {
            loadRecommendations();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when portfolioId changes
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
                <LoadingSpinner type="donut" size="lg" text="Loading recommendations..." />
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
                        <p className="text-gray-100">{humanize(recommendations.trigger_reason)}</p>
                    </div>

                    <div>
                        <p className="text-sm text-gray-400 mb-2">Recommended Timing</p>
                        <div className="flex items-center space-x-2">
                            <Clock size={16} className="text-primary-400" />
                            <span className="text-gray-100">{humanize(recommendations.recommended_timing)}</span>
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
                                            {action.action_type?.toUpperCase()} {formatQuantity(action.quantity_change)} {action.asset_symbol}
                                            <span className="text-gray-400 font-normal"> · ≈ {money(action.trade_value)}</span>
                                        </p>
                                        <p className="text-sm text-gray-400">
                                            {action.action_type === 'buy' ? 'Underweight vs. target' : 'Overweight vs. target'}
                                            {' · '}
                                            {formatQuantity(action.current_quantity)} → {formatQuantity(action.target_quantity)} shares at {money(action.price)}
                                        </p>
                                    </div>
                                </div>
                                <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${getPriorityColor(action.priority)}`}>
                                    {action.priority?.toUpperCase()}
                                </span>
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
                        Current → Target Allocation
                    </h3>

                    <div className="space-y-3">
                        {recommendations.expected_allocations.map((allocation, index) => (
                            <div key={index} className="flex items-center justify-between p-3 bg-dark-800 rounded-lg">
                                <div className="flex items-center space-x-3">
                                    <div className="w-8 h-8 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                        <Target size={16} className="text-primary-400" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-100">{allocation.asset_symbol}</p>
                                        <p className="text-sm text-gray-400">{allocation.asset_name}</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="font-medium text-gray-100">
                                        {formatPercentage(parseFloat(allocation.current_percentage), { showSign: false })}
                                        <span className="text-gray-500"> → </span>
                                        {formatPercentage(parseFloat(allocation.target_percentage), { showSign: false })}
                                    </p>
                                    <p className="text-sm text-gray-400">
                                        {money(parseFloat(allocation.current_value))}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

        </div>
    );
};

export default RebalancingRecommendations;
