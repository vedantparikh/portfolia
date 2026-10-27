import {
    BarChart3,
    Plus,
    Target
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { analyticsAPI } from '../../services/api';
import LoadingSpinner from '../../components/shared/LoadingSpinner';

const BenchmarkComparison = ({ portfolioId }) => {
    const [benchmarks, setBenchmarks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);

    useEffect(() => {
        if (portfolioId) {
            loadBenchmarkData();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps -- reload only when portfolioId changes
    }, [portfolioId]);

    const loadBenchmarkData = async () => {
        try {
            setLoading(true);
            setError(null);

            const benchmarksResponse = await analyticsAPI.getPortfolioBenchmarks(portfolioId);
            setBenchmarks(benchmarksResponse);
        } catch (err) {
            console.error('Failed to load benchmark data:', err);
            setError('Failed to load benchmark data');
        } finally {
            setLoading(false);
        }
    };

    const handleAddBenchmark = async (benchmarkData) => {
        try {
            await analyticsAPI.addPortfolioBenchmark(portfolioId, benchmarkData);
            await loadBenchmarkData();
            setShowAddModal(false);
        } catch (err) {
            console.error('Failed to add benchmark:', err);
            setError('Failed to add benchmark');
        }
    };


    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <LoadingSpinner type="analyst" size="lg" text="Loading benchmarks..." />
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-center py-12">
                <BarChart3 className="w-16 h-16 text-danger-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">Error Loading Benchmarks</h3>
                <p className="text-gray-500 mb-4">{error}</p>
                <button onClick={loadBenchmarkData} className="btn-primary">
                    Try Again
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-100">Benchmark Comparison</h2>
                <button
                    onClick={() => setShowAddModal(true)}
                    className="btn-primary flex items-center space-x-2"
                >
                    <Plus size={16} />
                    <span>Add Benchmark</span>
                </button>
            </div>

            {/* Benchmarks List */}
            <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Available Benchmarks</h3>

                {benchmarks.length === 0 ? (
                    <div className="text-center py-8">
                        <Target className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <h4 className="text-lg font-semibold text-gray-300 mb-2">No Benchmarks Set</h4>
                        <p className="text-gray-500 mb-4">Add benchmarks to compare your portfolio performance</p>
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="btn-primary"
                        >
                            Add First Benchmark
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {benchmarks.map((benchmark) => (
                            <div
                                key={benchmark.id}
                                className="flex items-center justify-between p-4 rounded-lg bg-dark-800"
                            >
                                <div className="flex items-center space-x-4">
                                    <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                        <Target size={20} className="text-primary-400" />
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-100">{benchmark.benchmark_name}</p>
                                        <p className="text-sm text-gray-400 capitalize">
                                            {benchmark.benchmark_type}
                                            {benchmark.is_primary && <span className="text-primary-400"> · Primary</span>}
                                        </p>
                                    </div>
                                </div>
                                {benchmark.beta != null && (
                                    <div className="text-right">
                                        <p className="text-sm text-gray-400">Beta</p>
                                        <p className="font-medium text-gray-100">
                                            {parseFloat(benchmark.beta).toFixed(2)}
                                        </p>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {benchmarks.length > 0 && (
                <div className="card p-6 flex items-start gap-4">
                    <BarChart3 className="w-5 h-5 mt-0.5 text-gray-500 shrink-0" />
                    <div>
                        <p className="font-medium text-gray-200">Benchmark comparison is coming</p>
                        <p className="text-sm text-gray-400 mt-1">
                            Side-by-side returns, beta and alpha against your benchmarks need a
                            backend calculation that isn&apos;t reliable yet, so they are not shown.
                            Return and risk metrics for the portfolio itself are on the
                            Performance Metrics and Analytics views.
                        </p>
                    </div>
                </div>
            )}

            {/* Add Benchmark Modal */}
            {showAddModal && (
                <AddBenchmarkModal
                    portfolioId={portfolioId}
                    onSave={handleAddBenchmark}
                    onClose={() => setShowAddModal(false)}
                />
            )}
        </div>
    );
};

// Add Benchmark Modal Component
const AddBenchmarkModal = ({ portfolioId, onSave, onClose }) => {
    const [formData, setFormData] = useState({
        benchmark_asset_id: '',
        benchmark_name: '',
        benchmark_type: 'index',
        tracking_error: '',
        information_ratio: '',
        beta: '',
        alpha: '',
        excess_return: '',
        excess_return_percent: '',
        is_active: true,
        is_primary: false
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        const data = {
            ...formData,
            portfolio_id: parseInt(portfolioId),
            tracking_error: formData.tracking_error ? parseFloat(formData.tracking_error) : null,
            information_ratio: formData.information_ratio ? parseFloat(formData.information_ratio) : null,
            beta: formData.beta ? parseFloat(formData.beta) : null,
            alpha: formData.alpha ? parseFloat(formData.alpha) : null,
            excess_return: formData.excess_return ? parseFloat(formData.excess_return) : null,
            excess_return_percent: formData.excess_return_percent ? parseFloat(formData.excess_return_percent) : null,
        };

        onSave(data);
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-dark-900 rounded-lg p-6 w-full max-w-md">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">Add Benchmark</h3>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Benchmark Asset ID
                        </label>
                        <input
                            type="number"
                            value={formData.benchmark_asset_id}
                            onChange={(e) => setFormData({ ...formData, benchmark_asset_id: e.target.value })}
                            className="input-field"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Benchmark Name
                        </label>
                        <input
                            type="text"
                            value={formData.benchmark_name}
                            onChange={(e) => setFormData({ ...formData, benchmark_name: e.target.value })}
                            className="input-field"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Benchmark Type
                        </label>
                        <select
                            value={formData.benchmark_type}
                            onChange={(e) => setFormData({ ...formData, benchmark_type: e.target.value })}
                            className="input-field"
                        >
                            <option value="index">Index</option>
                            <option value="custom">Custom</option>
                            <option value="peer_group">Peer Group</option>
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Beta
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                value={formData.beta}
                                onChange={(e) => setFormData({ ...formData, beta: e.target.value })}
                                className="input-field"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Alpha
                            </label>
                            <input
                                type="number"
                                step="0.01"
                                value={formData.alpha}
                                onChange={(e) => setFormData({ ...formData, alpha: e.target.value })}
                                className="input-field"
                            />
                        </div>
                    </div>

                    <div className="flex items-center space-x-4">
                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                id="is_primary"
                                checked={formData.is_primary}
                                onChange={(e) => setFormData({ ...formData, is_primary: e.target.checked })}
                                className="mr-2"
                            />
                            <label htmlFor="is_primary" className="text-sm text-gray-300">
                                Primary Benchmark
                            </label>
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
                            Add Benchmark
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default BenchmarkComparison;
