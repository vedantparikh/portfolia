import { Database, Search } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { assetAPI } from '../../services/api';
import LoadingSpinner from './LoadingSpinner';

const AssetSymbolSearch = ({
    value,
    onChange,
    onSelect,
    placeholder = "Search assets...",
    disabled = false,
    showSuggestions = true
}) => {
    const [suggestions, setSuggestions] = useState([]);
    const [showSuggestionsDropdown, setShowSuggestionsDropdown] = useState(false);
    const [searching, setSearching] = useState(false);
    const debounceTimeoutRef = useRef(null);
    const inputRef = useRef(null);
    const dropdownRef = useRef(null);

    // Debounced search function
    const searchAssets = async (query) => {
        if (!query || query.length < 2) {
            setSuggestions([]);
            return;
        }

        try {
            setSearching(true);
            const response = await assetAPI.searchAssets(query);
            const assets = response.assets || [];

            // Format assets for display
            const formattedAssets = assets.map(asset => ({
                ...asset,
                type: 'existing_asset',
                source: 'Your Assets',
                icon: Database
            }));

            setSuggestions(formattedAssets);
        } catch (error) {
            console.error('Failed to search assets:', error);
            setSuggestions([]);
        } finally {
            setSearching(false);
        }
    };

    // Handle input change with debouncing
    const handleInputChange = (e) => {
        const query = e.target.value;
        onChange(query);

        // Clear existing timeout
        if (debounceTimeoutRef.current) {
            clearTimeout(debounceTimeoutRef.current);
        }

        // Set new timeout
        debounceTimeoutRef.current = setTimeout(() => {
            if (showSuggestions) {
                searchAssets(query);
            }
        }, 300);
    };

    // Handle suggestion click
    const handleSuggestionClick = (asset) => {
        if (onSelect) {
            onSelect(asset);
        }
        setShowSuggestionsDropdown(false);
    };

    // Handle input focus
    const handleFocus = () => {
        if (value && suggestions.length > 0) {
            setShowSuggestionsDropdown(true);
        }
    };

    // Handle input blur
    const handleBlur = () => {
        // Delay hiding to allow clicking on suggestions
        setTimeout(() => {
            setShowSuggestionsDropdown(false);
        }, 200);
    };

    // Handle key navigation
    const handleKeyDown = (e) => {
        if (!showSuggestionsDropdown || suggestions.length === 0) return;

        const currentIndex = suggestions.findIndex(s => s.symbol === value);

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                const nextIndex = currentIndex < suggestions.length - 1 ? currentIndex + 1 : 0;
                onChange(suggestions[nextIndex].symbol);
                break;
            case 'ArrowUp':
                e.preventDefault();
                const prevIndex = currentIndex > 0 ? currentIndex - 1 : suggestions.length - 1;
                onChange(suggestions[prevIndex].symbol);
                break;
            case 'Enter':
                e.preventDefault();
                if (currentIndex >= 0) {
                    handleSuggestionClick(suggestions[currentIndex]);
                }
                break;
            case 'Escape':
                setShowSuggestionsDropdown(false);
                break;
        }
    };

    // Get suggestion icon
    const getSuggestionIcon = (suggestion) => {
        const IconComponent = suggestion.icon || Database;
        return (
            <div className="w-8 h-8 bg-primary-600/20 rounded-lg flex items-center justify-center">
                <IconComponent size={16} className="text-primary-400" />
            </div>
        );
    };

    // Get suggestion badge
    const getSuggestionBadge = (suggestion) => {
        return (
            <span className="text-xs px-2 py-1 bg-primary-600/20 text-primary-400 rounded">
                {suggestion.source}
            </span>
        );
    };

    // Cleanup timeout on unmount
    useEffect(() => {
        return () => {
            if (debounceTimeoutRef.current) {
                clearTimeout(debounceTimeoutRef.current);
            }
        };
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target) &&
                inputRef.current &&
                !inputRef.current.contains(event.target)
            ) {
                setShowSuggestionsDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    return (
        <div className="relative">
            {/* Input Field */}
            <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                    ref={inputRef}
                    type="text"
                    value={value}
                    onChange={handleInputChange}
                    onFocus={handleFocus}
                    onBlur={handleBlur}
                    onKeyDown={handleKeyDown}
                    placeholder={placeholder}
                    disabled={disabled}
                    className="input-field w-full pl-10 pr-4 py-3"
                />
                {searching && (
                    <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                        <LoadingSpinner type="ticker" size="sm" />
                    </div>
                )}
            </div>

            {/* Suggestions Dropdown */}
            {showSuggestionsDropdown && suggestions.length > 0 && (
                <div
                    ref={dropdownRef}
                    className="absolute z-50 w-full mt-1 bg-dark-800 border border-dark-600 rounded-lg shadow-lg max-h-80 overflow-y-auto"
                >
                    {suggestions.map((suggestion, index) => (
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
                                        {suggestion.name}
                                    </div>
                                    <div className="text-xs text-gray-600">
                                        {suggestion.exchange} • {suggestion.asset_type}
                                    </div>
                                </div>
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* No Results */}
            {showSuggestionsDropdown && suggestions.length === 0 && !searching && value && value.length >= 2 && (
                <div className="absolute z-50 w-full mt-1 bg-dark-800 border border-dark-600 rounded-lg shadow-lg">
                    <div className="px-4 py-6 text-center">
                        <Database size={32} className="mx-auto mb-3 text-gray-600" />
                        <p className="text-gray-400 text-sm mb-2">No assets found</p>
                        <p className="text-gray-500 text-xs">
                            Asset "{value}" doesn't exist. Please add it first in the Assets section.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AssetSymbolSearch;
