import { Search, TrendingUp } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { marketAPI } from '../../services/api';

const SymbolSearch = ({
    value,
    onChange,
    onSelect,
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
            setShowSuggestionsDropdown(true);
        } catch (error) {
            console.error('Failed to search symbols:', error);
            setSuggestions([]);
            setShowSuggestionsDropdown(false);
        } finally {
            setSearching(false);
        }
    };

    const handleSuggestionClick = (suggestion) => {
        if (onSelect) {
            onSelect(suggestion);
        }
        setShowSuggestionsDropdown(false);
    };

    const handleFocus = () => {
        if (value && suggestions.length > 0) {
            setShowSuggestionsDropdown(true);
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
                    <div className="absolute top-full left-0 right-0 mt-1 bg-dark-800 border border-dark-600 rounded-lg shadow-lg z-50 max-h-48 overflow-y-auto">
                        {searching && (
                            <div className="px-4 py-3 text-gray-400 text-sm flex items-center space-x-2">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-500"></div>
                                <span>Searching...</span>
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
                                        {suggestion.longname || suggestion.shortname || suggestion.name}
                                    </div>
                                    <div className="text-xs text-gray-600">
                                        {suggestion.exchDisp} • {suggestion.typeDisp}
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
