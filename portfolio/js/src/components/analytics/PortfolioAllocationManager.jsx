import {
    AlertTriangle,
    CheckCircle,
    Edit3,
    Plus,
    RefreshCw,
    Target,
    Trash2
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import { formatCurrency, formatPercentage } from '../../utils/formatters.jsx';
import LoadingSpinner from '../shared/LoadingSpinner';

const PortfolioAllocationManager = ({ portfolioId }) => {
    const [allocations, setAllocations] = useState([]);
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);
    const [editingAllocation, setEditingAllocation] = useState(null);

    useEffect(() => {
        if (portfolioId) {
            loadAllocationData();
        }
    }, [portfolioId]);

    const loadAllocationData = async () => {
        try {
            setLoading(true);
            setError(null);

            const [allocationsResponse, analysisResponse] = await Promise.allSettled([
                analyticsAPI.getPortfolioAllocations(portfolioId),
                analyticsAPI.analyzePortfolioAllocation(portfolioId)
            ]);

            setAllocations(allocationsResponse.status === 'fulfilled' ? allocationsResponse.value : []);
            setAnalysis(analysisResponse.status === 'fulfilled' ? analysisResponse.value : null);
        } catch (err) {
            console.error('Failed to load allocation data:', err);
            setError('Failed to load allocation data');
        } finally {
            setLoading(false);
        }
    };

    const handleAddAllocation = async (allocationData) => {
        try {
            await analyticsAPI.setPortfolioAllocations(portfolioId, [allocationData]);
            await loadAllocationData();
            setShowAddModal(false);
        } catch (err) {
            console.error('Failed to add allocation:', err);
            setError('Failed to add allocation');
        }
    };

    const handleUpdateAllocation = async (allocationId, allocationData) => {
        try {
            await analyticsAPI.updatePortfolioAllocation(portfolioId, allocationId, allocationData);
            await loadAllocationData();
            setEditingAllocation(null);
        } catch (err) {
            console.error('Failed to update allocation:', err);
            setError('Failed to update allocation');
        }
    };

    const handleDeleteAllocation = async (allocationId) => {
        if (window.confirm('Are you sure you want to delete this allocation?')) {
            try {
                await analyticsAPI.deletePortfolioAllocation(portfolioId, allocationId);
                await loadAllocationData();
            } catch (err) {
                console.error('Failed to delete allocation:', err);
                setError('Failed to delete allocation');
            }
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="lg" text="Loading allocations..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <AlertTriangle className="w-16 h-16 text-danger-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">Error Loading Allocations</h3>
                <p className="text-gray-500 mb-4">{error}</p>
                <button onClick={loadAllocationData} className="btn-primary">
                    Try Again
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100">Portfolio Allocations</h2>
                <div className="flex items-center space-x-3">
                    <button
                        onClick={loadAllocationData}
                        className="btn-outline flex items-center space-x-2"
                    >
                        <RefreshCw size={16} />
                        <span>Refresh</span>
                    </button>
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="btn-primary flex items-center space-x-2"
                    >
                        <Plus size={16} />
                        <span>Add Allocation</span>
                    </button>
                </div>
            </div>

            {/* Allocation Analysis */}
            {analysis && (
                <div className="card p-6">
                    <h3 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                        <Target className="w-5 h-5 mr-2 text-primary-400" />
                        Allocation Analysis
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Total Drift</p>
                            <p className={`text-2xl font-bold ${parseFloat(analysis.total_drift_percentage) > 5
                                ? 'text-danger-400'
                                : parseFloat(analysis.total_drift_percentage) > 2
                                    ? 'text-warning-400'
                                    : 'text-success-400'
                                }`}>
                                {formatPercentage(parseFloat(analysis.total_drift_percentage))}
                            </p>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Rebalancing Needed</p>
                            <div className="flex items-center justify-center">
                                {analysis.rebalancing_needed ? (
                                    <CheckCircle className="w-8 h-8 text-danger-400" />
                                ) : (
                                    <CheckCircle className="w-8 h-8 text-success-400" />
                                )}
                            </div>
                        </div>
                        <div className="text-center">
                            <p className="text-sm text-gray-400">Analysis Date</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {new Date(analysis.analysis_date).toLocaleDateString()}
                            </p>
                        </div>
                    </div>

                    {/* Drift Analysis */}
                    {analysis.allocation_drift && analysis.allocation_drift.length > 0 && (
                        <div className="space-y-4">
                            <h4 className="text-md font-semibold text-gray-100">Allocation Drift</h4>
                            <div className="space-y-3">
                                {analysis.allocation_drift.map((drift, index) => (
                                    <div key={index} className="flex items-center justify-between p-4 bg-dark-800 rounded-lg">
                                        <div className="flex items-center space-x-4">
                                            <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                                <Target size={20} className="text-primary-400" />
                                            </div>
                                            <div>
                                                <p className="font-medium text-gray-100">{drift.asset_symbol}</p>
                                                <p className="text-sm text-gray-400">
                                                    Current: {formatPercentage(parseFloat(drift.current_percentage))} |
                                                    Target: {formatPercentage(parseFloat(drift.target_percentage))}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className={`font-medium ${parseFloat(drift.drift_percentage) > 0
                                                ? 'text-danger-400'
                                                : 'text-success-400'
                                                }`}>
                                                {parseFloat(drift.drift_percentage) > 0 ? '+' : ''}
                                                {formatPercentage(parseFloat(drift.drift_percentage))}
                                            </p>
                                            <p className="text-sm text-gray-400">
                                                {formatCurrency(parseFloat(drift.drift_amount))}
                                            </p>
                                        </div>
                                        <div className="flex items-center">
                                            {drift.requires_rebalancing ? (
                                                <AlertTriangle className="w-5 h-5 text-danger-400" />
                                            ) : (
                                                <CheckCircle className="w-5 h-5 text-success-400" />
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Current Allocations */}
            <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Current Allocations</h3>

                {allocations.length === 0 ? (
                    <div className="text-center py-8">
                        <Target className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <h4 className="text-lg font-semibold text-gray-300 mb-2">No Allocations Set</h4>
                        <p className="text-gray-500 mb-4">Set target allocations for your portfolio assets</p>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="btn-primary"
                        >
                            Add First Allocation
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {allocations.map((allocation) => (
                            <div key={allocation.id} className="flex items-center justify-between p-4 bg-dark-800 rounded-lg">
                                <div className="flex items-center space-x-4">
                                    <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                        <Target size={20} className="text-primary-400" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-100">Asset ID: {allocation.asset_id}</p>
                                        <p className="text-sm text-gray-400">
                                            Target: {formatPercentage(parseFloat(allocation.target_percentage))}
                                            {allocation.min_percentage && (
                                                <span> | Min: {formatPercentage(parseFloat(allocation.min_percentage))}</span>
                                            )}
                                            {allocation.max_percentage && (
                                                <span> | Max: {formatPercentage(parseFloat(allocation.max_percentage))}</span>
                                            )}
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="text-sm text-gray-400">Threshold</p>
                                    <p className="font-medium text-gray-100">
                                        {allocation.rebalance_threshold ? formatPercentage(parseFloat(allocation.rebalance_threshold)) : 'N/A'}
                                    </p>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => setEditingAllocation(allocation)}
                                        className="p-2 text-gray-400 hover:text-primary-400 transition-colors"
                                    >
                                        <Edit3 size={16} />
                                    </button>
                                    <button
                                        onClick={() => handleDeleteAllocation(allocation.id)}
                                        className="p-2 text-gray-400 hover:text-danger-400 transition-colors"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Add/Edit Allocation Modal */}
            {(showAddModal || editingAllocation) && (
                <AllocationModal
                    allocation={editingAllocation}
                    onSave={editingAllocation ? handleUpdateAllocation : handleAddAllocation}
                    onClose={() => {
                        setShowAddModal(false);
                        setEditingAllocation(null);
                    }}
                />
            )}
        </div>
    );
};

// Allocation Modal Component
const AllocationModal = ({ allocation, onSave, onClose }) => {
    const [formData, setFormData] = useState({
        asset_id: allocation?.asset_id || '',
        target_percentage: allocation?.target_percentage || '',
        min_percentage: allocation?.min_percentage || '',
        max_percentage: allocation?.max_percentage || '',
        rebalance_threshold: allocation?.rebalance_threshold || '',
        rebalance_frequency: allocation?.rebalance_frequency || 'quarterly',
        is_active: allocation?.is_active ?? true
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        const data = {
            ...formData,
            portfolio_id: parseInt(portfolioId),
            target_percentage: parseFloat(formData.target_percentage),
            min_percentage: formData.min_percentage ? parseFloat(formData.min_percentage) : null,
            max_percentage: formData.max_percentage ? parseFloat(formData.max_percentage) : null,
            rebalance_threshold: formData.rebalance_threshold ? parseFloat(formData.rebalance_threshold) : null,
        };

        if (allocation) {
            onSave(allocation.id, data);
        } else {
            onSave(data);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-dark-900 rounded-lg p-6 w-full max-w-md">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    {allocation ? 'Edit Allocation' : 'Add Allocation'}
                </h3>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Asset ID
                        </label>
                        <input
                            type="number"
                            value={formData.asset_id}
                            onChange={(e) => setFormData({ ...formData, asset_id: e.target.value })}
                            className="input-field"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Target Percentage
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={formData.target_percentage}
                            onChange={(e) => setFormData({ ...formData, target_percentage: e.target.value })}
                            className="input-field"
                            required
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Min Percentage
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                max="100"
                                value={formData.min_percentage}
                                onChange={(e) => setFormData({ ...formData, min_percentage: e.target.value })}
                                className="input-field"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Max Percentage
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                min="0"
                                max="100"
                                value={formData.max_percentage}
                                onChange={(e) => setFormData({ ...formData, max_percentage: e.target.value })}
                                className="input-field"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Rebalance Threshold
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="100"
                            value={formData.rebalance_threshold}
                            onChange={(e) => setFormData({ ...formData, rebalance_threshold: e.target.value })}
                            className="input-field"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Rebalance Frequency
                        </label>
                        <select
                            value={formData.rebalance_frequency}
                            onChange={(e) => setFormData({ ...formData, rebalance_frequency: e.target.value })}
                            className="input-field"
                        >
                            <option value="monthly">Monthly</option>
                            <option value="quarterly">Quarterly</option>
                            <option value="semi-annually">Semi-Annually</option>
                            <option value="annually">Annually</option>
                        </select>
                    </div>

                    <div className="flex items-center">
                        <input
                            type="checkbox"
                            id="is_active"
                            checked={formData.is_active}
                            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                            className="mr-2"
                        />
                        <label htmlFor="is_active" className="text-sm text-gray-300">
                            Active
                        </label>
                    </div>

                    <div className="flex justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="btn-outline"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="btn-primary"
                        >
                            {allocation ? 'Update' : 'Add'} Allocation
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default PortfolioAllocationManager;
