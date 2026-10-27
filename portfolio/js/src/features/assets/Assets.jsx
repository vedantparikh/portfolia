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
import { useCallback, useEffect, useState } from 'react';
import useIsMobile from '../../hooks/useIsMobile';
import toast from 'react-hot-toast';
import { InView } from 'react-intersection-observer';
import { apiErrorMessage, portfolioAPI, transactionAPI, userAssetsAPI } from '../../services/api';
import { useAssets } from '../../shared/api/queries';
import { formatVolume, getChangeColor } from '../../utils/formatters';
import AssetAnalyticsView from '../analytics/AssetAnalyticsView';
import IndicatorConfigurationManager from '../analytics/IndicatorConfigurationManager';
import { usePageChrome, useShell } from '../../app/chrome';
import { LoadingSpinner, StatCard } from '../../components/shared';
import CreateTransactionModal from '../transactions/CreateTransactionModal';
import AssetCard from './AssetCard';
import AssetFilters from './AssetFilters';
import AssetModal from './AssetModal';
import BulkAssetModal from './BulkAssetModal';

const PAGE_SIZE = 8; // How many items to fetch per page

const Assets = () => {
    const [assets, setAssets] = useState([]);
    const [portfolios, setPortfolios] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
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
    const [, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [totalAssetsCount, setTotalAssetsCount] = useState(0);

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
    const [refreshInterval, setRefreshInterval] = useState(null);

    const loadData = useCallback(async (currentPage, isRefresh = false) => {
        if (currentPage > 1) {
            setLoadingMore(true);
        } else {
            setLoading(true);
        }

        try {
            if (currentPage === 1 && portfolios.length === 0) {
                const portfoliosResponse = await portfolioAPI.getPortfolios();
                setPortfolios(portfoliosResponse || []);
            }

            const skip = (currentPage - 1) * PAGE_SIZE;

            const apiParams = {
                limit: PAGE_SIZE,
                skip: skip,
                include_detail: true,
                include_performance: true,
                include_analytics: true,
                sort_by: filters.sortBy,
                sort_order: filters.sortOrder,
            };

            if (searchQuery) apiParams.query = searchQuery;
            if (filters.category !== 'all') {
                const categoryMap = {
                    'cryptocurrency': 'CRYPTOCURRENCY',
                    'stock': 'EQUITY',
                    'commodity': 'COMMODITY',
                    'forex': 'CASH',
                    'etf': 'ETF',
                    'bond': 'BOND',
                    'real_estate': 'REAL_ESTATE',
                    'mutual_fund': 'MUTUALFUND',
                    'index_fund': 'INDEX'
                };
                apiParams.asset_type = categoryMap[filters.category];
            }
            if (filters.priceRange !== 'all') apiParams.price_range = filters.priceRange;
            if (filters.valueRange !== 'all') apiParams.value_range = filters.valueRange;
            if (filters.changeRange !== 'all') apiParams.change_range = filters.changeRange;
            if (filters.marketCapRange !== 'all') apiParams.market_cap_range = filters.marketCapRange;

            const response = await userAssetsAPI.getUserAssets(apiParams);

            if (response?.assets) {
                setHasMore(response.assets.length === PAGE_SIZE);
                // After
                setAssets(prev => {
                    if (isRefresh) {
                        return response.assets; // For a refresh, just replace the data
                    }
                    // For infinite scroll, combine previous and new assets
                    const combinedAssets = [...prev, ...response.assets];
                    // Create a new array with unique assets based on their ID
                    const uniqueAssets = Array.from(new Map(combinedAssets.map(asset => [asset.id, asset])).values());
                    return uniqueAssets;
                });
                if (response.total) {
                    setTotalAssetsCount(response.total);
                }
            } else {
                setHasMore(false);
                if (isRefresh) setAssets([]);
            }
        } catch (error) {
            console.error('Failed to load user assets:', error);
            toast.error('Failed to load your assets');
        } finally {
            setLoading(false);
            setLoadingMore(false);
        }
    }, [filters, searchQuery, portfolios.length]);


    useEffect(() => {
        setAssets([]);
        setPage(1);
        setHasMore(true);
        loadData(1, true);
    }, [filters, searchQuery, loadData]);

    useAssets();

    const handleRefresh = useCallback((silent = false) => {
        setPage(1);
        setHasMore(true);
        loadData(1, true);
        if (!silent) toast.success('Assets refreshed');
    }, [loadData]);

    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(() => handleRefresh(true), 30000);
            setRefreshInterval(interval);
        } else if (refreshInterval) {
            clearInterval(refreshInterval);
        }
        return () => {
            if (refreshInterval) clearInterval(refreshInterval);
        };
    }, [autoRefresh, handleRefresh, refreshInterval]);

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
            setTimeout(() => handleRefresh(), 500);
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
            await userAssetsAPI.deleteUserAsset(assetId);
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
                await userAssetsAPI.createUserAsset(assetData);
                toast.success('Asset added successfully');
            } else if (modalMode === 'edit') {
                await userAssetsAPI.updateUserAsset(selectedAsset.id, assetData);
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
        if (action === 'refresh') handleRefresh();
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
                                placeholder="Search assets by symbol or name..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="input-field w-full pl-10 pr-4 py-3"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <StatCard label="Top Gainer (24h)" icon={Award} tone="success" value={stats.topGainer.symbol} valueTitle={stats.topGainer.symbol} sub={stats.topGainer.name} detail={`+${stats.topGainer.value.toFixed(2)}%`} detailClassName={getChangeColor(stats.topGainer.value)} />
                        <StatCard label="Highest Dividend Yield" icon={Landmark} value={stats.highestDividend.symbol} valueTitle={stats.highestDividend.symbol} sub={stats.highestDividend.name} detail={`${stats.highestDividend.value.toFixed(2)}% Yield`} />
                        <StatCard label="Best Value (Lowest P/E)" icon={Gem} tone="gray" value={stats.bestValue.symbol} valueTitle={stats.bestValue.symbol} sub={stats.bestValue.name} detail={`${stats.bestValue.value.toFixed(2)} P/E Ratio`} />
                        <StatCard label="Most Traded (24h)" icon={Zap} tone="warning" value={stats.mostTraded.symbol} valueTitle={stats.mostTraded.symbol} sub={stats.mostTraded.name} detail={`${formatVolume(stats.mostTraded.value)} Volume`} />
                        <StatCard label="Most Stable" icon={Shield} tone="success" value={stats.mostStable.symbol} valueTitle={stats.mostStable.symbol} sub={stats.mostStable.name} detail={`${stats.mostStable.value.toFixed(2)} Beta`} />
                        <StatCard label="Highest Growth" icon={TrendingUp} value={stats.highestGrowth.symbol} valueTitle={stats.highestGrowth.symbol} sub={stats.highestGrowth.name} detail={`+${(stats.highestGrowth.value * 100).toFixed(2)}% Revenue`} />
                        <StatCard label="Strongest Momentum" icon={ChevronsUp} tone="gray" value={stats.strongestMomentum.symbol} valueTitle={stats.strongestMomentum.symbol} sub={stats.strongestMomentum.name} detail={`${stats.strongestMomentum.value.toFixed(1)}% of 52-Wk High`} />
                        <StatCard label="Top Loser (24h)" icon={AlertTriangle} tone="danger" value={stats.topLoser.symbol} valueTitle={stats.topLoser.symbol} sub={stats.topLoser.name} detail={`${stats.topLoser.value.toFixed(2)}%`} detailClassName={getChangeColor(stats.topLoser.value)} />
                    </div>

                    {showFilters && (
                        <div className="card p-6 mb-8">
                            {/* The assets API only filters by type; ranges and sorting are ignored server-side */}
                            <AssetFilters
                                filters={filters}
                                onFilterChange={handleFilterChange}
                                hidden={['priceRange', 'valueRange', 'changeRange', 'marketCapRange', 'sort']}
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
                            Showing {assets.length}
                            {totalAssetsCount > assets.length ? ` of ${totalAssetsCount}` : ""} assets
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
                                                setPage(prev => {
                                                    const nextPage = prev + 1;
                                                    loadData(nextPage);
                                                    return nextPage;
                                                });
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
                        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
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
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Assets;

