import { X } from 'lucide-react';
import { useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import { authUtils, marketAPI } from '../../services/api';
import { LoadingSpinner, SymbolSearch } from '../../components/shared';

const AddSymbolModal = ({ isOpen, onClose, onAdd }) => {
    const { isAuthenticated } = useAuth();
    const [symbol, setSymbol] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Popular symbols for quick access
    const popularSymbols = [
        'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
        'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'ARKK', 'BTC', 'ETH'
    ];

    const handleSubmit = (e) => {
        e.preventDefault();
        addSymbol(symbol);
    };

    const addSymbol = async (value) => {
        const ticker = value.trim().toUpperCase();
        if (!ticker) {
            setError('Please enter a symbol');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const symbolData = await fetchSymbolData(ticker);

            await onAdd(symbolData);
            handleClose();
            toast.success(`Added ${ticker} to watchlist`);
        } catch (error) {
            console.error('Failed to add symbol:', error);
            const errorMessage = error.response?.data?.message || error.message || 'Failed to add symbol';
            setError(errorMessage);
            toast.error(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setSymbol('');
        setLoading(false);
        setError('');
        onClose();
    };

    const handleSymbolChange = (value) => {
        setSymbol(value);
        setError(''); // Clear error when user types
    };

    const handleSymbolSelect = async (suggestion) => {
        setSymbol(suggestion.symbol);
        setError('');

        // Automatically add the symbol to watchlist when selected
        try {
            // Pass the complete symbol data to preserve all symbol information
            await onAdd(suggestion);
            handleClose();
            toast.success(`Added ${suggestion.symbol} to watchlist`);
        } catch (error) {
            console.error('Failed to add symbol:', error);
            const errorMessage = error.response?.data?.message || error.message || 'Failed to add symbol';
            setError(errorMessage);
            toast.error(errorMessage);
        }
    };
    // Function to fetch symbol data for popular symbols
    const fetchSymbolData = async (symbolString) => {
        try {
            // Check authentication before making API call
            if (!authUtils.isAuthenticated()) {
                console.warn('[AddSymbolModal] User not authenticated for symbol search');
                throw new Error('Please log in to search for symbols');
            }

            // Search for the symbol to get complete data
            const results = await marketAPI.searchSymbols(symbolString);

            // Find exact match or return first result
            const exactMatch = results.find(result =>
                result.symbol?.toUpperCase() === symbolString.toUpperCase()
            );

            if (exactMatch) {
                return exactMatch;
            } else if (results.length > 0) {
                return results[0];
            } else {
                // Fallback: create basic symbol object
                return {
                    symbol: symbolString.toUpperCase(),
                    name: symbolString.toUpperCase(),
                    short_name: symbolString.toUpperCase(),
                    shortname: symbolString.toUpperCase() // Keep old property for compatibility
                };
            }
        } catch (error) {
            console.error('Failed to fetch symbol data:', error);
            // Fallback: create basic symbol object
            return {
                symbol: symbolString.toUpperCase(),
                name: symbolString.toUpperCase(),
                short_name: symbolString.toUpperCase(),
                shortname: symbolString.toUpperCase() // Keep old property for compatibility
            };
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-dark-900 border border-dark-700 rounded-lg w-full max-w-md mx-4">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <h2 className="text-lg font-semibold text-gray-100">Add Symbol</h2>
                    <button
                        onClick={handleClose}
                        className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
                    >
                        <X size={20} className="text-gray-400" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Authentication Status */}
                    {!isAuthenticated && (
                        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-3">
                            <p className="text-red-400 text-sm">
                                ⚠️ You need to be logged in to search for symbols. Popular symbols are still available.
                            </p>
                        </div>
                    )}

                    {/* Symbol Input */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Stock Symbol *
                        </label>
                        <SymbolSearch
                            value={symbol}
                            onChange={handleSymbolChange}
                            onSelect={handleSymbolSelect}
                            placeholder="e.g., AAPL"
                            disabled={loading}
                            showSuggestions={isAuthenticated}
                        />

                        {/* Error Message */}
                        {error && (
                            <p className="mt-2 text-sm text-red-400">{error}</p>
                        )}
                    </div>

                    {/* Popular Symbols */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                            Popular Symbols
                        </label>
                        <div className="grid grid-cols-4 gap-2">
                            {popularSymbols.slice(0, 8).map((popSymbol) => (
                                <button
                                    key={popSymbol}
                                    type="button"
                                    onClick={() => {
                                        setSymbol(popSymbol);
                                        addSymbol(popSymbol);
                                    }}
                                    className="px-3 py-2 text-sm bg-dark-800 border border-dark-600 rounded-lg text-gray-300 hover:bg-dark-700 hover:border-primary-500 transition-colors font-mono"
                                >
                                    {popSymbol}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center justify-end space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
                            disabled={loading}
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !symbol.trim()}
                            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center space-x-2"
                        >
                            {loading ? (
                                <LoadingSpinner size="sm" color="white" text="Adding..." />
                            ) : (
                                <span>Add Symbol</span>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddSymbolModal;
