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
import { invalidateAssets, useAssetHighlights, useAssetPages, useAssets } from './queries';
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

// "low-high", "low-" or "-high" (as AssetFilters writes them) → `<field>_min` / `<field>_max`
const rangeParams = (range, field) => {
    if (!range || range === 'all') return {};
    const [low, high] = range.split('-');
    const params = {};
    if (low) params[`${field}_min`] = Number(low);
    if (high) params[`${field}_max`] = Number(high);
    return params;
};

const HighlightCard = ({ pick, detail, changeColor = false, ...card }) => (
    <StatCard
        {...card}
        value={pick ? pick.symbol : 'N/A'}
        valueTitle={pick?.symbol}
        sub={pick ? pick.name : 'Not available'}
        detail={pick ? detail(pick.value) : null}
        detailClassName={changeColor && pick ? getChangeColor(pick.value) : undefined}
    />
);

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
        changeRange: 'all',
        marketCapRange: 'all',
        sortBy: 'symbol',
        sortOrder: 'asc'
    });
    const [autoRefresh, setAutoRefresh] = useState(false);

    const apiParams = useMemo(() => {
        const params = {
            include_detail: true,
            sort_by: filters.sortBy,
            sort_order: filters.sortOrder,
        };
        if (searchQuery) params.symbol = searchQuery;
        if (filters.category !== 'all') params.asset_type = CATEGORY_TYPES[filters.category];
        Object.assign(params, rangeParams(filters.priceRange, 'price'));
        Object.assign(params, rangeParams(filters.marketCapRange, 'market_cap'));
        if (filters.changeRange !== 'all') params.change = filters.changeRange;
        return params;
    }, [filters, searchQuery]);

    const { data: portfolios = [] } = usePortfolios();
    const { data: highlights } = useAssetHighlights();
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
                        <HighlightCard label="Top Gainer (24h)" icon={Award} tone="success" pick={highlights?.top_gainer} detail={(v) => formatPercentage(v)} changeColor />
                        <HighlightCard label="Highest Dividend Yield" icon={Landmark} pick={highlights?.highest_dividend_yield} detail={(v) => `${formatPercentage(v, { showSign: false })} Yield`} />
                        <HighlightCard label="Best Value (Lowest P/E)" icon={Gem} tone="gray" pick={highlights?.lowest_pe} detail={(v) => `${formatRatio(v)} P/E Ratio`} />
                        <HighlightCard label="Most Traded (24h)" icon={Zap} tone="warning" pick={highlights?.most_traded} detail={(v) => `${formatVolume(v)} Volume`} />
                        <HighlightCard label="Most Stable" icon={Shield} tone="success" pick={highlights?.lowest_beta} detail={(v) => `${formatRatio(v)} Beta`} />
                        <HighlightCard label="Highest Growth" icon={TrendingUp} pick={highlights?.highest_revenue_growth} detail={(v) => `${formatPercentage(v)} Revenue`} />
                        <HighlightCard label="Strongest Momentum" icon={ChevronsUp} tone="gray" pick={highlights?.closest_to_52w_high} detail={(v) => `${formatPercentage(v, { showSign: false, precision: 1 })} of 52-Wk High`} />
                        <HighlightCard label="Top Loser (24h)" icon={AlertTriangle} tone="danger" pick={highlights?.top_loser} detail={(v) => formatPercentage(v)} changeColor />
                    </div>

                    {showFilters && (
                        <div className="card p-6 mb-8">
                            <AssetFilters filters={filters} onFilterChange={handleFilterChange} />
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

