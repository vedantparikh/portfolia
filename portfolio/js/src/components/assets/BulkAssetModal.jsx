import { Loader2, Plus, Search, Tags, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { assetAPI, marketAPI } from '../../services/api';

export const useDebounce = (value, delay) => {
    const [debouncedValue, setDebouncedValue] = useState(value);
    useEffect(() => {
        const handler = setTimeout(() => setDebouncedValue(value), delay);
        return () => clearTimeout(handler);
    }, [value, delay]);
    return debouncedValue;
};

const BulkAssetModal = ({ onClose, onSuccess }) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [selectedAssets, setSelectedAssets] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const debouncedSearchQuery = useDebounce(searchQuery, 300);

    useEffect(() => {
        const searchAssets = async () => {
            if (!debouncedSearchQuery || debouncedSearchQuery.length < 2) {
                setSearchResults([]);
                return;
            }
            setIsSearching(true);
            try {
                const response = await marketAPI.searchSymbols(debouncedSearchQuery);
                const responseData = response.data || response;
                const selectedSymbols = selectedAssets.map(a => a.symbol);
                setSearchResults(responseData.filter(r => !selectedSymbols.includes(r.symbol)));
            } catch (error) {
                console.error('Failed to search assets:', error);
                setSearchResults([]);
            } finally {
                setIsSearching(false);
            }
        };
        searchAssets();
    }, [debouncedSearchQuery]);

    const handleSelectAsset = (asset) => {
        setSelectedAssets(prev => [...prev, asset]);
        setSearchQuery('');
        setSearchResults([]);
    };

    const handleRemoveAsset = (symbol) => {
        setSelectedAssets(prev => prev.filter(a => a.symbol !== symbol));
    };

    const handleSave = async () => {
        if (selectedAssets.length === 0) {
            toast.error('Please select at least one asset to add.');
            return;
        }

        setIsSaving(true);
        const symbols = selectedAssets.map(a => a.symbol);

        try {
            const response = await assetAPI.createBulkAssets(symbols);
            const responseData = response.data || response;
            const { created = [], failed = [] } = responseData || {};

            if (failed.length === 0 && created.length > 0) {
                toast.success(`${created.length} asset(s) added successfully!`);
            } else if (failed.length > 0 && created.length > 0) {
                const failedDetails = failed.map(f => `${f.symbol} (${f.reason})`).join(', ');
                toast.success(
                    `Partial success: ${created.length} added. Failed ${failed.length}: ${failedDetails}.`,
                    { duration: 4000 }
                );
            } else if (failed.length > 0 && created.length === 0) {
                const failedReasons = failed.map(f => `${f.symbol}: ${f.reason}`).join('\n');
                toast.error(
                    `Failed to add all ${failed.length} asset(s):\n${failedReasons}`,
                    { duration: 4000 }
                );
            }

            if (created.length > 0) {
                onSuccess();
            } else {
                onClose();
            }
        } catch (error) {
            console.error('Failed to save assets in bulk:', error);
            const errorMessage = error.response?.data?.detail || 'An unexpected error occurred while saving.';
            toast.error(errorMessage);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4">
            <div className="bg-dark-900 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <h3 className="text-xl font-semibold text-gray-100">Add Assets in Bulk</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-100">
                        <X size={24} />
                    </button>
                </div>

                <div className="p-6 space-y-6 overflow-y-auto">
                    <div className="card p-6 relative z-10">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4">Search Assets</h3>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                            <input
                                type="text"
                                placeholder="Search by symbol or name (e.g., AAPL, Bitcoin)..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="input-field w-full pl-10 pr-4 py-3"
                            />
                            {isSearching && <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 text-primary-400 animate-spin" />}
                        </div>
                        
                        {searchResults.length > 0 && (
                            <div className="absolute top-full left-0 w-full bg-dark-700 border-x border-b border-dark-600 rounded-b-lg max-h-60 overflow-y-auto shadow-lg">
                                <ul className="p-2">
                                    {searchResults.map((asset) => (
                                        <li
                                            key={asset.symbol}
                                            onClick={() => handleSelectAsset(asset)}
                                            className="px-4 py-3 cursor-pointer hover:bg-primary-600/20 rounded-md transition-colors"
                                        >
                                            <div className="flex flex-col">
                                                <span className="font-semibold text-gray-100">{asset.symbol}</span>
                                                <div className="flex items-center space-x-2">
                                                    <span className="text-sm text-gray-400 truncate">
                                                        {asset.name || asset.short_name || 'N/A'}
                                                    </span>
                                                    <span className="text-xs text-gray-500">
                                                        {asset.exchange && `${asset.exchange} • `}{asset.asset_type}
                                                    </span>
                                                </div>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    <div className="card p-6 min-h-[120px]">
                        <h4 className="text-lg font-semibold text-gray-100 mb-4 flex items-center">
                            <Tags size={18} className="mr-2" />
                            Assets to Add ({selectedAssets.length})
                        </h4>
                        {selectedAssets.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {selectedAssets.map(asset => (
                                    <span key={asset.symbol} className="flex items-center bg-primary-600/30 text-primary-300 text-sm font-medium px-3 py-1 rounded-full">
                                        {asset.symbol}
                                        <button onClick={() => handleRemoveAsset(asset.symbol)} className="ml-2 text-primary-200 hover:text-white">
                                            <X size={14} />
                                        </button>
                                    </span>
                                ))}
                            </div>
                        ) : (
                            <p className="text-gray-500 text-center text-sm py-4">Search for assets to add them to the list.</p>
                        )}
                    </div>
                </div>

                <div className="flex items-center justify-end p-6 border-t border-dark-700">
                    <button onClick={onClose} className="btn-outline mr-3">Cancel</button>
                    <button
                        onClick={handleSave}
                        disabled={isSaving || selectedAssets.length === 0}
                        className="btn-primary flex items-center"
                    >
                        {isSaving ? <Loader2 className="animate-spin mr-2" size={16} /> : <Plus size={16} className="mr-2" />}
                        Add {selectedAssets.length > 0 ? selectedAssets.length : ''} Asset(s)
                    </button>
                </div>
            </div>
        </div>
    );
};

export default BulkAssetModal;