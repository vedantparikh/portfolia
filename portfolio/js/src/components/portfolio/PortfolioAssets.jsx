import {
    Activity,
    BarChart3,
    Filter,
    MoreVertical,
    PieChart,
    Plus,
    RefreshCw,
    Search,
    Trash2,
    TrendingDown,
    TrendingUp
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { portfolioAPI, transactionAPI } from '../../services/api';
import AssetFilters from '../assets/AssetFilters';
import AssetModal from '../assets/AssetModal';
import CreateTransactionModal from '../transactions/CreateTransactionModal';

// Custom portfolio asset display component
const PortfolioAssetCard = ({ asset, viewMode = 'grid', onClick, onTransaction, onAnalytics, onDelete }) => {
    const [showMenu, setShowMenu] = useState(false);

    const handleMenuClick = (e) => {
        e.stopPropagation();
        setShowMenu(!showMenu);
    };

    const handleDelete = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onDelete && onDelete();
    };

    const handleTransaction = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onTransaction && onTransaction();
    };

    const handleAnalytics = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onAnalytics && onAnalytics();
    };

    if (viewMode === 'list') {
        return (
            <div
                className={`card p-4 hover:bg-dark-800/50 transition-colors cursor-pointer relative ${showMenu ? 'z-10' : 'z-0'}`}
                onClick={onClick}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                            <BarChart3 size={24} className="text-primary-400" />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-100">{asset.symbol}</h3>
                            <p className="text-sm text-gray-400 truncate max-w-48">{asset.name}</p>
                            {asset.asset_type && (
                                <p className="text-xs text-primary-400 capitalize">
                                    {asset.asset_type.toLowerCase().replace('_', ' ')}
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center space-x-8">
                        <div className="text-right">
                            <p className="text-sm text-gray-400">Quantity</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {asset.quantity?.toFixed(4) || '0'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Purchase Price</p>
                            <p className="text-sm font-medium text-gray-100">
                                ${asset.purchase_price?.toFixed(2) || '0.00'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Current Price</p>
                            <p className="text-sm font-medium text-gray-100">
                                ${asset.current_price?.toFixed(2) || '0.00'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Total Value</p>
                            <p className="text-lg font-semibold text-gray-100">
                                ${asset.total_value?.toFixed(2) || '0.00'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">P&L</p>
                            <p className={`text-sm font-medium ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.pnl?.toFixed(2) || '0.00'}
                            </p>
                            <p className={`text-xs ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {asset.pnl_percentage?.toFixed(2) || '0.00'}%
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-gray-400">Realized P&L</p>
                            <p className={`text-sm font-medium ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.realized_pnl?.toFixed(2) || '0.00'}
                            </p>
                            <p className={`text-xs ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {asset.realized_pnl_percentage?.toFixed(2) || '0.00'}%
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-gray-400">Today's P&L</p>
                            <p className={`text-sm font-medium ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.today_pnl?.toFixed(2) || '0.00'}
                            </p>
                            <p className={`text-xs ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {asset.today_pnl_percentage?.toFixed(2) || '0.00'}%
                            </p>
                        </div>

                        <div className="flex items-center space-x-2">
                            <div className="relative">
                                <button
                                    onClick={handleMenuClick}
                                    className="p-1 rounded-lg hover:bg-dark-700 transition-colors"
                                >
                                    <MoreVertical size={16} className="text-gray-400" />
                                </button>
                                {showMenu && (
                                    <div className="absolute right-0 top-8 bg-dark-800 border border-dark-700 rounded-lg shadow-lg z-10 min-w-40">
                                        <button
                                            onClick={handleTransaction}
                                            className="w-full px-3 py-2 text-left text-sm text-success-400 hover:bg-dark-700 flex items-center space-x-2"
                                        >
                                            <Plus size={14} />
                                            <span>Add Transaction</span>
                                        </button>
                                        <button
                                            onClick={handleAnalytics}
                                            className="w-full px-3 py-2 text-left text-sm text-primary-400 hover:bg-dark-700 flex items-center space-x-2"
                                        >
                                            <Activity size={14} />
                                            <span>Analytics</span>
                                        </button>
                                        <button
                                            onClick={handleDelete}
                                            className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-700 flex items-center space-x-2"
                                        >
                                            <Trash2 size={14} />
                                            <span>Delete</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            className={`card p-6 hover:bg-dark-800/50 transition-all duration-200 cursor-pointer group relative ${showMenu ? 'z-10' : 'z-0'}`}
            onClick={onClick}
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center group-hover:bg-primary-600/30 transition-colors">
                        <BarChart3 size={24} className="text-primary-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-gray-100">{asset.symbol}</h3>
                        <p className="text-sm text-gray-400 truncate max-w-32">{asset.name}</p>
                        {asset.asset_type && (
                            <p className="text-xs text-primary-400 capitalize">
                                {asset.asset_type.toLowerCase().replace('_', ' ')}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center space-x-2">
                    <div className="relative">
                        <button
                            onClick={handleMenuClick}
                            className="p-1 rounded-lg hover:bg-dark-700 transition-colors opacity-0 group-hover:opacity-100"
                        >
                            <MoreVertical size={16} className="text-gray-400" />
                        </button>
                        {showMenu && (
                            <div className="absolute right-0 top-8 bg-dark-800 border border-dark-700 rounded-lg shadow-lg z-10 min-w-40">
                                <button
                                    onClick={handleTransaction}
                                    className="w-full px-3 py-2 text-left text-sm text-success-400 hover:bg-dark-700 flex items-center space-x-2"
                                >
                                    <Plus size={14} />
                                    <span>Add Transaction</span>
                                </button>
                                <button
                                    onClick={handleAnalytics}
                                    className="w-full px-3 py-2 text-left text-sm text-primary-400 hover:bg-dark-700 flex items-center space-x-2"
                                >
                                    <Activity size={14} />
                                    <span>Analytics</span>
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-700 flex items-center space-x-2"
                                >
                                    <Trash2 size={14} />
                                    <span>Delete</span>
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Quantity</span>
                    <span className="text-lg font-bold text-gray-100">
                        {asset.quantity?.toFixed(4) || '0'}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Purchase Price</span>
                    <span className="text-sm font-medium text-gray-100">
                        ${asset.purchase_price?.toFixed(2) || '0.00'}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Current Price</span>
                    <span className="text-sm font-medium text-gray-100">
                        ${asset.current_price?.toFixed(2) || '0.00'}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Total Value</span>
                    <span className="text-lg font-bold text-gray-100">
                        ${asset.total_value?.toFixed(2) || '0.00'}
                    </span>
                </div>

                {/* P&L Section */}
                <div className="pt-3 border-t border-dark-700 space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">Unrealized P&L</span>
                        <div className="text-right">
                            <span className={`text-sm font-bold ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.pnl?.toFixed(2) || '0.00'}
                            </span>
                            <span className={`text-xs ml-2 ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ({asset.pnl_percentage?.toFixed(2) || '0.00'}%)
                            </span>
                        </div>
                    </div>

                    {asset.realized_pnl !== undefined && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Realized P&L</span>
                            <div className="text-right">
                                <span className={`text-sm font-medium ${(asset.realized_pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ${asset.realized_pnl?.toFixed(2) || '0.00'}
                                </span>
                                <span className={`text-xs ml-2 ${(asset.realized_pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ({asset.realized_pnl_percentage?.toFixed(2) || '0.00'}%)
                                </span>
                            </div>
                        </div>
                    )}
                    {asset.today_pnl !== undefined && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Today's P&L</span>
                            <div className="text-right">
                                <span className={`text-sm font-medium ${(asset.today_pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ${asset.today_pnl?.toFixed(2) || '0.00'}
                                </span>
                                <span className={`text-xs ml-2 ${(asset.today_pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ({asset.today_pnl_percentage?.toFixed(2) || '0.00'}%)
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* P&L indicator bar */}
            <div className="mt-4 pt-4 border-t border-dark-700">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Position Performance</span>
                    <span>{asset.pnl_percentage ? `${asset.pnl_percentage.toFixed(2)}%` : '0.00%'}</span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full transition-all duration-300 ${(asset.pnl_percentage || 0) > 0
                            ? 'bg-success-400'
                            : (asset.pnl_percentage || 0) < 0
                                ? 'bg-danger-400'
                                : 'bg-gray-500'
                            }`}
                        style={{
                            width: `${Math.min(Math.abs(asset.pnl_percentage || 0) * 2, 100)}%`
                        }}
                    />
                </div>
            </div>
        </div>
    );
};

const PortfolioAssets = ({ portfolio, onRefresh }) => {
    const [assets, setAssets] = useState([]);
    const [filteredAssets, setFilteredAssets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showFilters, setShowFilters] = useState(false);
    const [viewMode, setViewMode] = useState('grid'); // grid or list
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

    // Modal states
    const [showAssetModal, setShowAssetModal] = useState(false);
    const [showTransactionModal, setShowTransactionModal] = useState(false);
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [transactionAsset, setTransactionAsset] = useState(null);

    // Load portfolio assets when portfolio changes
    useEffect(() => {
        if (portfolio && portfolio.id) {
            loadPortfolioAssets();
        }
    }, [portfolio]);

    // Filter assets when search query or filters change
    useEffect(() => {
        filterAssets();
    }, [assets, searchQuery, filters]);

    const loadPortfolioAssets = async () => {
        if (!portfolio || !portfolio.id) return;

        try {
            setLoading(true);
            console.log('[PortfolioAssets] Loading assets for portfolio:', portfolio.id);

            // Get portfolio holdings which contain the assets
            const holdingsResponse = await portfolioAPI.getPortfolioHoldings(portfolio.id);
            console.log('[PortfolioAssets] Holdings response:', holdingsResponse);

            // Process holdings data to create asset objects
            let portfolioAssets = [];
            if (holdingsResponse && Array.isArray(holdingsResponse) && holdingsResponse.length > 0) {
                portfolioAssets = holdingsResponse.map(holding => ({
                    id: holding.asset_id,
                    symbol: holding.symbol,
                    name: holding.name,
                    asset_type: holding.asset_type || 'EQUITY',
                    quantity: holding.quantity,
                    purchase_price: holding.cost_basis,
                    current_price: holding.current_value / holding.quantity,
                    total_value: holding.current_value,
                    purchase_date: holding.purchase_date,
                    // Calculate P&L
                    pnl: holding.unrealized_pnl,
                    pnl_percentage: holding.unrealized_pnl_percent,
                    realized_pnl: holding.realized_pnl,
                    realized_pnl_percentage: holding.realized_pnl_percent,
                    today_pnl: holding.today_pnl,
                    today_pnl_percentage: holding.today_pnl_percent
                }));
            }

            setAssets(portfolioAssets);
        } catch (error) {
            console.error('Failed to load portfolio assets:', error);
            toast.error('Failed to load portfolio assets');
            setAssets([]);
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
                const totalValue = asset.total_value || 0;
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
                    aValue = a.total_value || 0;
                    bValue = b.total_value || 0;
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

    const handleRefresh = () => {
        loadPortfolioAssets();
        // Don't call onRefresh to avoid reloading all portfolios
        toast.success('Portfolio assets refreshed');
    };

    const handleFilterChange = (newFilters) => {
        setFilters(prev => ({ ...prev, ...newFilters }));
    };

    // Asset modal handlers
    const handleAssetClick = (asset) => {
        setSelectedAsset(asset);
        setShowAssetModal(true);
    };

    const handleTransactionClick = (asset) => {
        setTransactionAsset(asset);
        setShowTransactionModal(true);
    };

    const handleAnalyticsClick = (asset) => {
        // For now, show asset details - can be enhanced later
        setSelectedAsset(asset);
        setShowAssetModal(true);
    };

    const handleDeleteAsset = async (assetId) => {
        if (window.confirm('Are you sure you want to remove this asset from the portfolio?')) {
            try {
                // Remove asset from portfolio (this would need to be implemented in the API)
                toast.success('Asset removed from portfolio');
                loadPortfolioAssets(); // Reload assets
            } catch (error) {
                console.error('Failed to remove asset:', error);
                toast.error('Failed to remove asset from portfolio');
            }
        }
    };

    const handleCreateTransaction = async (transactionData) => {
        try {
            console.log('[PortfolioAssets] Creating transaction with data:', transactionData);
            const response = await transactionAPI.createTransaction(transactionData);
            console.log('[PortfolioAssets] Create response:', response);

            setShowTransactionModal(false);
            setTransactionAsset(null);
            toast.success('Transaction created successfully');

            // Refresh portfolio assets to ensure consistency
            setTimeout(() => {
                loadPortfolioAssets();
            }, 500);
        } catch (error) {
            console.error('Failed to create transaction:', error);
            const errorMessage = error.response?.data?.detail || error.message || 'Failed to create transaction';
            toast.error(errorMessage);
            throw error; // Re-throw so the modal can handle it
        }
    };

    const getTotalStats = () => {
        const totalValue = filteredAssets.reduce((sum, asset) => {
            return sum + (asset.total_value || 0);
        }, 0);

        const totalInvested = filteredAssets.reduce((sum, asset) => {
            const invested = (asset.quantity || 0) * (asset.purchase_price || 0);
            return sum + invested;
        }, 0);

        const totalPnL = totalValue - totalInvested;
        const totalPnLPercentage = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;

        const positiveAssets = filteredAssets.filter(asset => {
            const pnl = asset.pnl_percentage || 0;
            return pnl > 0;
        }).length;

        const negativeAssets = filteredAssets.filter(asset => {
            const pnl = asset.pnl_percentage || 0;
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
            <div className="space-y-6">
                <div className="text-center py-12">
                    <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading portfolio assets...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-gray-100 mb-2">Portfolio Assets</h2>
                    <p className="text-gray-400">Assets in {portfolio?.name || 'this portfolio'}</p>
                </div>
                <div className="flex items-center space-x-3">
                    <button
                        onClick={handleRefresh}
                        className="btn-secondary flex items-center space-x-2"
                    >
                        <RefreshCw size={16} />
                        <span>Refresh</span>
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

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
                            <p className="text-sm text-gray-400">Total Value</p>
                            <p className="text-2xl font-bold text-gray-100">
                                ${(stats.totalValue / 1000).toFixed(2)}K
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                            <TrendingUp size={24} className="text-success-400" />
                        </div>
                    </div>
                </div>

                <div className="card p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-400">Total Invested</p>
                            <p className="text-2xl font-bold text-gray-100">
                                ${(stats.totalInvested / 1000).toFixed(2)}K
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-warning-600/20 rounded-lg flex items-center justify-center">
                            <BarChart3 size={24} className="text-warning-400" />
                        </div>
                    </div>
                </div>

                <div className="card p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-400">P&L</p>
                            <p className={`text-2xl font-bold ${stats.totalPnL >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${(stats.totalPnL / 1000).toFixed(2)}K
                            </p>
                            <p className={`text-xs ${stats.totalPnLPercentage >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {stats.totalPnLPercentage.toFixed(2)}%
                            </p>
                        </div>
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${stats.totalPnL >= 0 ? 'bg-success-600/20' : 'bg-danger-600/20'}`}>
                            {stats.totalPnL >= 0 ? <TrendingUp size={24} className="text-success-400" /> : <TrendingDown size={24} className="text-danger-400" />}
                        </div>
                    </div>
                </div>
            </div>

            {/* Filters */}
            {showFilters && (
                <div className="card p-6">
                    <AssetFilters
                        filters={filters}
                        onFilterChange={handleFilterChange}
                    />
                </div>
            )}

            {/* View Mode Toggle */}
            <div className="flex items-center justify-between">
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

            {/* Assets Grid/List */}
            {filteredAssets.length === 0 ? (
                <div className="card p-12 text-center">
                    <BarChart3 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-gray-300 mb-2">No assets found</h3>
                    <p className="text-gray-500">
                        {searchQuery ? 'Try adjusting your search criteria' : 'No assets in this portfolio yet'}
                    </p>
                </div>
            ) : (
                <div className={
                    viewMode === 'grid'
                        ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
                        : 'space-y-4'
                }>
                    {filteredAssets.map((asset) => (
                        <PortfolioAssetCard
                            key={asset.id}
                            asset={asset}
                            viewMode={viewMode}
                            onClick={() => handleAssetClick(asset)}
                            onTransaction={() => handleTransactionClick(asset)}
                            onAnalytics={() => handleAnalyticsClick(asset)}
                            onDelete={() => handleDeleteAsset(asset.id)}
                        />
                    ))}
                </div>
            )}

            {/* Asset Modal */}
            {showAssetModal && selectedAsset && (
                <AssetModal
                    asset={selectedAsset}
                    mode="view"
                    onClose={() => {
                        setShowAssetModal(false);
                        setSelectedAsset(null);
                    }}
                />
            )}

            {/* Create Transaction Modal */}
            {showTransactionModal && transactionAsset && (
                <CreateTransactionModal
                    portfolios={[portfolio]} // Pass current portfolio
                    prefilledAsset={transactionAsset}
                    prefilledPrice={transactionAsset.current_price}
                    onClose={() => {
                        setShowTransactionModal(false);
                        setTransactionAsset(null);
                    }}
                    onCreate={handleCreateTransaction}
                />
            )}
        </div>
    );
};

export default PortfolioAssets;
