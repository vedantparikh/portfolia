import { Filter, X } from 'lucide-react';
import React from 'react';
import transactionTypes from '../../utils/transactionTypes';

const TransactionFilters = ({ filters, portfolios, onFilterChange }) => {

    const dateRanges = [
        { value: 'all', label: 'All Time' },
        { value: 'today', label: 'Today' },
        { value: 'week', label: 'This Week' },
        { value: 'month', label: 'This Month' },
        { value: 'quarter', label: 'This Quarter' },
        { value: 'year', label: 'This Year' }
    ];

    const sortOptions = [
        { value: 'created_at', label: 'Date' },
        { value: 'amount', label: 'Amount' },
        { value: 'symbol', label: 'Symbol' },
        { value: 'type', label: 'Type' }
    ];

    const sortOrders = [
        { value: 'desc', label: 'Newest First' },
        { value: 'asc', label: 'Oldest First' }
    ];

    const handleFilterChange = (key, value) => {
        onFilterChange({ ...filters, [key]: value });
    };

    const clearFilters = () => {
        onFilterChange({
            portfolio: 'all',
            type: 'all',
            dateRange: 'all',
            sortBy: 'created_at',
            sortOrder: 'desc'
        });
    };

    const hasActiveFilters = () => {
        return filters.portfolio !== 'all' ||
            filters.type !== 'all' ||
            filters.dateRange !== 'all' ||
            filters.sortBy !== 'created_at' ||
            filters.sortOrder !== 'desc';
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

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Portfolio Filter */}
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Portfolio
                    </label>
                    <select
                        value={filters.portfolio}
                        onChange={(e) => handleFilterChange('portfolio', e.target.value)}
                        className="input-field w-full"
                    >
                        <option value="all">All Portfolios</option>
                        {portfolios.map((portfolio) => (
                            <option key={portfolio.id} value={portfolio.id}>
                                {portfolio.name}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Transaction Type Filter */}
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Transaction Type
                    </label>
                    <select
                        value={filters.type}
                        onChange={(e) => handleFilterChange('type', e.target.value)}
                        className="input-field w-full"
                    >
                        {transactionTypes.map((type) => (
                            <option key={type.value} value={type.value}>
                                {type.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Date Range Filter */}
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                        Date Range
                    </label>
                    <select
                        value={filters.dateRange}
                        onChange={(e) => handleFilterChange('dateRange', e.target.value)}
                        className="input-field w-full"
                    >
                        {dateRanges.map((range) => (
                            <option key={range.value} value={range.value}>
                                {range.label}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Sort By Filter */}
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
            </div>

            {/* Sort Order */}
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

            {/* Active Filters Display */}
            {hasActiveFilters() && (
                <div className="flex flex-wrap gap-2">
                    <span className="text-sm text-gray-400">Active filters:</span>
                    {filters.portfolio !== 'all' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            {portfolios.find(p => p.id === parseInt(filters.portfolio))?.name || 'Portfolio'}
                        </span>
                    )}
                    {filters.type !== 'all' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            {transactionTypes.find(t => t.value === filters.type)?.label}
                        </span>
                    )}
                    {filters.dateRange !== 'all' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            {dateRanges.find(r => r.value === filters.dateRange)?.label}
                        </span>
                    )}
                    {filters.sortBy !== 'created_at' && (
                        <span className="px-2 py-1 bg-primary-600/20 text-primary-400 text-xs rounded-full">
                            Sort: {sortOptions.find(o => o.value === filters.sortBy)?.label}
                        </span>
                    )}
                </div>
            )}
        </div>
    );
};

export default TransactionFilters;
