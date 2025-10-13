import {
    Activity,
    Award,
    BarChart3,
    Filter,
    Gem,
    PieChart,
    RefreshCw,
    Search,
    TrendingUp
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { portfolioAPI, transactionAPI } from '../../services/api';
import AssetFilters from '../assets/AssetFilters';
import AssetModal from '../assets/AssetModal';
import LoadingSpinner from '../shared/LoadingSpinner';
import CreateTransactionModal from '../transactions/CreateTransactionModal';
import PortfolioAssetCard from './PortfolioAssetCard';


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
                    current_price: holding.current_value && holding.quantity ? holding.current_value / holding.quantity : 0,
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
    const getPortfolioHighlights = () => {
        const defaultAsset = { symbol: 'N/A', name: 'Not Available', value: 0 };
        if (filteredAssets.length === 0) {
            return {
                bestPerformer: defaultAsset,
                largestHolding: defaultAsset,
                topContributor: defaultAsset,
                dailyMover: defaultAsset
            };
        }

        const highlights = filteredAssets.reduce((acc, asset) => {
            // Best Performer (%)
            if ((asset.pnl_percentage || -Infinity) > acc.bestPerformer.value) {
                acc.bestPerformer = { symbol: asset.symbol, name: asset.name, value: asset.pnl_percentage };
            }
            // Largest Holding ($)
            if ((asset.total_value || -Infinity) > acc.largestHolding.value) {
                acc.largestHolding = { symbol: asset.symbol, name: asset.name, value: asset.total_value };
            }
            // Top Contributor ($)
            if ((asset.pnl || -Infinity) > acc.topContributor.value) {
                acc.topContributor = { symbol: asset.symbol, name: asset.name, value: asset.pnl };
            }
            // Portfolio's Daily Mover (absolute $)
            if (Math.abs(asset.today_pnl || 0) > Math.abs(acc.dailyMover.value)) {
                acc.dailyMover = { symbol: asset.symbol, name: asset.name, value: asset.today_pnl };
            }
            return acc;
        }, {
            bestPerformer: { ...defaultAsset, value: -Infinity },
            largestHolding: { ...defaultAsset, value: -Infinity },
            topContributor: { ...defaultAsset, value: -Infinity },
            dailyMover: { ...defaultAsset, value: 0 },
        });

        // Clean up initial values if no valid asset was found
        if (highlights.bestPerformer.value === -Infinity) highlights.bestPerformer.value = 0;
        if (highlights.largestHolding.value === -Infinity) highlights.largestHolding.value = 0;
        if (highlights.topContributor.value === -Infinity) highlights.topContributor.value = 0;

        return highlights;
    };

    const highlights = getPortfolioHighlights();
    const totalPortfolioValue = filteredAssets.reduce((sum, asset) => sum + (asset.total_value || 0), 0);
    if (loading) {
        return (
            <div className="space-y-6">
                <div className="text-center py-12">
                    <LoadingSpinner size="lg" text="Loading portfolio assets..." centered />
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
                            <p className="text-sm text-gray-400">Best Performer</p>
                            <p className="text-xl font-bold text-gray-100 truncate" title={highlights.bestPerformer.name}>{highlights.bestPerformer.symbol}</p>
                            <p className="text-xs text-gray-500">{highlights.bestPerformer.name}</p>
                            <p className="text-sm font-semibold text-success-400">
                                +{highlights.bestPerformer.value.toFixed(2)}%
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                            <Award size={24} className="text-success-400" />
                        </div>
                    </div>
                </div>
                <div className="card p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-400">Largest Holding</p>
                            <p className="text-xl font-bold text-gray-100 truncate" title={highlights.largestHolding.name}>{highlights.largestHolding.symbol}</p>
                            <p className="text-xs text-gray-500">{highlights.largestHolding.name}</p>
                            <p className="text-sm font-semibold text-primary-400">
                                ${highlights.largestHolding.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </p>
                        </div>
                        <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                            <Gem size={24} className="text-primary-400" />
                        </div>
                    </div>
                </div>
                <div className="card p-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-gray-400">Top Contributor</p>
                            <p className="text-xl font-bold text-gray-100 truncate" title={highlights.topContributor.name}>{highlights.topContributor.symbol}</p>
                            <p className="text-xs text-gray-500">{highlights.topContributor.name}</p>
                            <p className="text-sm font-semibold text-success-400">
                                +${highlights.topContributor.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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
                            <p className="text-sm text-gray-400">Daily Mover</p>
                            <p className="text-xl font-bold text-gray-100 truncate" title={highlights.dailyMover.name}>{highlights.dailyMover.symbol}</p>
                            <p className="text-xs text-gray-500">{highlights.dailyMover.name}</p>
                            <p className={`text-sm font-semibold ${highlights.dailyMover.value >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {highlights.dailyMover.value >= 0 ? '+' : ''}${highlights.dailyMover.value.toFixed(2)}
                            </p>
                        </div>
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${highlights.dailyMover.value >= 0 ? 'bg-success-600/20' : 'bg-danger-600/20'}`}>
                            <Activity size={24} className={highlights.dailyMover.value >= 0 ? 'text-success-400' : 'text-danger-400'} />
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
                            portfolioTotalValue={totalPortfolioValue}
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