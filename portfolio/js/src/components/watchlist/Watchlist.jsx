import { ArrowLeft, Bookmark, Edit3, MoreVertical, Plus, RefreshCw, Star, Trash2 } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { watchlistAPI } from '../../services/api';
import EmailVerificationPrompt from '../auth/EmailVerificationPrompt';
import { LoadingSpinner, Sidebar } from '../shared';
import AddSymbolModal from './AddSymbolModal';
import CreateWatchlistModal from './CreateWatchlistModal';
import EditWatchlistModal from './EditWatchlistModal';
import WatchlistContent from './WatchlistContent';

const Watchlist = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [watchlists, setWatchlists] = useState([]);
    const [selectedWatchlist, setSelectedWatchlist] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showAddSymbolModal, setShowAddSymbolModal] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('all');
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
    const [refreshInterval, setRefreshInterval] = useState(30000); // 30 seconds default
    const [isMobile, setIsMobile] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingWatchlist, setEditingWatchlist] = useState(null);
    const [showDropdown, setShowDropdown] = useState(null);
    const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'content'

    // Additional loading states for specific operations
    const [addingSymbol, setAddingSymbol] = useState(false);
    const [removingSymbol, setRemovingSymbol] = useState(null); // Store the ID of symbol being removed
    const [creatingWatchlist, setCreatingWatchlist] = useState(false);
    const [updatingWatchlist, setUpdatingWatchlist] = useState(false);
    const [deletingWatchlist, setDeletingWatchlist] = useState(null); // Store the ID of watchlist being deleted

    // useRef to store the interval ID so we can clear it later
    const refreshIntervalRef = useRef(null);

    // Load watchlists on component mount
    useEffect(() => {
        loadWatchlists();
    }, []);

    // Check for mobile screen size
    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(window.innerWidth < 768);
        };

        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    // Set up automatic refresh when component mounts and selectedWatchlist changes
    useEffect(() => {
        // Clear any existing interval
        if (refreshIntervalRef.current) {
            clearInterval(refreshIntervalRef.current);
        }

        // Only start auto-refresh if we have a selected watchlist and auto-refresh is enabled
        if (selectedWatchlist && autoRefreshEnabled) {
            console.log(`[Watchlist] Starting auto-refresh every ${refreshInterval}ms for watchlist ${selectedWatchlist.id}`);

            refreshIntervalRef.current = setInterval(() => {
                refreshSelectedWatchlist();
            }, refreshInterval);
        }

        // Cleanup function - this runs when component unmounts or dependencies change
        return () => {
            if (refreshIntervalRef.current) {
                console.log('[Watchlist] Clearing auto-refresh interval');
                clearInterval(refreshIntervalRef.current);
            }
        };
    }, [selectedWatchlist, autoRefreshEnabled, refreshInterval]); // Dependencies: re-run when these change

    const loadWatchlists = async () => {
        try {
            setLoading(true);
            const data = await watchlistAPI.getWatchlists(false);
            console.log('[Watchlist] Watchlists response:', data);
            setWatchlists(data || []);

        } catch (error) {
            console.error('Failed to load watchlists:', error);
            console.error('Error details:', error.response?.data);
            toast.error('Failed to load watchlists');
        } finally {
            setLoading(false);
        }
    };

    // Function to refresh the currently selected watchlist data
    const refreshSelectedWatchlist = async () => {
        if (!selectedWatchlist) return;

        try {
            console.log(`[Watchlist] Refreshing watchlist ${selectedWatchlist.id} with real-time data`);
            setIsRefreshing(true);

            // Fetch the latest data with real-time prices
            const updatedWatchlist = await watchlistAPI.getWatchlist(selectedWatchlist.id, true);
            setSelectedWatchlist(updatedWatchlist);

            console.log('[Watchlist] Watchlist data refreshed successfully');
        } catch (error) {
            console.error('Failed to refresh watchlist data:', error);
            // Don't show toast for background refresh failures to avoid spam
            if (!autoRefreshEnabled) {
                toast.error('Failed to refresh watchlist data');
            }
        } finally {
            setIsRefreshing(false);
        }
    };

    // Manual refresh function (called when user clicks refresh button)
    const handleManualRefresh = async () => {
        await refreshSelectedWatchlist();
        toast.success('Watchlist data refreshed');
    };

    const handleQuickAction = (action) => {
        switch (action) {
            case 'create-portfolio':
                navigate('/portfolio');
                break;
            case 'create-transaction':
                navigate('/transactions');
                break;
            case 'refresh':
                handleManualRefresh();
                break;
            default:
                break;
        }
    };

    const handleEditWatchlist = (watchlist) => {
        setEditingWatchlist(watchlist);
        setShowEditModal(true);
        setShowDropdown(null);
    };

    const handleDeleteWatchlist = (watchlist) => {
        if (window.confirm(`Are you sure you want to delete "${watchlist.name}"? This action cannot be undone.`)) {
            deleteWatchlist(watchlist.id);
        }
        setShowDropdown(null);
    };

    const getWatchlistColor = (watchlist) => {
        if (watchlist.color) {
            return watchlist.color;
        }
        // Fallback colors based on watchlist ID for consistency
        const fallbackColors = [
            '#3B82F6', // blue
            '#10B981', // emerald
            '#F59E0B', // amber
            '#EF4444', // red
            '#8B5CF6', // violet
            '#06B6D4', // cyan
            '#84CC16', // lime
            '#F97316', // orange
        ];
        return fallbackColors[watchlist.id % fallbackColors.length];
    };

    const sortedWatchlists = [...watchlists].sort((a, b) => {
        // Default watchlist first
        if (a.is_default && !b.is_default) return -1;
        if (!a.is_default && b.is_default) return 1;
        // Then by name
        return a.name.localeCompare(b.name);
    });

    const handleCreateWatchlist = async (watchlistData) => {
        try {
            setCreatingWatchlist(true);
            console.log('Creating watchlist with data:', watchlistData);
            const newWatchlist = await watchlistAPI.createWatchlist(watchlistData);
            console.log('Watchlist created successfully:', newWatchlist);
            setWatchlists(prev => [...prev, newWatchlist]);
            setSelectedWatchlist(newWatchlist);
            setShowCreateModal(false);
            toast.success('Watchlist created successfully');
        } catch (error) {
            console.error('Failed to create watchlist:', error);
            console.error('Error details:', error.response?.data);
            toast.error('Failed to create watchlist');
        } finally {
            setCreatingWatchlist(false);
        }
    };

    const handleUpdateWatchlist = async (watchlistId, updateData) => {
        try {
            setUpdatingWatchlist(true);
            const updatedWatchlist = await watchlistAPI.updateWatchlist(watchlistId, updateData);
            setWatchlists(prev =>
                prev.map(w => w.id === watchlistId ? updatedWatchlist : w)
            );
            if (selectedWatchlist?.id === watchlistId) {
                setSelectedWatchlist(updatedWatchlist);
            }
            toast.success('Watchlist updated successfully');
        } catch (error) {
            console.error('Failed to update watchlist:', error);
            toast.error('Failed to update watchlist');
        } finally {
            setUpdatingWatchlist(false);
        }
    };

    const deleteWatchlist = async (watchlistId) => {
        try {
            setDeletingWatchlist(watchlistId);
            await watchlistAPI.deleteWatchlist(watchlistId);
            setWatchlists(prev => prev.filter(w => w.id !== watchlistId));

            // If deleted watchlist was selected, select another one
            if (selectedWatchlist?.id === watchlistId) {
                const remainingWatchlists = watchlists.filter(w => w.id !== watchlistId);
                if (remainingWatchlists.length > 0) {
                    setSelectedWatchlist(remainingWatchlists[0]);
                } else {
                    setSelectedWatchlist(null);
                }
            }
            toast.success('Watchlist deleted successfully');
        } catch (error) {
            console.error('Failed to delete watchlist:', error);
            toast.error('Failed to delete watchlist');
        } finally {
            setDeletingWatchlist(null);
        }
    };

    const handleAddSymbol = async (symbolData) => {
        if (!selectedWatchlist) {
            const error = new Error('Please select a watchlist first');
            throw error;
        }

        try {
            setAddingSymbol(true);
            // Extract symbol string for display purposes
            const symbolString = typeof symbolData === 'string' ? symbolData : symbolData.symbol || symbolData.name;
            symbolData.company_name = symbolData.long_name || symbolData.short_name || symbolData.longname || symbolData.shortname || symbolData.name;

            // Pass the complete symbol data to the API
            const newItem = await watchlistAPI.addItemToWatchlist(selectedWatchlist.id, symbolData);

            // Update the selected watchlist with the new item
            setSelectedWatchlist(prev => ({
                ...prev,
                items: [...(prev.items || []), newItem]
            }));

            setShowAddSymbolModal(false);
            toast.success(`${symbolString} added to watchlist`);
        } catch (error) {
            console.error('Failed to add symbol:', error);

            // Provide more specific error messages
            let errorMessage = 'Failed to add symbol to watchlist';

            if (error.response?.status === 400) {
                errorMessage = error.response.data?.message || 'Invalid symbol or symbol already exists';
            } else if (error.response?.status === 404) {
                errorMessage = 'Watchlist not found';
            } else if (error.response?.status === 401) {
                errorMessage = 'Please log in again';
            } else if (error.response?.status >= 500) {
                errorMessage = 'Server error. Please try again later';
            } else if (error.message === 'Please select a watchlist first') {
                errorMessage = error.message;
            }

            toast.error(errorMessage);
            throw error; // Re-throw to let the modal handle it
        } finally {
            setAddingSymbol(false);
        }
    };

    const handleRemoveSymbol = async (itemId) => {
        if (!selectedWatchlist) return;

        try {
            setRemovingSymbol(itemId);
            await watchlistAPI.removeItemFromWatchlist(selectedWatchlist.id, itemId);

            // Update the selected watchlist by removing the item
            setSelectedWatchlist(prev => ({
                ...prev,
                items: prev.items.filter(item => item.id !== itemId)
            }));

            toast.success('Symbol removed from watchlist');
        } catch (error) {
            console.error('Failed to remove symbol:', error);
            toast.error('Failed to remove symbol from watchlist');
        } finally {
            setRemovingSymbol(null);
        }
    };

    const handleReorderItems = async (itemIds) => {
        if (!selectedWatchlist) return;

        try {
            await watchlistAPI.reorderWatchlistItems(selectedWatchlist.id, itemIds);

            // Update the selected watchlist with reordered items
            const reorderedItems = itemIds.map(id =>
                selectedWatchlist.items.find(item => item.id === id)
            ).filter(Boolean);

            setSelectedWatchlist(prev => ({
                ...prev,
                items: reorderedItems
            }));
        } catch (error) {
            console.error('Failed to reorder items:', error);
            toast.error('Failed to reorder watchlist items');
        }
    };

    const handleSelectWatchlist = async (watchlist) => {
        try {
            // Only load the basic watchlist data first, not the items
            setSelectedWatchlist(watchlist);
            setViewMode('content');
        } catch (error) {
            console.error('Failed to select watchlist:', error);
            toast.error('Failed to select watchlist');
        }
    };

    const handleUpdateWatchlistItem = (updatedItem) => {
        // Update the selected watchlist with the updated item
        setSelectedWatchlist(prev => ({
            ...prev,
            items: prev.items.map(item =>
                item.id === updatedItem.id ? updatedItem : item
            )
        }));
    };

    const handleLoadWatchlistItems = async (watchlistId) => {
        try {
            // Load the full watchlist with items
            const fullWatchlist = await watchlistAPI.getWatchlist(watchlistId, true);
            setSelectedWatchlist(fullWatchlist);
        } catch (error) {
            console.error('Failed to load watchlist items:', error);
            throw error; // Re-throw to let the component handle it
        }
    };

    const handleBackToGrid = () => {
        setViewMode('grid');
        setSelectedWatchlist(null);
    };

    const filteredWatchlists = watchlists.filter(watchlist => {
        const matchesSearch = watchlist.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            watchlist.description?.toLowerCase().includes(searchTerm.toLowerCase());

        if (filterType === 'all') return matchesSearch;
        if (filterType === 'default') return matchesSearch && watchlist.is_default;
        if (filterType === 'public') return matchesSearch && watchlist.is_public;
        if (filterType === 'private') return matchesSearch && !watchlist.is_public;

        return matchesSearch;
    });

    if (loading) {
        return (
            <div className="min-h-screen gradient-bg flex items-center justify-center">
                <LoadingSpinner size="lg" text="Loading watchlists..." centered />
            </div>
        );
    }

    return (
        <div className="min-h-screen gradient-bg flex">
            {/* Mobile sidebar overlay */}
            {isMobile && sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Shared Sidebar */}
            <Sidebar
                currentView="watchlist"
                onRefresh={handleManualRefresh}
                onQuickAction={handleQuickAction}
                isMobile={isMobile}
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
            />

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Mobile Header */}
                {isMobile && (
                    <div className="bg-dark-900 border-b border-dark-700 p-4 flex items-center justify-between">
                        <button
                            onClick={() => setSidebarOpen(true)}
                            className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
                        >
                            <Bookmark size={20} className="text-gray-400" />
                        </button>
                        <h1 className="text-lg font-semibold text-gray-100">Watchlists</h1>
                        <div className="w-10" /> {/* Spacer for centering */}
                    </div>
                )}

                {/* Email Verification Prompt */}
                {user && !user.is_verified && (
                    <div className="px-6 pt-6">
                        <EmailVerificationPrompt user={user} />
                    </div>
                )}

                {/* Header */}
                <header className="bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            {viewMode === 'content' ? (
                                /* Content View Header */
                                <>
                                    <button
                                        onClick={handleBackToGrid}
                                        className="flex items-center space-x-2 px-3 py-2 text-gray-400 hover:text-gray-100 hover:bg-dark-800 rounded-lg transition-colors"
                                    >
                                        <ArrowLeft size={20} />
                                        <span>Back to Watchlists</span>
                                    </button>
                                    <div className="w-px h-6 bg-dark-600"></div>
                                    <Bookmark size={24} className="text-primary-400" />
                                    <div>
                                        <h1 className="text-xl font-semibold text-gray-100">
                                            {selectedWatchlist?.name || 'Watchlist'}
                                        </h1>
                                        <p className="text-sm text-gray-400">
                                            {selectedWatchlist?.items?.length || 0} symbols • {selectedWatchlist?.is_public ? 'Public' : 'Private'}
                                        </p>
                                    </div>
                                </>
                            ) : (
                                /* Grid View Header */
                                <>
                                    <button
                                        onClick={() => navigate('/dashboard')}
                                        className="flex items-center space-x-2 px-3 py-2 text-gray-400 hover:text-gray-100 hover:bg-dark-800 rounded-lg transition-colors"
                                    >
                                        <ArrowLeft size={20} />
                                        <span>Back to Dashboard</span>
                                    </button>
                                    <div className="w-px h-6 bg-dark-600"></div>
                                    <Bookmark size={24} className="text-primary-400" />
                                    <div>
                                        <h1 className="text-xl font-semibold text-gray-100">Watchlists</h1>
                                        <p className="text-sm text-gray-400">
                                            Manage your watchlists and track market symbols
                                        </p>
                                    </div>
                                </>
                            )}
                        </div>

                        <div className="flex items-center space-x-3">
                            {viewMode === 'grid' && (
                                <>
                                    <button
                                        onClick={handleManualRefresh}
                                        disabled={isRefreshing}
                                        className="flex items-center space-x-2 px-3 py-2 bg-dark-800 hover:bg-dark-700 text-gray-300 rounded-lg transition-colors disabled:opacity-50"
                                        title="Refresh watchlist data"
                                    >
                                        <RefreshCw
                                            size={16}
                                            className={isRefreshing ? 'animate-spin' : ''}
                                        />
                                        <span>{isRefreshing ? 'Refreshing...' : 'Refresh'}</span>
                                    </button>

                                    <button
                                        onClick={() => setShowCreateModal(true)}
                                        disabled={creatingWatchlist}
                                        className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        <Plus size={16} />
                                        <span>{creatingWatchlist ? 'Creating...' : 'New Watchlist'}</span>
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </header>

                {/* Main Content Area */}
                <main className="flex-1 p-6 overflow-auto">
                    <div className="max-w-7xl mx-auto">
                        {viewMode === 'content' && selectedWatchlist ? (
                            /* Watchlist Content View */
                            <div>
                                {/* Watchlist Content with inline refresh controls */}
                                <WatchlistContent
                                    watchlist={selectedWatchlist}
                                    onRemoveSymbol={handleRemoveSymbol}
                                    onReorderItems={handleReorderItems}
                                    onUpdateWatchlist={handleUpdateWatchlistItem}
                                    // Pass refresh controls as props to WatchlistContent
                                    autoRefreshEnabled={autoRefreshEnabled}
                                    setAutoRefreshEnabled={setAutoRefreshEnabled}
                                    refreshInterval={refreshInterval}
                                    setRefreshInterval={setRefreshInterval}
                                    isRefreshing={isRefreshing}
                                    onManualRefresh={handleManualRefresh}
                                    onAddSymbol={() => setShowAddSymbolModal(true)}
                                    onLoadWatchlistItems={handleLoadWatchlistItems}
                                    // Pass loading states
                                    addingSymbol={addingSymbol}
                                    removingSymbol={removingSymbol}
                                />
                            </div>
                        ) : (
                            /* Watchlists Grid View */
                            <>
                                {loading ? (
                                    <div className="flex items-center justify-center py-12">
                                        <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
                                        <span className="ml-3 text-gray-400">Loading watchlists...</span>
                                    </div>
                                ) : sortedWatchlists.length === 0 ? (
                                    <div className="text-center py-12">
                                        <Bookmark className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                        <h3 className="text-xl font-semibold text-gray-300 mb-2">No watchlists yet</h3>
                                        <p className="text-gray-500 mb-6">Create your first watchlist to start tracking market symbols</p>
                                        <button
                                            onClick={() => setShowCreateModal(true)}
                                            className="btn-primary flex items-center space-x-2 mx-auto"
                                        >
                                            <Plus size={16} />
                                            <span>Create Watchlist</span>
                                        </button>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                        {/* Watchlist Cards */}
                                        {sortedWatchlists.map((watchlist) => {
                                            const color = getWatchlistColor(watchlist);
                                            return (
                                                <div
                                                    key={watchlist.id}
                                                    className="group relative p-6 bg-dark-800 rounded-xl hover:bg-dark-700 transition-all duration-200 cursor-pointer border border-dark-700 hover:border-dark-600"
                                                    onClick={() => handleSelectWatchlist(watchlist)}
                                                >
                                                    {/* Color indicator */}
                                                    <div
                                                        className="absolute top-0 left-0 right-0 h-1 rounded-t-xl"
                                                        style={{ backgroundColor: color }}
                                                    />

                                                    {/* Header */}
                                                    <div className="flex items-start justify-between mb-4">
                                                        <div className="flex items-center space-x-2">
                                                            <Bookmark
                                                                size={20}
                                                                className={watchlist.is_default ? 'text-yellow-400' : 'text-gray-400'}
                                                            />
                                                            {watchlist.is_default && (
                                                                <Star size={16} className="text-yellow-400" />
                                                            )}
                                                        </div>

                                                        {/* Actions Dropdown */}
                                                        <div className="relative">
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setShowDropdown(showDropdown === watchlist.id ? null : watchlist.id);
                                                                }}
                                                                className="p-1 rounded hover:bg-dark-600 transition-colors opacity-0 group-hover:opacity-100"
                                                            >
                                                                <MoreVertical size={16} className="text-gray-400" />
                                                            </button>

                                                            {showDropdown === watchlist.id && (
                                                                <div className="absolute right-0 top-8 w-48 bg-dark-800 border border-dark-600 rounded-lg shadow-lg z-10">
                                                                    <button
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            handleEditWatchlist(watchlist);
                                                                        }}
                                                                        className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-300 hover:bg-dark-700 transition-colors"
                                                                    >
                                                                        <Edit3 size={14} />
                                                                        <span>Edit</span>
                                                                    </button>
                                                                    <button
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            handleDeleteWatchlist(watchlist);
                                                                        }}
                                                                        className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                                                                    >
                                                                        <Trash2 size={14} />
                                                                        <span>Delete</span>
                                                                    </button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Watchlist Info */}
                                                    <div className="mb-4">
                                                        <h3 className="text-lg font-semibold text-gray-100 mb-2 truncate">
                                                            {watchlist.name}
                                                        </h3>
                                                        <p className="text-sm text-gray-400 line-clamp-2">
                                                            {watchlist.description || 'No description'}
                                                        </p>
                                                    </div>

                                                    {/* Stats */}
                                                    <div className="flex items-center justify-between text-sm">
                                                        <div className="flex items-center space-x-4">
                                                            <span className="text-gray-400">
                                                                {watchlist.items?.length || 0} symbols
                                                            </span>
                                                            <div
                                                                className="w-3 h-3 rounded-full"
                                                                style={{ backgroundColor: color }}
                                                            />
                                                        </div>
                                                        <div className="text-gray-500">
                                                            {watchlist.is_public ? 'Public' : 'Private'}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}

                                        {/* Create New Watchlist Card - Now at the end */}
                                        <div
                                            onClick={() => setShowCreateModal(true)}
                                            className="group cursor-pointer p-6 bg-dark-800 border-2 border-dashed border-gray-600 rounded-xl hover:border-primary-500 hover:bg-dark-700 transition-all duration-200 flex flex-col items-center justify-center min-h-[200px]"
                                        >
                                            <div className="w-12 h-12 bg-primary-600/20 rounded-full flex items-center justify-center mb-4 group-hover:bg-primary-600/30 transition-colors">
                                                <Plus size={24} className="text-primary-400" />
                                            </div>
                                            <h3 className="text-lg font-semibold text-gray-100 mb-2">Create New Watchlist</h3>
                                            <p className="text-sm text-gray-400 text-center">Start tracking your favorite symbols</p>
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </main>
            </div>

            {/* Modals */}
            <CreateWatchlistModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onCreate={handleCreateWatchlist}
                isLoading={creatingWatchlist}
            />

            <EditWatchlistModal
                isOpen={showEditModal}
                onClose={() => {
                    setShowEditModal(false);
                    setEditingWatchlist(null);
                }}
                watchlist={editingWatchlist}
                onUpdate={handleUpdateWatchlist}
                isLoading={updatingWatchlist}
            />

            <AddSymbolModal
                isOpen={showAddSymbolModal}
                onClose={() => setShowAddSymbolModal(false)}
                onAdd={handleAddSymbol}
                isLoading={addingSymbol}
            />
        </div>
    );
};

export default Watchlist;
