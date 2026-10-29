import {
    AlertTriangle,
    ArrowLeft,
    Award,
    BarChart3,
    ChevronsUp,
    Filter,
    Gem,
    Landmark,
    PieChart,
    Plus,
    RefreshCw,
    Search,
    Settings,
    Shield,
    TrendingUp,
    Menu,
    X,
    Zap
} from 'lucide-react';
import { useMemo, useState } from 'react';
import useIsMobile from '../../hooks/useIsMobile';
import toast from 'react-hot-toast';
import { InView } from 'react-intersection-observer';
import { assetAPI } from './api';
import { transactionAPI } from '../transactions/api';
import { apiErrorMessage } from '../../shared/api/client';
import { queryClient } from '../../shared/api/queryClient';
import { portfolioKeys, usePortfolios } from '../portfolio/queries';
import { transactionKeys } from '../transactions/queries';
import { invalidateAssets, useAssetPages, useAssets } from './queries';
import { formatPercentage, formatRatio, formatVolume, getChangeColor } from '../../utils/formatters';
import AssetAnalyticsView from '../analytics/AssetAnalyticsView';
import IndicatorConfigurationManager from '../analytics/IndicatorConfigurationManager';
import { usePageChrome, useShell } from '../../app/chrome';
import { LoadingSpinner, StatCard } from '../../components/shared';
import CreateTransactionModal from '../transactions/CreateTransactionModal';
import AssetCard from './AssetCard';
import AssetFilters from './AssetFilters';
import AssetModal from './AssetModal';
import BulkAssetModal from './BulkAssetModal';
import { Modal } from '../../shared/ui';

const CATEGORY_TYPES = {
    cryptocurrency: 'CRYPTOCURRENCY',
    stock: 'EQUITY',
    commodity: 'COMMODITY',
    forex: 'CASH',
    etf: 'ETF',
    bond: 'BOND',
    real_estate: 'REAL_ESTATE',
    mutual_fund: 'MUTUALFUND',
    index_fund: 'INDEX',
};

const assetPayload = (asset, overrides = {}) => ({
    symbol: asset.symbol,
    name: asset.name,
    asset_type: asset.asset_type,
    exchange: asset.exchange,
    sector: asset.sector,
    industry: asset.industry,
    country: asset.country,
    description: asset.description,
    is_active: asset.is_active,
    ...overrides,
});

const Assets = () => {
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    const isMobile = useIsMobile();
    const { openSidebar } = useShell();
    const [viewMode, setViewMode] = useState('grid');
    const [modalMode, setModalMode] = useState('view');
    const [showAnalytics, setShowAnalytics] = useState(false);
    const [selectedConfiguration, setSelectedConfiguration] = useState(null);
    const [showConfigurationManager, setShowConfigurationManager] = useState(false);
    const [showTransactionModal, setShowTransactionModal] = useState(false);
    const [transactionAsset, setTransactionAsset] = useState(null);
    const [showBulkAssetModal, setShowBulkAssetModal] = useState(false);

    const [filters, setFilters] = useState({
        category: 'all',
        priceRange: 'all',
        valueRange: 'all',
        changeRange: 'all',
        marketCapRange: 'all',
        sortBy: 'symbol',
        sortOrder: 'asc'
    });
    const [autoRefresh, setAutoRefresh] = useState(false);

    const apiParams = useMemo(() => {
        const params = {
            include_detail: true,
            include_performance: true,
            include_analytics: true,
            sort_by: filters.sortBy,
            sort_order: filters.sortOrder,
        };
        if (searchQuery) params.symbol = searchQuery;
        if (filters.category !== 'all') params.asset_type = CATEGORY_TYPES[filters.category];
        if (filters.priceRange !== 'all') params.price_range = filters.priceRange;
        if (filters.valueRange !== 'all') params.value_range = filters.valueRange;
        if (filters.changeRange !== 'all') params.change_range = filters.changeRange;
        if (filters.marketCapRange !== 'all') params.market_cap_range = filters.marketCapRange;
        return params;
    }, [filters, searchQuery]);

    const { data: portfolios = [] } = usePortfolios();
    const pages = useAssetPages(apiParams, { refetchInterval: autoRefresh ? 30000 : false });
    const assets = useMemo(
        () => Array.from(new Map((pages.data?.pages.flatMap((page) => page.items) || []).map((asset) => [asset.id, asset])).values()),
        [pages.data],
    );
    const total = pages.data?.pages[0]?.total;
    const loading = pages.isPending;
    const loadingMore = pages.isFetchingNextPage;
    const hasMore = pages.hasNextPage;

    useAssets();

    const handleRefresh = (silent = false) => {
        invalidateAssets();
        if (!silent) toast.success('Assets refreshed');
    };

    const handleAssetClick = (asset) => {
        setSelectedAsset(asset);
        setModalMode('view');
        setShowModal(true);
    };

    const handleAnalyticsClick = (asset) => {
        setSelectedAsset(asset);
        setShowAnalytics(true);
    };

    const handleTransactionClick = (asset) => {
        setTransactionAsset(asset);
        setShowTransactionModal(true);
    };

    const handleCreateTransaction = async (transactionData) => {
        try {
            await transactionAPI.createTransaction(transactionData);
            setShowTransactionModal(false);
            setTransactionAsset(null);
            toast.success('Transaction created successfully');
            queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
            queryClient.invalidateQueries({ queryKey: transactionKeys.all });
            handleRefresh(true);
        } catch (error) {
            console.error('Failed to create transaction:', error);
            const errorMessage = apiErrorMessage(error, 'Failed to create transaction');
            toast.error(errorMessage);
            throw error;
        }
    };

    const handleConfigurationSelect = (configuration) => {
        setSelectedConfiguration(configuration);
        setShowConfigurationManager(false);
    };

    const handleCreateAsset = () => {
        setSelectedAsset(null);
        setModalMode('create');
        setShowModal(true);
    };

    const handleEditAsset = (asset) => {
        setSelectedAsset(asset);
        setModalMode('edit');
        setShowModal(true);
    };

    const handleDeleteAsset = async (assetId) => {
        try {
            await assetAPI.deleteAsset(assetId);
            toast.success('Asset deleted successfully');
            handleRefresh();
        } catch (error) {
            console.error('Failed to delete asset:', error);
            toast.error('Failed to delete asset');
        }
    };

    const handleAssetSave = async (assetData) => {
        try {
            if (modalMode === 'create') {
                await assetAPI.createAsset(assetPayload(assetData, { asset_type: assetData.asset_type || 'EQUITY', is_active: true }));
                toast.success('Asset added successfully');
            } else if (modalMode === 'edit') {
                await assetAPI.updateAsset(selectedAsset.id, assetPayload(assetData));
                toast.success('Asset updated successfully');
            }
            handleRefresh();
            setShowModal(false);
            setSelectedAsset(null);
        } catch (error) {
            console.error('Failed to save asset:', error);
            toast.error(`Failed to ${modalMode} asset`);
            throw error;
        }
    };

    const handleFilterChange = (newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    };

    const handleQuickAction = (action) => {
        if (action !== 'refresh') return false;
        handleRefresh();
        return true;
    };

    usePageChrome({
        searchQuery,
        onSearchChange: setSearchQuery,
        onQuickAction: handleQuickAction,
    });

    const handleAddToPortfolio = () => {
        toast.info('Use Portfolio section to manage assets in specific portfolios');
    };

    const handleViewInPortfolio = () => {
        toast.info('Use Portfolio section to view assets in specific portfolios');
    };

    const getHighlightStats = () => {
        // Define a default asset structure for consistency
        const defaultAsset = { symbol: 'N/A', name: 'Not Available', value: 0 };

        if (!assets || assets.length === 0) {
            return {
                topGainer: { ...defaultAsset, value: 0 },
                highestDividend: defaultAsset,
                bestValue: defaultAsset,
                mostTraded: defaultAsset,
                mostStable: defaultAsset,
                highestGrowth: defaultAsset,
                strongestMomentum: defaultAsset,
                topLoser: { ...defaultAsset, value: 0 }
            };
        }

        const highlights = assets.reduce((acc, asset) => {
            const detail = asset.detail;
            if (!detail) return acc;

            // --- Existing Highlights ---
            const change = parseFloat(detail.price_change_percentage_24h || 0);
            if (change > acc.topGainer.value) {
                acc.topGainer = { symbol: asset.symbol, name: asset.name, value: change };
            }

            const dividendYield = parseFloat(detail.dividend_yield || 0);
            if (dividendYield > acc.highestDividend.value) {
                acc.highestDividend = { symbol: asset.symbol, name: asset.name, value: dividendYield };
            }

            const peRatio = parseFloat(detail.trailing_PE || 0);
            if (peRatio > 0 && (peRatio < acc.bestValue.value || acc.bestValue.value === 0)) {
                acc.bestValue = { symbol: asset.symbol, name: asset.name, value: peRatio };
            }

            const volume = parseFloat(detail.volume_24h || 0);
            if (volume > acc.mostTraded.value) {
                acc.mostTraded = { symbol: asset.symbol, name: asset.name, value: volume };
            }

            // --- New Highlights ---
            // 5. Find Most Stable (Lowest positive Beta)
            const beta = parseFloat(detail.beta);
            if (beta > 0 && (beta < acc.mostStable.value || acc.mostStable.value === 0)) {
                acc.mostStable = { symbol: asset.symbol, name: asset.name, value: beta };
            }

            // 6. Find Highest Growth (Revenue Growth)
            const revenueGrowth = parseFloat(detail.revenue_growth || 0);
            if (revenueGrowth > acc.highestGrowth.value) {
                acc.highestGrowth = { symbol: asset.symbol, name: asset.name, value: revenueGrowth };
            }

            // 7. Find Strongest Momentum (Closest to 52-Week High)
            const high52w = parseFloat(detail.high_52w);
            const currentPrice = parseFloat(detail.current_price);
            if (high52w > 0 && currentPrice <= high52w) {
                const proximity = (currentPrice / high52w) * 100; // e.g., 99.5 for 99.5%
                if (proximity > acc.strongestMomentum.value) {
                    acc.strongestMomentum = { symbol: asset.symbol, name: asset.name, value: proximity };
                }
            }

            // 8. Find Top Loser (Most negative % change)
            if (change < acc.topLoser.value) {
                acc.topLoser = { symbol: asset.symbol, name: asset.name, value: change };
            }

            return acc;
        }, {
            topGainer: { ...defaultAsset, value: -Infinity },
            highestDividend: defaultAsset,
            bestValue: { ...defaultAsset, value: 0 },
            mostTraded: defaultAsset,
            mostStable: { ...defaultAsset, value: 0 },
            highestGrowth: { ...defaultAsset, value: -Infinity },
            strongestMomentum: defaultAsset,
            topLoser: { ...defaultAsset, value: Infinity }
        });

        // Clean up initial values if no asset was found
        if (highlights.topGainer.value === -Infinity) highlights.topGainer.value = 0;
        if (highlights.highestGrowth.value === -Infinity) highlights.highestGrowth.value = 0;
        if (highlights.topLoser.value === Infinity) highlights.topLoser.value = 0;

        return highlights;
    };

    // In your component, call this new function
    const stats = getHighlightStats();

    return (
        <div className="min-h-screen gradient-bg flex">
            <div className="flex-1 min-w-0 overflow-y-auto">
              {isMobile && (
                <div className="bg-dark-900 border-b border-dark-700 p-4 flex items-center justify-between">
                  <button
                    onClick={openSidebar}
                    aria-label="Open menu"
                    className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
                  >
                    <Menu size={20} className="text-gray-400" />
                  </button>
                  <h1 className="text-lg font-semibold text-gray-100">Assets</h1>
                  <div className="w-10" />
                </div>
              )}
                <div className="max-w-7xl mx-auto p-4 sm:p-6">
                    <div className="mb-8">
                        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                            <a href="/dashboard" aria-label="Back to Dashboard" className="flex items-center space-x-2 text-gray-400 hover:text-gray-300">
                                <ArrowLeft size={20} /><span className="hidden sm:inline">Back to Dashboard</span>
                            </a>
                            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                                <button onClick={handleCreateAsset} className="btn-primary flex items-center space-x-2 whitespace-nowrap">
                                    <Plus size={16} /><span>Add Asset</span>
                                </button>
                                <button onClick={() => setShowBulkAssetModal(true)} aria-label="Bulk Entry" title="Bulk Entry" className="btn-secondary flex items-center space-x-2">
                                    <Zap size={16} /><span className="hidden sm:inline">Bulk Entry</span>
                                </button>
                                <button onClick={() => handleRefresh(false)} aria-label="Refresh" title="Refresh" className="btn-secondary flex items-center space-x-2">
                                    <RefreshCw size={16} /><span className="hidden sm:inline">Refresh</span>
                                </button>
                                <button onClick={() => setAutoRefresh(!autoRefresh)} aria-label="Toggle auto-refresh" title={autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'} className={`btn-outline flex items-center space-x-2 ${autoRefresh ? 'bg-primary-600 text-white' : ''}`}>
                                    <RefreshCw size={16} className={autoRefresh ? 'animate-spin' : ''} />
                                    <span className="hidden sm:inline">{autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}</span>
                                </button>
                                <button onClick={() => setShowFilters(!showFilters)} aria-label="Filters" title="Filters" className="btn-outline flex items-center space-x-2">
                                    <Filter size={16} /><span className="hidden sm:inline">Filters</span>
                                </button>
                            </div>
                        </div>

                        <div className="mb-4">
                            <h1 className="text-3xl font-bold text-gray-100 mb-2">Asset Analysis</h1>
                            <p className="text-gray-400">Analyze and research assets for investment decisions</p>
                        </div>

                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                            <input
                                type="text"
                                placeholder="Search assets by symbol..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="input-field w-full pl-10 pr-4 py-3"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <StatCard label="Top Gainer (24h)" icon={Award} tone="success" value={stats.topGainer.symbol} valueTitle={stats.topGainer.symbol} sub={stats.topGainer.name} detail={formatPercentage(stats.topGainer.value)} detailClassName={getChangeColor(stats.topGainer.value)} />
                        <StatCard label="Highest Dividend Yield" icon={Landmark} value={stats.highestDividend.symbol} valueTitle={stats.highestDividend.symbol} sub={stats.highestDividend.name} detail={`${formatPercentage(stats.highestDividend.value, { showSign: false })} Yield`} />
                        <StatCard label="Best Value (Lowest P/E)" icon={Gem} tone="gray" value={stats.bestValue.symbol} valueTitle={stats.bestValue.symbol} sub={stats.bestValue.name} detail={`${formatRatio(stats.bestValue.value)} P/E Ratio`} />
                        <StatCard label="Most Traded (24h)" icon={Zap} tone="warning" value={stats.mostTraded.symbol} valueTitle={stats.mostTraded.symbol} sub={stats.mostTraded.name} detail={`${formatVolume(stats.mostTraded.value)} Volume`} />
                        <StatCard label="Most Stable" icon={Shield} tone="success" value={stats.mostStable.symbol} valueTitle={stats.mostStable.symbol} sub={stats.mostStable.name} detail={`${formatRatio(stats.mostStable.value)} Beta`} />
                        <StatCard label="Highest Growth" icon={TrendingUp} value={stats.highestGrowth.symbol} valueTitle={stats.highestGrowth.symbol} sub={stats.highestGrowth.name} detail={`${formatPercentage(stats.highestGrowth.value * 100)} Revenue`} />
                        <StatCard label="Strongest Momentum" icon={ChevronsUp} tone="gray" value={stats.strongestMomentum.symbol} valueTitle={stats.strongestMomentum.symbol} sub={stats.strongestMomentum.name} detail={`${formatPercentage(stats.strongestMomentum.value, { showSign: false, precision: 1 })} of 52-Wk High`} />
                        <StatCard label="Top Loser (24h)" icon={AlertTriangle} tone="danger" value={stats.topLoser.symbol} valueTitle={stats.topLoser.symbol} sub={stats.topLoser.name} detail={formatPercentage(stats.topLoser.value)} detailClassName={getChangeColor(stats.topLoser.value)} />
                    </div>

                    {showFilters && (
                        <div className="card p-6 mb-8">
                            {/* The assets API filters by type and sorts; it has no range filters */}
                            <AssetFilters
                                filters={filters}
                                onFilterChange={handleFilterChange}
                                hidden={['priceRange', 'valueRange', 'changeRange', 'marketCapRange']}
                            />
                        </div>
                    )}

                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center space-x-2">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`p-2 rounded-lg transition-colors ${viewMode === 'grid' ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}>
                                <BarChart3 size={16} />
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                className={`p-2 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}>
                                <PieChart size={16} />
                            </button>
                        </div>
                        <p className="text-sm text-gray-400">
                            Showing {assets.length}{total != null ? ` of ${total}` : ''} assets
                        </p>
                    </div>

                    {showAnalytics && selectedAsset && (
                        <div className="mb-8">
                            <div className="flex items-center justify-between mb-4">
                                <button
                                    onClick={() => setShowAnalytics(false)}
                                    className="btn-outline flex items-center space-x-2"
                                >
                                    <ArrowLeft size={16} />
                                    <span>Back to Assets</span>
                                </button>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={() => setShowConfigurationManager(true)}
                                        className="btn-outline flex items-center space-x-2"
                                    >
                                        <Settings size={16} />
                                        <span>Manage Configurations</span>
                                    </button>
                                    {selectedConfiguration && (
                                        <div className="flex items-center space-x-2">
                                            <span className="text-sm text-gray-400">Using:</span>
                                            <span className="text-sm font-medium text-primary-400">
                                                {selectedConfiguration.name}
                                            </span>
                                            <button
                                                onClick={() => setSelectedConfiguration(null)}
                                                className="text-gray-400 hover:text-gray-100"
                                            >
                                                <X size={16} />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <AssetAnalyticsView
                                asset={selectedAsset}
                                selectedConfiguration={selectedConfiguration}
                            />
                        </div>
                    )}

                    {!showAnalytics && (
                        <>
                            {loading && assets.length === 0 ? (
                                <div className="flex justify-center items-center p-12">
                                    <LoadingSpinner type="ticker" size="lg" text="Loading assets..." />
                                </div>
                            ) : assets.length === 0 ? (
                                <div className="card p-12 text-center">
                                    <BarChart3 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                    <h3 className="text-xl font-semibold text-gray-300 mb-2">No assets found</h3>
                                    <p className="text-gray-500">
                                        {searchQuery || filters.category !== 'all' ? 'Try adjusting your search criteria' : 'No assets available for analysis'}
                                    </p>
                                </div>
                            ) : (
                                <>
                                    <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6' : 'space-y-4'}>
                                        {assets.map((asset) => (
                                            <AssetCard
                                                key={asset.id}
                                                asset={asset}
                                                viewMode={viewMode}
                                                onClick={() => handleAssetClick(asset)}
                                                onEdit={() => handleEditAsset(asset)}
                                                onDelete={() => handleDeleteAsset(asset.id)}
                                                onAddToPortfolio={handleAddToPortfolio}
                                                onViewInPortfolio={handleViewInPortfolio}
                                                onAnalytics={() => handleAnalyticsClick(asset)}
                                                onTransaction={() => handleTransactionClick(asset)}
                                            />
                                        ))}
                                    </div>
                                    <InView
                                        as="div"
                                        onChange={(inView) => {
                                            if (inView && hasMore && !loadingMore && !loading) {
                                                pages.fetchNextPage();
                                            }
                                        }}
                                        threshold={0.5}
                                    >
                                        {loadingMore && (
                                            <div className="flex justify-center items-center p-4 mt-4">
                                                <LoadingSpinner type="ticker" size="md" text="Loading more assets..." />
                                            </div>
                                        )}
                                    </InView>
                                </>
                            )}

                            {showModal && (
                                <AssetModal
                                    asset={selectedAsset}
                                    mode={modalMode}
                                    existingAssets={assets}
                                    onClose={() => {
                                        setShowModal(false);
                                        setSelectedAsset(null);
                                    }}
                                    onSave={handleAssetSave}
                                />
                            )}
                            {showBulkAssetModal && (
                                <BulkAssetModal
                                    onClose={() => setShowBulkAssetModal(false)}
                                    onSuccess={() => {
                                        setShowBulkAssetModal(false);
                                        handleRefresh();
                                    }}
                                />
                            )}

                            {showTransactionModal && transactionAsset && (
                                <CreateTransactionModal
                                    portfolios={portfolios}
                                    prefilledAsset={transactionAsset}
                                    prefilledPrice={transactionAsset.detail?.current_price || transactionAsset.current_price}
                                    onClose={() => {
                                        setShowTransactionModal(false);
                                        setTransactionAsset(null);
                                    }}
                                    onCreate={handleCreateTransaction}
                                />
                            )}
                        </>
                    )}

                    {showConfigurationManager && (
                        <Modal onClose={() => setShowConfigurationManager(false)}>
                            <div className="bg-dark-800 rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden">
                                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                                    <h3 className="text-xl font-semibold text-gray-100">Analysis Configurations</h3>
                                    <button
                                        onClick={() => setShowConfigurationManager(false)}
                                        className="text-gray-400 hover:text-gray-100"
                                    >
                                        <X size={24} />
                                    </button>
                                </div>
                                <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                                    <IndicatorConfigurationManager
                                        onConfigurationSelect={handleConfigurationSelect}
                                        selectedConfigurationId={selectedConfiguration?.id}
                                        showCreateButton={true}
                                        showSearch={true}
                                        showFilters={true}
                                    />
                                </div>
                            </div>
                        </Modal>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Assets;

