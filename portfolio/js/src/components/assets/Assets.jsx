import {
    Activity,
    ArrowLeft,
    BarChart3,
    Filter,
    PieChart,
    Plus,
    RefreshCw,
    Search,
    Settings,
    TrendingDown,
    TrendingUp,
    X,
    Zap
} from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { InView } from 'react-intersection-observer';
import { portfolioAPI, transactionAPI, userAssetsAPI } from '../../services/api';
import assetCache from '../../services/assetCache';
import { formatMarketCap } from '../../utils/formatters';
import AssetAnalyticsView from '../analytics/AssetAnalyticsView';
import IndicatorConfigurationManager from '../analytics/IndicatorConfigurationManager';
import { Sidebar } from '../shared';
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
    const [viewMode, setViewMode] = useState('grid');
    const [modalMode, setModalMode] = useState('view');
    const [showAnalytics, setShowAnalytics] = useState(false);
    const [chartData, setChartData] = useState([]);
    const [selectedConfiguration, setSelectedConfiguration] = useState(null);
    const [showConfigurationManager, setShowConfigurationManager] = useState(false);
    const [showTransactionModal, setShowTransactionModal] = useState(false);
    const [transactionAsset, setTransactionAsset] = useState(null);
    const [showBulkAssetModal, setShowBulkAssetModal] = useState(false);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [totalAssetsCount, setTotalAssetsCount] = useState(0);

    const [filters, setFilters] = useState({
        category: 'all',
        priceRange: 'all',
        valueRange: 'all',
        changeRange: 'all',
        marketCapRange: 'all',
        rsiRange: 'all',
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

            if (searchQuery) apiParams.symbol = searchQuery;
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
            if (filters.rsiRange !== 'all') apiParams.rsi_range = filters.rsiRange;

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

    useEffect(() => {
        assetCache.preloadAssets();
    }, []);

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

    const handleAnalyticsClick = async (asset) => {
        setSelectedAsset(asset);
        setShowAnalytics(true);
        await loadChartData(asset);
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
            const errorMessage = error.response?.data?.detail || 'Failed to create transaction';
            toast.error(errorMessage);
            throw error;
        }
    };

    const loadChartData = async (asset) => {
        if (!asset?.id) return;
        try {
            const response = await userAssetsAPI.getUserAsset(asset.id);
            setChartData(response.price_history || []);
        } catch (error) {
            console.error('Failed to load chart data:', error);
            setChartData([]);
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

    const handleAddToPortfolio = () => {
        toast.info('Use Portfolio section to manage assets in specific portfolios');
    };

    const handleViewInPortfolio = () => {
        toast.info('Use Portfolio section to view assets in specific portfolios');
    };

    const getTotalStats = () => {
        if (!assets || assets.length === 0) {
            return { totalAssets: totalAssetsCount, dailyGainers: 0, dailyLosers: 0, totalMarketCap: 0 };
        }

        const stats = assets.reduce((acc, asset) => {
            const change = parseFloat(asset.detail?.price_change_percentage_24h || 0);
            const marketCap = parseFloat(asset.detail?.market_cap || 0);
            if (change > 0) acc.dailyGainers += 1;
            else if (change < 0) acc.dailyLosers += 1;
            if (marketCap > 0) acc.totalMarketCap += marketCap;
            return acc;
        }, { dailyGainers: 0, dailyLosers: 0, totalMarketCap: 0 });

        return { totalAssets: totalAssetsCount, ...stats };
    };

    const stats = getTotalStats();

    return (
        <div className="min-h-screen gradient-bg flex">
            <Sidebar
                currentView="assets"
                onRefresh={() => handleRefresh(false)}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                showFilters={showFilters}
                onToggleFilters={() => setShowFilters(!showFilters)}
                stats={stats}
                onQuickAction={handleQuickAction}
            />
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-7xl mx-auto p-6">
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <a href="/dashboard" className="flex items-center space-x-2 text-gray-400 hover:text-gray-300">
                                <ArrowLeft size={20} /><span>Back to Dashboard</span>
                            </a>
                            <div className="flex items-center space-x-3">
                                <button onClick={handleCreateAsset} className="btn-primary flex items-center space-x-2">
                                    <Plus size={16} /><span>Add Asset</span>
                                </button>
                                <button onClick={() => setShowBulkAssetModal(true)} className="btn-secondary flex items-center space-x-2">
                                    <Zap size={16} /><span>Bulk Entry</span>
                                </button>
                                <button onClick={() => handleRefresh(false)} className="btn-secondary flex items-center space-x-2">
                                    <RefreshCw size={16} /><span>Refresh</span>
                                </button>
                                <button onClick={() => setAutoRefresh(!autoRefresh)} className={`btn-outline flex items-center space-x-2 ${autoRefresh ? 'bg-primary-600 text-white' : ''}`}>
                                    <RefreshCw size={16} className={autoRefresh ? 'animate-spin' : ''} />
                                    <span>{autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}</span>
                                </button>
                                <button onClick={() => setShowFilters(!showFilters)} className="btn-outline flex items-center space-x-2">
                                    <Filter size={16} /><span>Filters</span>
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
                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Total Assets</p>
                                    <p className="text-2xl font-bold text-gray-100">{stats.totalAssets}</p>
                                </div>
                                <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                    <BarChart3 size={24} className="text-primary-400" />
                                </div>
                            </div>
                        </div>
                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Daily Gainers</p>
                                    <p className="text-2xl font-bold text-success-400">{stats.dailyGainers}</p>
                                    <p className="text-xs text-gray-500">assets gaining in 24h</p>
                                </div>
                                <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                                    <TrendingUp size={24} className="text-success-400" />
                                </div>
                            </div>
                        </div>
                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Daily Losers</p>
                                    <p className="text-2xl font-bold text-danger-400">{stats.dailyLosers}</p>
                                    <p className="text-xs text-gray-500">assets losing in 24h</p>
                                </div>
                                <div className="w-12 h-12 bg-danger-600/20 rounded-lg flex items-center justify-center">
                                    <TrendingDown size={24} className="text-danger-400" />
                                </div>
                            </div>
                        </div>
                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Total Market Cap</p>
                                    <p className="text-2xl font-bold text-primary-400">{formatMarketCap(stats.totalMarketCap)}</p>
                                    <p className="text-xs text-gray-500">of loaded assets</p>
                                </div>
                                <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                    <PieChart size={24} className="text-primary-400" />
                                </div>
                            </div>
                        </div>
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
                            Showing {assets.length} of {totalAssetsCount} assets
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
                                chartData={chartData}
                                selectedConfiguration={selectedConfiguration}
                                onRefresh={() => loadChartData(selectedAsset)}
                            />
                        </div>
                    )}

                    {!showAnalytics && (
                        <>
                            {loading && assets.length === 0 ? (
                                <div className="flex justify-center items-center p-12">
                                    <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
                                    <p className="ml-3 text-gray-400">Loading assets...</p>
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
                                                <RefreshCw className="w-6 h-6 text-primary-400 animate-spin" />
                                                <p className="ml-2 text-gray-400">Loading more assets...</p>
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

                            {showConfigurationManager && (
                                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
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
                </div>
            </div>
        </div>
    );
};

export default Assets;

