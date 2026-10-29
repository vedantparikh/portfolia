import { Filter, X } from 'lucide-react';
import { formatCurrency } from '../../utils/formatters.jsx';

const usd = (n) =>
    formatCurrency(n, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
        notation: n >= 1e6 ? 'compact' : 'standard',
    });

const range = (value, low, high) => ({
    value,
    label: low === null ? `Under ${usd(high)}` : high === null ? `Over ${usd(low)}` : `${usd(low)} - ${usd(high)}`,
});

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
        range('0-1', null, 1),
        range('1-10', 1, 10),
        range('10-100', 10, 100),
        range('100-1000', 100, 1000),
        range('1000-', 1000, null)
    ];

    const valueRanges = [
        { value: 'all', label: 'All Values' },
        range('0-100', null, 100),
        range('100-1000', 100, 1000),
        range('1000-10000', 1000, 10000),
        range('10000-', 10000, null)
    ];

    const changeRanges = [
        { value: 'all', label: 'All Changes' },
        { value: 'positive', label: 'Gainers' },
        { value: 'negative', label: 'Losers' },
        { value: 'stable', label: 'Stable' }
    ];

    const marketCapRanges = [
        { value: 'all', label: 'All Market Caps' },
        range('0-1e6', null, 1e6),
        range('1e6-1e9', 1e6, 1e9),
        range('1e9-1e12', 1e9, 1e12),
        range('1e12-', 1e12, null)
    ];

    const sortOptions = [
        { value: 'symbol', label: 'Symbol' },
        { value: 'name', label: 'Name' },
        { value: 'created_at', label: 'Date Added' },
        { value: 'current_price', label: 'Current Price' },
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
