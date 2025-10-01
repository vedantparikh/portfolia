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
    X
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { portfolioAPI, transactionAPI, userAssetsAPI } from '../../services/api';
import assetCache from '../../services/assetCache';
import AssetAnalyticsView from '../analytics/AssetAnalyticsView';
import IndicatorConfigurationManager from '../analytics/IndicatorConfigurationManager';
import { Sidebar } from '../shared';
import CreateTransactionModal from '../transactions/CreateTransactionModal';
import AssetCard from './AssetCard';
import AssetFilters from './AssetFilters';
import AssetModal from './AssetModal';

const Assets = () => {
    const [assets, setAssets] = useState([]);
    const [filteredAssets, setFilteredAssets] = useState([]);
    const [portfolios, setPortfolios] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [showFilters, setShowFilters] = useState(false);
    const [viewMode, setViewMode] = useState('grid'); // grid or list
    const [modalMode, setModalMode] = useState('view'); // view, create, edit
    const [showAnalytics, setShowAnalytics] = useState(false);
    const [chartData, setChartData] = useState([]);
    const [selectedConfiguration, setSelectedConfiguration] = useState(null);
    const [showConfigurationManager, setShowConfigurationManager] = useState(false);
    const [showTransactionModal, setShowTransactionModal] = useState(false);
    const [transactionAsset, setTransactionAsset] = useState(null);
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

    // Load assets on component mount
    useEffect(() => {
        let isMounted = true;

        const loadAssetsSafe = async () => {
            try {
                setLoading(true);

                // Load portfolios for transaction creation
                const portfoliosResponse = await portfolioAPI.getPortfolios();
                console.log('[Assets] Portfolios response:', portfoliosResponse);

                const response = await userAssetsAPI.getUserAssets({
                    limit: 100,
                    include_detail: true,
                    include_performance: true,
                    include_analytics: true
                });

                // Only update state if component is still mounted
                if (isMounted) {
                    console.log('[Assets] User assets response:', response);
                    setAssets(response.assets || []);
                    setPortfolios(portfoliosResponse || []);
                }
            } catch (error) {
                if (isMounted) {
                    console.error('Failed to load user assets:', error);
                    toast.error('Failed to load your assets');
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };

        loadAssetsSafe();

        // Cleanup function to prevent state updates on unmounted component
        return () => {
            isMounted = false;
        };
    }, []);

    // Filter assets when search query or filters change
    useEffect(() => {
        filterAssets();
    }, [assets, searchQuery, filters]);

    // Auto-refresh functionality
    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(() => {
                loadAssets();
            }, 30000); // Refresh every 30 seconds
            setRefreshInterval(interval);
        } else {
            if (refreshInterval) {
                clearInterval(refreshInterval);
                setRefreshInterval(null);
            }
        }

        return () => {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        };
    }, [autoRefresh]);

    // External loadAssets function for manual refresh and other operations
    const loadAssets = async () => {
        try {
            setLoading(true);

            // Load portfolios for transaction creation
            const portfoliosResponse = await portfolioAPI.getPortfolios();
            console.log('[Assets] Portfolios response:', portfoliosResponse);

            const response = await userAssetsAPI.getUserAssets({
                limit: 100,
                include_detail: true,
                include_performance: true,
                include_analytics: true
            });
            console.log('[Assets] User assets response:', response);
            setAssets(response.assets || []);
            setPortfolios(portfoliosResponse || []);
        } catch (error) {
            console.error('Failed to load user assets:', error);
            toast.error('Failed to load your assets');
        } finally {
            setLoading(false);
        }
    };

    const filterAssets = () => {
        let filtered = [...assets];

        // Search filter
        if (searchQuery) {
            filtered = filtered.filter(asset =>
                asset.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
                asset.name.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }

        // Category filter
        if (filters.category !== 'all') {
            filtered = filtered.filter(asset => {
                // Map frontend categories to backend asset types
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
                return asset.asset_type === categoryMap[filters.category];
            });
        }

        // Price range filter
        if (filters.priceRange !== 'all') {
            const [min, max] = filters.priceRange.split('-').map(Number);
            filtered = filtered.filter(asset => {
                const price = asset.current_price || 0;
                if (max) {
                    return price >= min && price <= max;
                } else {
                    return price >= min;
                }
            });
        }

        // Value range filter
        if (filters.valueRange !== 'all') {
            const [min, max] = filters.valueRange.split('-').map(Number);
            filtered = filtered.filter(asset => {
                const totalValue = (asset.quantity || 0) * (asset.current_price || 0);
                if (max) {
                    return totalValue >= min && totalValue <= max;
                } else {
                    return totalValue >= min;
                }
            });
        }

        // Change range filter
        if (filters.changeRange !== 'all') {
            filtered = filtered.filter(asset => {
                const change = asset.price_change_percentage_24h || 0;
                switch (filters.changeRange) {
                    case 'positive':
                        return change > 0;
                    case 'negative':
                        return change < 0;
                    case 'stable':
                        return change >= -1 && change <= 1;
                    default:
                        return true;
                }
            });
        }

        // Market cap range filter
        if (filters.marketCapRange !== 'all') {
            filtered = filtered.filter(asset => {
                const marketCap = asset.market_cap || 0;
                switch (filters.marketCapRange) {
                    case '0-1e6':
                        return marketCap < 1e6;
                    case '1e6-1e9':
                        return marketCap >= 1e6 && marketCap < 1e9;
                    case '1e9-1e12':
                        return marketCap >= 1e9 && marketCap < 1e12;
                    case '1e12-':
                        return marketCap >= 1e12;
                    default:
                        return true;
                }
            });
        }

        // RSI range filter
        if (filters.rsiRange !== 'all') {
            filtered = filtered.filter(asset => {
                const rsi = asset.rsi;
                if (rsi === null || rsi === undefined) return false;
                switch (filters.rsiRange) {
                    case '0-30':
                        return rsi >= 0 && rsi <= 30;
                    case '30-70':
                        return rsi > 30 && rsi < 70;
                    case '70-100':
                        return rsi >= 70 && rsi <= 100;
                    default:
                        return true;
                }
            });
        }

        // Sort
        filtered.sort((a, b) => {
            let aValue, bValue;

            switch (filters.sortBy) {
                case 'symbol':
                    aValue = a.symbol || '';
                    bValue = b.symbol || '';
                    break;
                case 'name':
                    aValue = a.name || '';
                    bValue = b.name || '';
                    break;
                case 'quantity':
                    aValue = a.quantity || 0;
                    bValue = b.quantity || 0;
                    break;
                case 'purchase_price':
                    aValue = a.purchase_price || 0;
                    bValue = b.purchase_price || 0;
                    break;
                case 'current_price':
                    aValue = a.current_price || 0;
                    bValue = b.current_price || 0;
                    break;
                case 'total_value':
                    aValue = (a.quantity || 0) * (a.current_price || 0);
                    bValue = (b.quantity || 0) * (b.current_price || 0);
                    break;
                case 'purchase_date':
                    aValue = new Date(a.purchase_date || 0);
                    bValue = new Date(b.purchase_date || 0);
                    break;
                case 'market_cap':
                    aValue = a.market_cap || 0;
                    bValue = b.market_cap || 0;
                    break;
                case 'volume_24h':
                    aValue = a.volume_24h || 0;
                    bValue = b.volume_24h || 0;
                    break;
                case 'price_change_percentage_24h':
                    aValue = a.price_change_percentage_24h || 0;
                    bValue = b.price_change_percentage_24h || 0;
                    break;
                default:
                    aValue = a.symbol || '';
                    bValue = b.symbol || '';
            }

            if (filters.sortBy === 'symbol' || filters.sortBy === 'name') {
                // String comparison
                if (filters.sortOrder === 'asc') {
                    return aValue.localeCompare(bValue);
                } else {
                    return bValue.localeCompare(aValue);
                }
            } else {
                // Numeric comparison
                if (filters.sortOrder === 'asc') {
                    return aValue - bValue;
                } else {
                    return bValue - aValue;
                }
            }
        });

        setFilteredAssets(filtered);
    };

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
            console.log('[Assets] Creating transaction with data:', transactionData);
            const response = await transactionAPI.createTransaction(transactionData);
            console.log('[Assets] Create response:', response);

            setShowTransactionModal(false);
            setTransactionAsset(null);
            toast.success('Transaction created successfully');

            // Refresh assets to ensure consistency
            setTimeout(() => {
                loadAssets();
            }, 500);
        } catch (error) {
            console.error('Failed to create transaction:', error);
            const errorMessage = error.response?.data?.detail || error.message || 'Failed to create transaction';
            toast.error(errorMessage);
            throw error; // Re-throw so the modal can handle it
        }
    };

    const loadChartData = async (asset) => {
        if (!asset?.id) return;

        try {
            // Load chart data with statistical indicators
            const response = await userAssetsAPI.getUserAsset(asset.id);
            // For now, we'll use mock data or existing data
            // In a real implementation, this would call the statistical indicators API
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
        if (window.confirm('Are you sure you want to delete this asset?')) {
            try {
                await userAssetsAPI.deleteUserAsset(assetId);
                toast.success('Asset deleted successfully');
                loadAssets(); // Reload assets
            } catch (error) {
                console.error('Failed to delete asset:', error);
                toast.error('Failed to delete asset');
            }
        }
    };

    const handleAssetSave = async (assetData) => {
        try {
            let savedAsset;
            if (modalMode === 'create') {
                savedAsset = await userAssetsAPI.createUserAsset(assetData);
                toast.success('Asset added successfully');

                // Refresh the asset cache to include the new asset
                try {
                    await assetCache.refreshCache();
                    console.log('[Assets] Asset cache refreshed after creating new asset');
                } catch (cacheError) {
                    console.warn('[Assets] Failed to refresh asset cache:', cacheError);
                }
            } else if (modalMode === 'edit') {
                savedAsset = await userAssetsAPI.updateUserAsset(selectedAsset.id, assetData);
                toast.success('Asset updated successfully');

                // Refresh the asset cache to include the updated asset
                try {
                    await assetCache.refreshCache();
                    console.log('[Assets] Asset cache refreshed after updating asset');
                } catch (cacheError) {
                    console.warn('[Assets] Failed to refresh asset cache:', cacheError);
                }
            }
            loadAssets(); // Reload assets
            setShowModal(false);
            setSelectedAsset(null);
            return savedAsset; // Return the saved asset for transaction creation
        } catch (error) {
            console.error('Failed to save asset:', error);
            toast.error(`Failed to ${modalMode === 'create' ? 'create' : 'update'} asset`);
            throw error; // Re-throw error so AssetModal can handle it
        }
    };

    const handleRefresh = () => {
        loadAssets();
        toast.success('Assets refreshed');
    };

    const handleFilterChange = (newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    };

    const handleQuickAction = (action) => {
        switch (action) {
            case 'refresh':
                handleRefresh();
                break;
            default:
                break;
        }
    };

    const handleAddToPortfolio = (asset) => {
        // Removed - no longer allowing direct portfolio addition
        toast.info('Use Portfolio section to manage assets in specific portfolios');
    };

    const handleViewInPortfolio = (asset) => {
        // Removed - no longer allowing direct portfolio view
        toast.info('Use Portfolio section to view assets in specific portfolios');
    };

    const getTotalStats = () => {
        const totalValue = filteredAssets.reduce((sum, asset) => {
            const value = (asset.quantity || 0) * (asset.current_price || 0);
            return sum + value;
        }, 0);

        const totalInvested = filteredAssets.reduce((sum, asset) => {
            const invested = (asset.quantity || 0) * (asset.purchase_price || 0);
            return sum + invested;
        }, 0);

        const totalPnL = totalValue - totalInvested;
        const totalPnLPercentage = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

        const positiveAssets = filteredAssets.filter(asset => {
            if (!asset.quantity || !asset.purchase_price || !asset.current_price) return false;
            const pnl = ((asset.current_price - asset.purchase_price) / asset.purchase_price) * 100;
            return pnl > 0;
        }).length;

        const negativeAssets = filteredAssets.filter(asset => {
            if (!asset.quantity || !asset.purchase_price || !asset.current_price) return false;
            const pnl = ((asset.current_price - asset.purchase_price) / asset.purchase_price) * 100;
            return pnl < 0;
        }).length;

        return {
            totalValue,
            totalInvested,
            totalPnL,
            totalPnLPercentage,
            positiveAssets,
            negativeAssets,
            totalAssets: filteredAssets.length
        };
    };

    const stats = getTotalStats();

    if (loading) {
        return (
            <div className="min-h-screen gradient-bg flex items-center justify-center">
                <div className="text-center">
                    <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading assets...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen gradient-bg flex">
            <Sidebar
                currentView="assets"
                onRefresh={handleRefresh}
                searchQuery={searchQuery}
                onSearchChange={setSearchQuery}
                showFilters={showFilters}
                onToggleFilters={() => setShowFilters(!showFilters)}
                stats={stats}
                onQuickAction={handleQuickAction}
            />
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-7xl mx-auto p-6">
                    {/* Header */}
                    <div className="mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center space-x-4">
                                <a
                                    href="/dashboard"
                                    className="flex items-center space-x-2 text-gray-400 hover:text-gray-300 transition-colors"
                                >
                                    <ArrowLeft size={20} />
                                    <span>Back to Dashboard</span>
                                </a>
                            </div>
                            <div className="flex items-center space-x-3">
                                <button
                                    onClick={handleCreateAsset}
                                    className="btn-primary flex items-center space-x-2"
                                >
                                    <Plus size={16} />
                                    <span>Add Asset</span>
                                </button>
                                <button
                                    onClick={handleRefresh}
                                    className="btn-secondary flex items-center space-x-2"
                                >
                                    <RefreshCw size={16} />
                                    <span>Refresh</span>
                                </button>
                                <button
                                    onClick={() => setAutoRefresh(!autoRefresh)}
                                    className={`btn-outline flex items-center space-x-2 ${autoRefresh ? 'bg-primary-600 text-white' : ''}`}
                                >
                                    <RefreshCw size={16} className={autoRefresh ? 'animate-spin' : ''} />
                                    <span>{autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}</span>
                                </button>
                                <button
                                    onClick={() => setShowFilters(!showFilters)}
                                    className="btn-outline flex items-center space-x-2"
                                >
                                    <Filter size={16} />
                                    <span>Filters</span>
                                </button>
                            </div>
                        </div>

                        <div className="mb-4">
                            <h1 className="text-3xl font-bold text-gray-100 mb-2">Asset Analysis</h1>
                            <p className="text-gray-400">Analyze and research assets for investment decisions</p>
                        </div>

                        {/* Search Bar */}
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

                    {/* Analysis Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Assets Analyzed</p>
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
                                    <p className="text-sm text-gray-400">Market Leaders</p>
                                    <p className="text-2xl font-bold text-success-400">{stats.positiveAssets}</p>
                                    <p className="text-xs text-gray-500">positive performers</p>
                                </div>
                                <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                                    <TrendingUp size={24} className="text-success-400" />
                                </div>
                            </div>
                        </div>

                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Market Laggards</p>
                                    <p className="text-2xl font-bold text-danger-400">{stats.negativeAssets}</p>
                                    <p className="text-xs text-gray-500">underperforming</p>
                                </div>
                                <div className="w-12 h-12 bg-danger-600/20 rounded-lg flex items-center justify-center">
                                    <TrendingDown size={24} className="text-danger-400" />
                                </div>
                            </div>
                        </div>

                        <div className="card p-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-gray-400">Analysis Tools</p>
                                    <p className="text-2xl font-bold text-primary-400">RSI, MACD</p>
                                    <p className="text-xs text-gray-500">technical indicators</p>
                                </div>
                                <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                    <Activity size={24} className="text-primary-400" />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Filters */}
                    {showFilters && (
                        <div className="card p-6 mb-8">
                            <AssetFilters
                                filters={filters}
                                onFilterChange={handleFilterChange}
                            />
                        </div>
                    )}

                    {/* View Mode Toggle */}
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center space-x-2">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`p-2 rounded-lg transition-colors ${viewMode === 'grid'
                                    ? 'bg-primary-600 text-white'
                                    : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
                                    }`}
                            >
                                <BarChart3 size={16} />
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                className={`p-2 rounded-lg transition-colors ${viewMode === 'list'
                                    ? 'bg-primary-600 text-white'
                                    : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
                                    }`}
                            >
                                <PieChart size={16} />
                            </button>
                        </div>
                        <p className="text-sm text-gray-400">
                            Showing {filteredAssets.length} of {assets.length} assets
                        </p>
                    </div>

                    {/* Analytics View */}
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

                    {/* Assets Grid/List */}
                    {!showAnalytics && filteredAssets.length === 0 ? (
                        <div className="space-y-6">
                            <div className="card p-12 text-center">
                                <BarChart3 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                <h3 className="text-xl font-semibold text-gray-300 mb-2">No assets found</h3>
                                <p className="text-gray-500">
                                    {searchQuery ? 'Try adjusting your search criteria' : 'No assets available for analysis'}
                                </p>
                                <p className="text-sm text-gray-600 mt-2">
                                    Use this section to analyze assets before adding them to your portfolios
                                </p>
                            </div>
                        </div>
                    ) : (
                        <div className={
                            viewMode === 'grid'
                                ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                                : 'space-y-4'
                        }>
                            {filteredAssets.map((asset) => (
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
                    )}

                    {/* Asset Modal */}
                    {showModal && (
                        <AssetModal
                            asset={selectedAsset}
                            mode={modalMode}
                            existingAssets={assets}
                            onClose={() => {
                                setShowModal(false);
                                setSelectedAsset(null);
                                setModalMode('view');
                            }}
                            onSave={handleAssetSave}
                        />
                    )}

                    {/* Configuration Manager Modal */}
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

                    {/* Create Transaction Modal */}
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
                </div>
            </div>
        </div>
    );
};

export default Assets;
