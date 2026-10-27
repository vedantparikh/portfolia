import { Filter, X } from 'lucide-react';

// `hidden` lets a page drop filters its data source cannot honour
const AssetFilters = ({ filters, onFilterChange, hidden = [] }) => {
    const categories = [
        { value: 'all', label: 'All Categories' },
        { value: 'cryptocurrency', label: 'Cryptocurrency' },
        { value: 'stock', label: 'Stocks' },
        { value: 'commodity', label: 'Commodities' },
        { value: 'forex', label: 'Forex' },
        { value: 'etf', label: 'ETFs' },
        { value: 'bond', label: 'Bonds' },
        { value: 'real_estate', label: 'Real Estate' },
        { value: 'mutual_fund', label: 'Mutual Funds' },
        { value: 'index_fund', label: 'Index Funds' }
    ];

    const priceRanges = [
        { value: 'all', label: 'All Prices' },
        { value: '0-1', label: 'Under $1' },
        { value: '1-10', label: '$1 - $10' },
        { value: '10-100', label: '$10 - $100' },
        { value: '100-1000', label: '$100 - $1,000' },
        { value: '1000-', label: 'Over $1,000' }
    ];

    const valueRanges = [
        { value: 'all', label: 'All Values' },
        { value: '0-100', label: 'Under $100' },
        { value: '100-1000', label: '$100 - $1,000' },
        { value: '1000-10000', label: '$1,000 - $10,000' },
        { value: '10000-', label: 'Over $10,000' }
    ];

    const changeRanges = [
        { value: 'all', label: 'All Changes' },
        { value: 'positive', label: 'Gainers' },
        { value: 'negative', label: 'Losers' },
        { value: 'stable', label: 'Stable' }
    ];

    const marketCapRanges = [
        { value: 'all', label: 'All Market Caps' },
        { value: '0-1e6', label: 'Under $1M' },
        { value: '1e6-1e9', label: '$1M - $1B' },
        { value: '1e9-1e12', label: '$1B - $1T' },
        { value: '1e12-', label: 'Over $1T' }
    ];

    const sortOptions = [
        { value: 'symbol', label: 'Symbol' },
        { value: 'name', label: 'Name' },
        { value: 'quantity', label: 'Quantity' },
        { value: 'purchase_price', label: 'Purchase Price' },
        { value: 'current_price', label: 'Current Price' },
        { value: 'total_value', label: 'Total Value' },
        { value: 'market_cap', label: 'Market Cap' },
        { value: 'volume_24h', label: '24h Volume' },
        { value: 'price_change_percentage_24h', label: '24h Change %' }
    ];

    const sortOrders = [
        { value: 'desc', label: 'Descending' },
        { value: 'asc', label: 'Ascending' }
    ];

    const handleFilterChange = (key, value) => {
        onFilterChange({ [key]: value });
    };

    const clearFilters = () => {
        onFilterChange({
            category: 'all',
            priceRange: 'all',
            valueRange: 'all',
            changeRange: 'all',
            marketCapRange: 'all',
            sortBy: 'symbol',
            sortOrder: 'asc'
        });
    };

    const hasActiveFilters = () => {
        return filters.category !== 'all' ||
            filters.priceRange !== 'all' ||
            filters.valueRange !== 'all' ||
            filters.changeRange !== 'all' ||
            filters.marketCapRange !== 'all' ||
            filters.sortBy !== 'symbol' ||
            filters.sortOrder !== 'asc';
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <Filter size={20} className="text-primary-400" />
                    <h3 className="text-lg font-semibold text-gray-100">Filters</h3>
                </div>
                {hasActiveFilters() && (
                    <button
                        onClick={clearFilters}
                        className="text-sm text-primary-400 hover:text-primary-300 flex items-center space-x-1"
                    >
                        <X size={16} />
                        <span>Clear all</span>
                    </button>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {/* Category Filter */}
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Category
                    </label>
                    <select
                        value={filters.category}
                        onChange={(e) => handleFilterChange('category', e.target.value)}
                        className="input-field w-full"
                    >
                        {categories.map((category) => (
                            <option key={category.value} value={category.value}>
                                {category.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Price Range Filter */}
                {!hidden.includes('priceRange') && (
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Price Range
                    </label>
                    <select
                        value={filters.priceRange}
                        onChange={(e) => handleFilterChange('priceRange', e.target.value)}
                        className="input-field w-full"
                    >
                        {priceRanges.map((range) => (
                            <option key={range.value} value={range.value}>
                                {range.label}
                            </option>
                        ))}
                    </select>
                </div>
                )}

                {/* Value Range Filter */}
                {!hidden.includes('valueRange') && (
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Total Value
                    </label>
                    <select
                        value={filters.valueRange || 'all'}
                        onChange={(e) => handleFilterChange('valueRange', e.target.value)}
                        className="input-field w-full"
                    >
                        {valueRanges.map((range) => (
                            <option key={range.value} value={range.value}>
                                {range.label}
                            </option>
                        ))}
                    </select>
                </div>
                )}

                {/* Change Range Filter */}
                {!hidden.includes('changeRange') && (
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        24h Change
                    </label>
                    <select
                        value={filters.changeRange}
                        onChange={(e) => handleFilterChange('changeRange', e.target.value)}
                        className="input-field w-full"
                    >
                        {changeRanges.map((range) => (
                            <option key={range.value} value={range.value}>
                                {range.label}
                            </option>
                        ))}
                    </select>
                </div>
                )}

                {/* Market Cap Range Filter */}
                {!hidden.includes('marketCapRange') && (
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Market Cap
                    </label>
                    <select
                        value={filters.marketCapRange || 'all'}
                        onChange={(e) => handleFilterChange('marketCapRange', e.target.value)}
                        className="input-field w-full"
                    >
                        {marketCapRanges.map((range) => (
                            <option key={range.value} value={range.value}>
                                {range.label}
                            </option>
                        ))}
                    </select>
                </div>
                )}

                {/* Sort By Filter */}
                {!hidden.includes('sort') && (
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Sort By
                    </label>
                    <select
                        value={filters.sortBy}
                        onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                        className="input-field w-full"
                    >
                        {sortOptions.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                </div>
                )}

            </div>

            {/* Sort Order */}
            {!hidden.includes('sort') && (
            <div className="flex items-center space-x-4">
                <label className="block text-sm font-medium text-gray-300">
                    Sort Order:
                </label>
                <div className="flex space-x-2">
                    {sortOrders.map((order) => (
                        <button
                            key={order.value}
                            onClick={() => handleFilterChange('sortOrder', order.value)}
                            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${filters.sortOrder === order.value
                                ? 'bg-primary-600 text-white'
                                : 'bg-dark-700 text-gray-300 hover:bg-dark-600'
                                }`}
                        >
                            {order.label}
                        </button>
                    ))}
                </div>
            </div>
            )}

            {/* Active Filters Display */}
            {hasActiveFilters() && (
                <div className="flex flex-wrap gap-2">
                    <span className="text-sm text-gray-400">Active filters:</span>
                    {filters.category !== 'all' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            {categories.find(c => c.value === filters.category)?.label}
                        </span>
                    )}
                    {filters.priceRange !== 'all' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            {priceRanges.find(r => r.value === filters.priceRange)?.label}
                        </span>
                    )}
                    {filters.changeRange !== 'all' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            {changeRanges.find(r => r.value === filters.changeRange)?.label}
                        </span>
                    )}
                    {!hidden.includes('sort') && filters.sortBy !== 'symbol' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            Sort: {sortOptions.find(o => o.value === filters.sortBy)?.label}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
};

export default AssetFilters;
