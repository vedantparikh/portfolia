import { BarChart3, Plus, Target } from 'lucide-react';
import { useMemo, useState } from 'react';
import toast from 'react-hot-toast';

import { apiErrorMessage } from '../../shared/api/client';
import { ErrorState, Modal } from '../../shared/ui';
import LoadingSpinner from '../../shared/ui/Spinner';
import { useAssets } from '../assets/queries';
import BenchmarkCard from '../portfolio/BenchmarkCard';
import { useBenchmarkComparison, useBenchmarkOptions } from '../portfolio/queries';
import { analyticsAPI } from './api';
import { invalidateAnalytics, usePortfolioBenchmarks } from './queries';

const PERIODS = [
    ['3M', '3m'],
    ['6M', '6m'],
    ['YTD', 'ytd'],
    ['1Y', '1y'],
    ['3Y', '3y'],
    ['All', 'inception'],
];

// Saved benchmarks first (the primary one leads), then the suggested total-return series
const benchmarkChoices = (saved, suggested) => {
    const choices = [];
    const seen = new Set();
    const add = (symbol, name) => {
        if (!symbol || seen.has(symbol)) return;
        seen.add(symbol);
        choices.push({ symbol, name });
    };
    [...saved]
        .sort((a, b) => Number(b.is_primary) - Number(a.is_primary))
        .forEach((b) => add(b.symbol, b.benchmark_name));
    suggested.forEach((o) => add(o.symbol, o.name));
    return choices;
};

const BenchmarkComparison = ({ portfolioId, currency }) => {
    const query = usePortfolioBenchmarks(portfolioId);
    const saved = useMemo(() => query.data || [], [query.data]);
    const { data: suggested = [] } = useBenchmarkOptions(currency);
    const choices = useMemo(() => benchmarkChoices(saved, suggested), [saved, suggested]);
    const [picked, setPicked] = useState('');
    const [period, setPeriod] = useState('1y');
    const [showAddModal, setShowAddModal] = useState(false);
    const symbol = picked || choices[0]?.symbol || '';
    const comparison = useBenchmarkComparison(portfolioId, period, symbol);

    const handleAddBenchmark = async (benchmarkData) => {
        try {
            await analyticsAPI.addPortfolioBenchmark(portfolioId, benchmarkData);
            await invalidateAnalytics(portfolioId);
            setShowAddModal(false);
        } catch (error) {
            toast.error(apiErrorMessage(error, 'Failed to add benchmark'));
        }
    };

    if (query.isPending) {
        return (
            <div className="flex items-center justify-center py-12">
                <LoadingSpinner type="analyst" size="lg" text="Loading benchmarks..." />
            </div>
        );
    }

    if (query.isError) {
        return (
            <ErrorState icon={BarChart3} title="Error Loading Benchmarks" message="Failed to load benchmark data" onRetry={() => query.refetch()} />
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-2xl font-bold text-gray-100">Benchmark Comparison</h2>
                <button onClick={() => setShowAddModal(true)} className="btn-primary flex items-center space-x-2">
                    <Plus size={16} />
                    <span>Add Benchmark</span>
                </button>
            </div>

            <div className="flex flex-wrap items-center gap-3">
                <label htmlFor="benchmark-pick" className="text-sm text-gray-400">Compare with</label>
                <select
                    id="benchmark-pick"
                    value={symbol}
                    onChange={(e) => setPicked(e.target.value)}
                    className="input-field w-auto"
                >
                    {choices.map((choice) => (
                        <option key={choice.symbol} value={choice.symbol}>
                            {choice.name} ({choice.symbol})
                        </option>
                    ))}
                </select>
                <div className="flex flex-wrap gap-1">
                    {PERIODS.map(([label, code]) => (
                        <button
                            key={code}
                            onClick={() => setPeriod(code)}
                            className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                                period === code ? 'bg-primary-600 text-white' : 'text-gray-400 hover:bg-dark-700'
                            }`}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            {!symbol ? null : comparison.isPending ? (
                <LoadingSpinner centered text="Comparing..." />
            ) : comparison.isError ? (
                <BenchmarkCard comparison={{ benchmark: { symbol }, error: apiErrorMessage(comparison.error, 'Benchmark could not be loaded.') }} />
            ) : (
                <BenchmarkCard comparison={comparison.data} />
            )}

            <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-1">Saved benchmarks</h3>
                <p className="text-xs text-gray-500 mb-4">
                    The primary one is the default here, on the chart&apos;s &quot;Compare with&quot; and for beta.
                </p>
                {saved.length === 0 ? (
                    <p className="text-sm text-gray-400">
                        None saved; the suggested series for {currency || 'the portfolio currency'} are used.
                    </p>
                ) : (
                    <div className="space-y-3">
                        {saved.map((benchmark) => (
                            <div key={benchmark.id} className="flex items-center gap-4 p-4 rounded-lg bg-dark-800">
                                <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                    <Target size={20} className="text-primary-400" />
                                </div>
                                <div>
                                    <p className="font-medium text-gray-100">{benchmark.benchmark_name}</p>
                                    <p className="text-sm text-gray-400">
                                        {benchmark.symbol}
                                        {benchmark.is_primary && <span className="text-primary-400"> · Primary</span>}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {showAddModal && (
                <AddBenchmarkModal portfolioId={portfolioId} onSave={handleAddBenchmark} onClose={() => setShowAddModal(false)} />
            )}
        </div>
    );
};

// A benchmark is one of your assets; pick a total-return series (accumulating ETF or TR index)
const AddBenchmarkModal = ({ portfolioId, onSave, onClose }) => {
    const { data: assets = [] } = useAssets();
    const [assetId, setAssetId] = useState('');
    const [name, setName] = useState('');
    const [isPrimary, setIsPrimary] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        const asset = assets.find((a) => String(a.id) === assetId);
        onSave({
            portfolio_id: Number(portfolioId),
            benchmark_asset_id: Number(assetId),
            benchmark_name: name.trim() || asset?.name || asset?.symbol,
            benchmark_type: 'index',
            is_active: true,
            is_primary: isPrimary,
        });
    };

    return (
        <Modal onClose={onClose}>
            <div className="bg-dark-900 rounded-lg p-6 w-full max-w-md">
                <h3 className="text-lg font-semibold text-gray-100 mb-1">Add Benchmark</h3>
                <p className="text-xs text-gray-500 mb-4">
                    Pick one of your assets. Use a total-return series (an accumulating ETF or a TR index); add it under Assets first if it is missing.
                </p>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <label htmlFor="benchmark-asset" className="flex flex-col gap-1 text-sm text-gray-300">
                        Asset
                        <select id="benchmark-asset" value={assetId} onChange={(e) => setAssetId(e.target.value)} className="input-field" required>
                            <option value="">Choose…</option>
                            {assets.map((asset) => (
                                <option key={asset.id} value={asset.id}>
                                    {asset.symbol} — {asset.name}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label htmlFor="benchmark-name" className="flex flex-col gap-1 text-sm text-gray-300">
                        Name (optional)
                        <input id="benchmark-name" value={name} onChange={(e) => setName(e.target.value)} className="input-field" maxLength={255} />
                    </label>
                    <label className="flex items-center gap-2 text-sm text-gray-300">
                        <input type="checkbox" checked={isPrimary} onChange={(e) => setIsPrimary(e.target.checked)} />
                        Primary benchmark
                    </label>
                    <div className="flex justify-end space-x-3 pt-2">
                        <button type="button" onClick={onClose} className="btn-outline">Cancel</button>
                        <button type="submit" className="btn-primary">Add Benchmark</button>
                    </div>
                </form>
            </div>
        </Modal>
    );
};

export default BenchmarkComparison;
