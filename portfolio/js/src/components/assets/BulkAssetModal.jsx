import { Loader2, Plus, Tags, X } from 'lucide-react';
import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { assetAPI } from '../../services/api';
import { SymbolSearch } from '../shared'; // Make sure this path is correct

const BulkAssetModal = ({ onClose, onSuccess }) => {
    // State is now much simpler!
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedAssets, setSelectedAssets] = useState([]);
    const [isSaving, setIsSaving] = useState(false);

    // This function is called when a user selects an asset from the SymbolSearch dropdown.
    const handleSelectAsset = (asset) => {
        // Prevent adding duplicates
        if (selectedAssets.some(a => a.symbol === asset.symbol)) {
            toast.error(`${asset.symbol} is already in the list.`);
            return;
        }

        // Add the new asset and clear the search input
        setSelectedAssets(prev => [...prev, asset]);
        setSearchQuery('');
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
            const { created = [], failed = [] } = response.data || response || {};

            if (failed.length === 0 && created.length > 0) {
                toast.success(`${created.length} asset(s) added successfully!`);
            } else if (failed.length > 0 && created.length > 0) {
                toast.success(
                    `Partial success: ${created.length} added. ${failed.length} failed.`,
                    { duration: 4000 }
                );
            } else if (failed.length > 0 && created.length === 0) {
                toast.error(
                    `Failed to add all ${failed.length} asset(s). They may already exist.`,
                    { duration: 4000 }
                );
            }

            if (created.length > 0) {
                onSuccess();
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
                    {/* UPDATED SEARCH SECTION */}
                    <div className="card p-6 relative z-10">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4">Search Assets</h3>
                        <SymbolSearch
                            value={searchQuery}
                            onChange={setSearchQuery}
                            onSelect={handleSelectAsset}
                            placeholder="Search by symbol or name (e.g., AAPL, Bitcoin)..."
                            excludeSymbols={selectedAssets.map(a => a.symbol)}
                        />
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