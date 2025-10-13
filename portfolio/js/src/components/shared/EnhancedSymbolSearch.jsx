import { Database, ExternalLink, Plus, Search, TrendingUp } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { assetAPI, marketAPI } from '../../services/api';
import LoadingSpinner from './LoadingSpinner';

const EnhancedSymbolSearch = ({
    value,
    onChange,
    onSelect,
    onPriceUpdate,
    placeholder = "e.g., AAPL, BTC",
    className = "",
    disabled = false,
    showSuggestions = true,
    autoFocus = false
}) => {
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestionsDropdown, setShowSuggestionsDropdown] = useState(false);
    const [searching, setSearching] = useState(false);
    const [searchType, setSearchType] = useState('all'); // 'all', 'assets', 'symbols'
    const [existingAssets, setExistingAssets] = useState([]);
    const [symbolSearchResults, setSymbolSearchResults] = useState([]);
    const debounceTimeoutRef = useRef(null);

    // Cleanup debounce timeout on unmount
    useEffect(() => {
        return () => {
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }
        };
    }, []);

    // Close suggestions when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (showSuggestionsDropdown && !event.target.closest('.enhanced-symbol-search-container')) {
                setShowSuggestionsDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [showSuggestionsDropdown]);

    const handleInputChange = (e) => {
        const inputValue = e.target.value;
        onChange(inputValue);
        handleSymbolSearch(inputValue);
    };

    const handleSymbolSearch = (value) => {
        // Clear existing timeout
        if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
        }

        // Set new timeout for debounced search
        debounceTimeoutRef.current = setTimeout(async () => {
            await performSymbolSearch(value);
        }, 400);
    };

    const performSymbolSearch = async (value) => {
        if (!showSuggestions || value.trim().length < 2) {
            setSuggestions([]);
            setShowSuggestionsDropdown(false);
            return;
        }

        setSearching(true);
        try {
            // Search both existing assets and external symbols in parallel
            const [assetsResponse, symbolsResponse] = await Promise.allSettled([
                searchExistingAssets(value.trim()),
                searchExternalSymbols(value.trim())
            ]);

            const existingAssets = assetsResponse.status === 'fulfilled' ? assetsResponse.value : [];
            const symbolResults = symbolsResponse.status === 'fulfilled' ? symbolsResponse.value : [];

            setExistingAssets(existingAssets);
            setSymbolSearchResults(symbolResults);

            // Combine and format results
            const combinedSuggestions = [
                ...existingAssets.map(asset => ({
                    ...asset,
                    type: 'existing_asset',
                    source: 'Your Assets',
                    icon: Database
                })),
                ...symbolResults.map(symbol => ({
                    ...symbol,
                    type: 'external_symbol',
                    source: 'Market Search',
                    icon: ExternalLink
                }))
            ];

            setSuggestions(combinedSuggestions);
            setShowSuggestionsDropdown(true);
        } catch (error) {
            console.error('Failed to search symbols:', error);
            setSuggestions([]);
            setShowSuggestionsDropdown(false);
        } finally {
            setSearching(false);
        }
    };

    const searchExistingAssets = async (query) => {
        try {
            const response = await assetAPI.searchAssets(query);
            return response.results || [];
        } catch (error) {
            console.error('Failed to search existing assets:', error);
            return [];
        }
    };

    const searchExternalSymbols = async (query) => {
        try {
            const response = await marketAPI.searchSymbols(query);
            return response.results || [];
        } catch (error) {
            console.error('Failed to search external symbols:', error);
            return [];
        }
    };

    const handleSuggestionClick = async (suggestion) => {
        if (onSelect) {
            onSelect(suggestion);
        }

        // Fetch current price if callback is provided
        if (onPriceUpdate) {
            try {
                const priceData = await marketAPI.getCurrentPrice(suggestion.symbol);
                onPriceUpdate(priceData);
            } catch (error) {
                console.error('Failed to fetch current price:', error);
                // Still allow selection even if price fetch fails
            }
        }

        setShowSuggestionsDropdown(false);
    };

    const handleCreateAsset = async (symbolData) => {
        try {
            const assetData = {
                symbol: symbolData.symbol,
                name: symbolData.long_name || symbolData.short_name || symbolData.longname || symbolData.shortname || symbolData.name || symbolData.symbol,
                asset_type: symbolData.quote_type || 'EQUITY',
                exchange: symbolData.exchange,
                sector: symbolData.sector,
                industry: symbolData.industry,
                country: symbolData.country,
                description: `${symbolData.long_name || symbolData.short_name || symbolData.longname || symbolData.shortname || symbolData.name} - ${symbolData.exchange || symbolData.exchDisp}`,
                is_active: true
            };

            const newAsset = await assetAPI.createAsset(assetData);

            // Update the suggestion to show it's now an existing asset
            const updatedSuggestion = {
                ...symbolData,
                type: 'existing_asset',
                source: 'Your Assets',
                icon: Database,
                id: newAsset.id
            };

            // Update suggestions to reflect the new asset
            setSuggestions(prev =>
                prev.map(s => s.symbol === symbolData.symbol ? updatedSuggestion : s)
            );

            // Select the newly created asset
            if (onSelect) {
                onSelect(updatedSuggestion);
            }

            setShowSuggestionsDropdown(false);
        } catch (error) {
            console.error('Failed to create asset:', error);
            // You might want to show a toast notification here
        }
    };

    const handleFocus = () => {
        if (value && suggestions.length > 0) {
            setShowSuggestionsDropdown(true);
        }
    };

    const getSuggestionIcon = (suggestion) => {
        const IconComponent = suggestion.icon || TrendingUp;
        return <IconComponent size={16} className="text-primary-400" />;
    };

    const getSuggestionBadge = (suggestion) => {
        if (suggestion.type === 'existing_asset') {
            return (
                <span className="px-2 py-1 text-xs bg-green-600/20 text-green-400 rounded-full">
                    Your Asset
                </span>
            );
        } else {
            return (
                <span className="px-2 py-1 text-xs bg-blue-600/20 text-blue-400 rounded-full">
                    Market
                </span>
            );
        }
    };

    return (
        <div className={`relative enhanced-symbol-search-container ${className}`}>
            <div className="relative">
                <input
                    type="text"
                    value={value}
                    onChange={handleInputChange}
                    onFocus={handleFocus}
                    placeholder={placeholder}
                    disabled={disabled}
                    autoFocus={autoFocus}
                    className={`w-full pl-10 pr-4 py-3 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
                />
                <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />

                {/* Search Type Filter */}
                {showSuggestions && value.trim().length >= 2 && (
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex space-x-1">
                        <button
                            type="button"
                            onClick={() => setSearchType('all')}
                            className={`px-2 py-1 text-xs rounded ${searchType === 'all' ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
                        >
                            All
                        </button>
                        <button
                            type="button"
                            onClick={() => setSearchType('assets')}
                            className={`px-2 py-1 text-xs rounded ${searchType === 'assets' ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
                        >
                            Assets
                        </button>
                        <button
                            type="button"
                            onClick={() => setSearchType('symbols')}
                            className={`px-2 py-1 text-xs rounded ${searchType === 'symbols' ? 'bg-primary-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'}`}
                        >
                            Market
                        </button>
                    </div>
                )}
            </div>

            {/* Suggestions Dropdown */}
            {showSuggestions && showSuggestionsDropdown && suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-dark-800 border border-dark-600 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
                    {searching && (
                        <div className="px-4 py-3 text-gray-400 text-sm">
                            <LoadingSpinner type="ticker" size="sm" color="primary" text="Searching..." />
                        </div>
                    )}

                    {/* Existing Assets Section */}
                    {searchType === 'all' || searchType === 'assets' ? (
                        existingAssets.length > 0 && (
                            <div className="px-3 py-2 bg-dark-700/50 text-xs text-gray-400 font-medium">
                                Your Assets ({existingAssets.length})
                            </div>
                        )
                    ) : null}

                    {suggestions
                        .filter(suggestion => searchType === 'all' ||
                            (searchType === 'assets' && suggestion.type === 'existing_asset') ||
                            (searchType === 'symbols' && suggestion.type === 'external_symbol')
                        )
                        .map((suggestion, index) => (
                            <div key={`${suggestion.type}-${index}`} className="border-b border-dark-700 last:border-b-0">
                                <button
                                    type="button"
                                    onClick={() => handleSuggestionClick(suggestion)}
                                    className="w-full flex items-center space-x-3 px-4 py-3 text-left text-gray-300 hover:bg-dark-700 transition-colors"
                                >
                                    {getSuggestionIcon(suggestion)}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2">
                                            <div className="font-mono text-sm font-medium">{suggestion.symbol}</div>
                                            {getSuggestionBadge(suggestion)}
                                        </div>
                                        <div className="text-xs text-gray-500 truncate">
                                            {suggestion.long_name || suggestion.short_name || suggestion.longname || suggestion.shortname || suggestion.name || suggestion.asset_name}
                                        </div>
                                        <div className="text-xs text-gray-600">
                                            {suggestion.exchange || suggestion.exchDisp} • {suggestion.quote_type || suggestion.typeDisp || suggestion.asset_type}
                                        </div>
                                    </div>
                                    {suggestion.type === 'external_symbol' && (
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleCreateAsset(suggestion);
                                            }}
                                            className="flex items-center space-x-1 px-2 py-1 text-xs bg-primary-600/20 text-primary-400 rounded hover:bg-primary-600/30 transition-colors"
                                        >
                                            <Plus size={12} />
                                            <span>Add</span>
                                        </button>
                                    )}
                                </button>
                            </div>
                        ))}

                    {suggestions.length === 0 && !searching && (
                        <div className="px-4 py-3 text-gray-400 text-sm text-center">
                            No results found for "{value}"
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default EnhancedSymbolSearch;
