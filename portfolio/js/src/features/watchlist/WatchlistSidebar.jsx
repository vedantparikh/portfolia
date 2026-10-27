import {
    Bookmark,
    Edit3,
    Filter,
    Globe,
    Lock,
    MoreVertical,
    Plus,
    Search,
    Star,
    Trash2
} from 'lucide-react';
import { useState } from 'react';
import EditWatchlistModal from './EditWatchlistModal';

const WatchlistSidebar = ({
    watchlists,
    selectedWatchlist,
    onSelectWatchlist,
    onCreateWatchlist,
    onUpdateWatchlist,
    onDeleteWatchlist,
    searchTerm,
    onSearchChange,
    filterType,
    onFilterChange
}) => {
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingWatchlist, setEditingWatchlist] = useState(null);
    const [showDropdown, setShowDropdown] = useState(null);

    const handleEditWatchlist = (watchlist) => {
        setEditingWatchlist(watchlist);
        setShowEditModal(true);
        setShowDropdown(null);
    };

    const handleDeleteWatchlist = (watchlist) => {
        if (window.confirm(`Are you sure you want to delete "${watchlist.name}"? This action cannot be undone.`)) {
            onDeleteWatchlist(watchlist.id);
        }
        setShowDropdown(null);
    };

    const getFilterIcon = () => {
        switch (filterType) {
            case 'default':
                return <Star size={16} />;
            case 'public':
                return <Globe size={16} />;
            case 'private':
                return <Lock size={16} />;
            default:
                return <Filter size={16} />;
        }
    };

    const getFilterLabel = () => {
        switch (filterType) {
            case 'default':
                return 'Default';
            case 'public':
                return 'Public';
            case 'private':
                return 'Private';
            default:
                return 'All';
        }
    };

    return (
        <div className="w-80 bg-dark-900 border-r border-dark-700 flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-dark-700">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-gray-100">Watchlists</h2>
                    <button
                        onClick={onCreateWatchlist}
                        className="p-2 rounded-lg bg-primary-600/20 text-primary-400 hover:bg-primary-600/30 transition-colors"
                    >
                        <Plus size={16} />
                    </button>
                </div>

                {/* Search */}
                <div className="relative mb-4">
                    <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                    <input
                        type="text"
                        placeholder="Search watchlists..."
                        value={searchTerm}
                        onChange={(e) => onSearchChange(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                </div>

                {/* Filter */}
                <div className="relative">
                    <button
                        onClick={() => onFilterChange(filterType === 'all' ? 'default' : filterType === 'default' ? 'public' : filterType === 'public' ? 'private' : 'all')}
                        className="w-full flex items-center justify-between px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-300 hover:bg-dark-700 transition-colors"
                    >
                        <div className="flex items-center space-x-2">
                            {getFilterIcon()}
                            <span>{getFilterLabel()}</span>
                        </div>
                        <Filter size={14} />
                    </button>
                </div>
            </div>

            {/* Watchlist List */}
            <div className="flex-1 overflow-y-auto">
                {watchlists.length === 0 ? (
                    <div className="p-6 text-center">
                        <Bookmark size={48} className="mx-auto text-gray-600 mb-4" />
                        <p className="text-gray-400 mb-4">No watchlists found</p>
                        <button
                            onClick={onCreateWatchlist}
                            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
                        >
                            Create your first watchlist
                        </button>
                    </div>
                ) : (
                    <div className="p-4 space-y-2">
                        {watchlists.map((watchlist) => (
                            <div
                                key={watchlist.id}
                                className={`relative group p-3 rounded-lg cursor-pointer transition-colors ${
                                    selectedWatchlist?.id === watchlist.id
                                        ? 'bg-primary-600/20 border border-primary-500/30'
                                        : 'bg-dark-800 hover:bg-dark-700 border border-transparent'
                                }`}
                                onClick={() => onSelectWatchlist(watchlist)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <Bookmark 
                                                size={16} 
                                                className={`${
                                                    watchlist.is_default ? 'text-yellow-400' : 'text-gray-400'
                                                }`} 
                                            />
                                            <h3 className="text-sm font-medium text-gray-100 truncate">
                                                {watchlist.name}
                                            </h3>
                                            {watchlist.is_default && (
                                                <Star size={12} className="text-yellow-400" />
                                            )}
                                            {watchlist.is_public ? (
                                                <Globe size={12} className="text-blue-400" />
                                            ) : (
                                                <Lock size={12} className="text-gray-500" />
                                            )}
                                        </div>
                                        <p className="text-xs text-gray-400 truncate">
                                            {watchlist.description || 'No description'}
                                        </p>
                                        <div className="flex items-center space-x-4 mt-2">
                                            <span className="text-xs text-gray-500">
                                                {watchlist.item_count ?? watchlist.items?.length ?? 0} symbols
                                            </span>
                                            {watchlist.color && (
                                                <div 
                                                    className="w-3 h-3 rounded-full"
                                                    style={{ backgroundColor: watchlist.color }}
                                                />
                                            )}
                                        </div>
                                    </div>

                                    {/* Actions Dropdown */}
                                    <div className="relative">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                setShowDropdown(showDropdown === watchlist.id ? null : watchlist.id);
                                            }}
                                            className="p-1 rounded-sm hover:bg-dark-600 transition-colors opacity-0 group-hover:opacity-100"
                                        >
                                            <MoreVertical size={14} className="text-gray-400" />
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
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Footer Stats */}
            <div className="p-4 border-t border-dark-700">
                <div className="text-xs text-gray-400">
                    <div className="flex justify-between mb-1">
                        <span>Total Watchlists:</span>
                        <span>{watchlists.length}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>Total Symbols:</span>
                        <span>{watchlists.reduce((sum, w) => sum + (w.item_count ?? w.items?.length ?? 0), 0)}</span>
                    </div>
                </div>
            </div>

            {/* Edit Modal */}
            <EditWatchlistModal
                isOpen={showEditModal}
                onClose={() => {
                    setShowEditModal(false);
                    setEditingWatchlist(null);
                }}
                watchlist={editingWatchlist}
                onUpdate={onUpdateWatchlist}
            />
        </div>
    );
};

export default WatchlistSidebar;
