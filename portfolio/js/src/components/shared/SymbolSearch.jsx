import { Search, TrendingUp } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { marketAPI } from '../../services/api';
import LoadingSpinner from './LoadingSpinner';

const SymbolSearch = ({
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
            if (showSuggestionsDropdown && !event.target.closest('.symbol-search-container')) {
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
            const results = await marketAPI.searchSymbols(value.trim());
            setSuggestions(results || []);
            if (results && results.length > 0) {
                setShowSuggestionsDropdown(true);
            }
        } catch (error) {
            console.error('Failed to search symbols:', error);
            setSuggestions([]);
            setShowSuggestionsDropdown(false);
        } finally {
            setSearching(false);
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

    const handleFocus = () => {
        if (value && value.length >= 2 && suggestions.length > 0) {
            setShowSuggestionsDropdown(true);
        } else if (value && value.length >= 2) {
            // Trigger search if we have a value but no suggestions yet
            performSymbolSearch(value);
        }
    };

    return (
        <div className={`relative symbol-search-container ${className}`}>
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

                {/* Suggestions Dropdown */}
                {showSuggestions && showSuggestionsDropdown && suggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-dark-800 border border-dark-600 rounded-lg shadow-lg z-[60] max-h-48 overflow-y-auto">
                        {searching && (
                            <div className="px-4 py-3 text-gray-400 text-sm">
                                <LoadingSpinner size="sm" color="primary" text="Searching..." />
                            </div>
                        )}
                        {suggestions.map((suggestion, index) => (
                            <button
                                key={index}
                                type="button"
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="w-full flex items-center space-x-3 px-4 py-3 text-left text-gray-300 hover:bg-dark-700 transition-colors"
                            >
                                <TrendingUp size={16} className="text-primary-400" />
                                <div className="flex-1">
                                    <div className="font-mono text-sm">{suggestion.symbol}</div>
                                    <div className="text-xs text-gray-500 truncate">
                                        {suggestion.long_name || suggestion.short_name || suggestion.longname || suggestion.shortname || suggestion.name || suggestion.company_name ||
                                            (suggestion.sector && suggestion.industry ? `${suggestion.sector} - ${suggestion.industry}` : suggestion.sector || suggestion.industry) ||
                                            'No description available'}
                                    </div>
                                    <div className="text-xs text-gray-600">
                                        {(suggestion.exchange || suggestion.exchDisp || '')}
                                        {(suggestion.exchange || suggestion.exchDisp) && (suggestion.quote_type || suggestion.typeDisp || suggestion.type || suggestion.asset_type) && ' • '}
                                        {(suggestion.quote_type || suggestion.typeDisp || suggestion.type || suggestion.asset_type || '')}
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SymbolSearch;
