import { DragDropContext, Draggable, Droppable } from "@hello-pangea/dnd";
import {
  AlertTriangle,
  Edit3,
  GripVertical,
  MoreVertical,
  Plus,
  RefreshCw,
  Search,
  SortAsc,
  SortDesc,
  Trash2,
  X,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { watchlistAPI, assetAPI } from "../../services/api";
import {
  formatDate,
  formatDateTime,
  getChangeColor,
} from "../../utils/formatters.jsx";
import LoadingSpinner from "../shared/LoadingSpinner";
import EditSymbolModal from "./EditSymbolModal";

// WatchlistContent component - displays the symbols table with search, sort, and refresh controls
// This component receives props from the parent Watchlist component
const WatchlistContent = ({
  watchlist,
  onRemoveSymbol,
  onReorderItems,
  onUpdateWatchlist,
  // New props for refresh controls
  autoRefreshEnabled,
  setAutoRefreshEnabled,
  refreshInterval,
  setRefreshInterval,
  isRefreshing,
  onManualRefresh,
  onAddSymbol,
  // New prop for loading watchlist items
  onLoadWatchlistItems,
  // Loading states
  addingSymbol,
  removingSymbol,
}) => {
  // useState is a React Hook that lets you add state to functional components
  // Each useState call returns an array with two elements: [currentValue, setterFunction]
  const [loadingItems, setLoadingItems] = useState(true);
  // Search functionality state
  const [searchTerm, setSearchTerm] = useState(""); // Current search input value

  // Sorting functionality state
  const [sortBy, setSortBy] = useState("symbol"); // Which column to sort by
  const [sortOrder, setSortOrder] = useState("asc"); // Sort direction: ascending or descending

  // Load watchlist items when component mounts or watchlist changes
  useEffect(() => {
    const loadWatchlistItems = async () => {
      if (!watchlist?.id) return;

      // Only load items if they haven't been loaded yet AND items is undefined (not just empty)
      // This prevents loading when a watchlist is genuinely empty vs not yet loaded
      if (watchlist.items === undefined) {
        setLoadingItems(true);
        try {
          if (onLoadWatchlistItems) {
            await onLoadWatchlistItems(watchlist.id);
          }
        } catch (error) {
          console.error("Failed to load watchlist items:", error);
          toast.error("Failed to load watchlist items");
        } finally {
          setLoadingItems(false);
        }
      }
    };

    loadWatchlistItems();
  }, [watchlist?.id, onLoadWatchlistItems]);

  // Modal and dropdown state management
  const [showEditModal, setShowEditModal] = useState(false); // Controls edit modal visibility
  const [editingSymbol, setEditingSymbol] = useState(null); // Which symbol is being edited
  const [showDropdown, setShowDropdown] = useState(null); // Which dropdown is open (by item ID)
  const [showNotesModal, setShowNotesModal] = useState(false); // Controls notes modal visibility
  const [selectedNotes, setSelectedNotes] = useState(null); // Which symbol's notes to show

  // These functions handle user interactions and update the component state

  // Function to handle editing a symbol
  // This is called when user clicks "Edit" in the dropdown menu
  const handleEditSymbol = (symbol) => {
    setEditingSymbol(symbol); // Store which symbol we're editing
    setShowEditModal(true); // Show the edit modal
    setShowDropdown(null); // Close any open dropdowns
  };

  // Function to handle deleting a symbol
  // This shows a confirmation dialog before removing the symbol
  const handleDeleteSymbol = (itemId) => {
    // window.confirm() shows a browser confirmation dialog
    if (
      window.confirm(
        "Are you sure you want to remove this symbol from the watchlist?"
      )
    ) {
      onRemoveSymbol(itemId); // Call the parent component's remove function
    }
    setShowDropdown(null); // Close the dropdown after action
  };

  // Async function to handle updating a symbol
  // This makes an API call to update the symbol data
  const handleUpdateSymbol = async (itemId, updateData) => {
    try {
      // Find the item being updated to get its symbol
      const itemToUpdate = watchlist.items.find((item) => item.id === itemId);

      if (itemToUpdate) {
        // As requested, create an asset when the item is edited.
        // Your backend should be designed to handle this call without creating
        // duplicates if the asset already exists.
        await assetAPI.createAsset({
          symbol: itemToUpdate.symbol,
          name:
            itemToUpdate.long_name ||
            itemToUpdate.short_name ||
            "Unknown Company",
          asset_type: itemToUpdate.asset_type || "EQUITY",
          exchange: itemToUpdate.exchange,
          sector: itemToUpdate.sector,
          industry: itemToUpdate.industry,
        });
      }

      // Make API call to update the watchlist item
      const updatedItem = await watchlistAPI.updateWatchlistItem(
        watchlist.id,
        itemId,
        updateData
      );

      // If parent component provided an update callback, call it
      if (onUpdateWatchlist) {
        onUpdateWatchlist(updatedItem);
      }

      // Show success message using toast notification
      toast.success("Symbol updated successfully");
    } catch (error) {
      // Log error to console for debugging
      console.error("Failed to update symbol:", error);

      // Extract error message from API response or use default
      const errorMessage =
        error.response?.data?.message || "Failed to update symbol";

      // Show error message using toast notification
      toast.error(errorMessage);
    }
  };

  // Function to show notes for a symbol
  // This opens the notes modal with the selected symbol's data
  const handleShowNotes = (item) => {
    setSelectedNotes(item); // Store which symbol's notes to show
    setShowNotesModal(true); // Show the notes modal
  };

  // Function to handle drag and drop reordering
  // This is called when user finishes dragging a symbol to a new position
  const handleDragEnd = (result) => {
    // Check if drag operation was valid (has destination and watchlist has items)
    if (!result.destination || !watchlist?.items) return;

    // Create a copy of the items array (don't mutate original)
    const items = Array.from(watchlist.items);

    // Remove the dragged item from its original position
    const [reorderedItem] = items.splice(result.source.index, 1);

    // Insert the dragged item at its new position
    items.splice(result.destination.index, 0, reorderedItem);

    // Extract just the IDs in the new order
    const itemIds = items.map((item) => item.id);

    // Call parent component's reorder function with new order
    onReorderItems(itemIds);
  };

  // Function to get filtered and sorted items for display
  // This combines search filtering and sorting logic
  const getSortedItems = () => {
    // Return empty array if no watchlist or items
    if (!watchlist?.items) return [];

    // Create a copy of items array (spread operator creates new array)
    let items = [...watchlist.items];

    // Apply search filter if search term exists
    if (searchTerm) {
      items = items.filter(
        (item) =>
          // Search in symbol name (case insensitive)
          item.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
          // Search in company name (optional chaining ?. prevents errors if null)
          item.company_name?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Sort the filtered items
    items.sort((a, b) => {
      let aValue, bValue; // Variables to hold values for comparison

      // Switch statement determines which field to sort by
      switch (sortBy) {
        case "symbol":
          aValue = a.symbol; // String comparison
          bValue = b.symbol;
          break;
        case "price":
          // Convert to numbers for numerical comparison
          aValue = parseFloat(a.current_price || 0);
          bValue = parseFloat(b.current_price || 0);
          break;
        case "change":
          // Sort by percentage change
          aValue = parseFloat(a.price_change_percent_since_added || 0);
          bValue = parseFloat(b.price_change_percent_since_added || 0);
          break;
        case "added_price":
          // Sort by price when added to watchlist
          aValue = parseFloat(a.added_price || 0);
          bValue = parseFloat(b.added_price || 0);
          break;
        case "added_date":
          // Convert to Date objects for date comparison
          aValue = new Date(a.added_date || 0);
          bValue = new Date(b.added_date || 0);
          break;
        default:
          // Default to symbol sorting
          aValue = a.symbol;
          bValue = b.symbol;
      }

      // Apply sort order (ascending or descending)
      if (sortOrder === "asc") {
        return aValue > bValue ? 1 : -1; // Ascending: smaller values first
      } else {
        return aValue < bValue ? 1 : -1; // Descending: larger values first
      }
    });

    return items; // Return the processed items
  };

  // These are helper functions that format data for display

  // Function to format large numbers with K, M, B suffixes
  // This makes numbers more readable (e.g., 1000000 becomes 1.0M)

  // If no watchlist is provided, show a message instead of the main content
  if (!watchlist) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          {/* Warning icon */}
          <AlertTriangle size={48} className="mx-auto text-gray-600 mb-4" />
          {/* Error message */}
          <h3 className="text-lg font-medium text-gray-300 mb-2">
            No Watchlist Selected
          </h3>
          <p className="text-gray-400">
            Select a watchlist from the sidebar to view its symbols
          </p>
        </div>
      </div>
    );
  }

  // Show loading state when loading watchlist items
  if (loadingItems) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading watchlist items..." centered />
      </div>
    );
  }

  // Get the filtered and sorted items for display
  const sortedItems = getSortedItems();

  // This is what gets displayed on the screen
  return (
    <div className="flex-1 flex flex-col">
      {/* Toolbar with Search, Sort, and Refresh Controls */}
      {/* This section contains all the controls for filtering and managing the watchlist */}
      <div className="p-4 border-b border-dark-700 bg-dark-900/50">
        <div className="flex items-center justify-between">
          {/* Left side: Search and Sort controls */}
          <div className="flex items-center space-x-4">
            {/* Search input with icon */}
            <div className="relative">
              {/* Search icon positioned absolutely inside the input */}
              <Search
                size={16}
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
              />
              <input
                type="text"
                placeholder="Search symbols..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent w-64"
              />
            </div>

            {/* Sort controls */}
            <div className="flex items-center space-x-2">
              {/* Sort by dropdown */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="symbol">Symbol</option>
                <option value="price">Current Price</option>
                <option value="change">Change %</option>
                <option value="added_price">Added Price</option>
                <option value="added_date">Added Date</option>
              </select>

              {/* Sort order toggle button */}
              <button
                onClick={() =>
                  setSortOrder(sortOrder === "asc" ? "desc" : "asc")
                }
                className="p-2 rounded-lg bg-dark-800 border border-dark-600 text-gray-400 hover:bg-dark-700 transition-colors"
              >
                {sortOrder === "asc" ? (
                  <SortAsc size={16} />
                ) : (
                  <SortDesc size={16} />
                )}
              </button>
            </div>

            {/* Refresh controls - only show if props are provided */}
            {autoRefreshEnabled !== undefined && (
              <div className="flex items-center space-x-2">
                {/* Auto-refresh toggle checkbox */}
                <label className="flex items-center space-x-2 text-sm text-gray-400">
                  <input
                    type="checkbox"
                    checked={autoRefreshEnabled}
                    onChange={(e) => setAutoRefreshEnabled(e.target.checked)}
                    className="rounded border-dark-600 bg-dark-800 text-primary-600 focus:ring-primary-500"
                  />
                  <span>Auto-refresh</span>
                </label>

                {/* Refresh interval selector - only show when auto-refresh is enabled */}
                {autoRefreshEnabled && (
                  <select
                    value={refreshInterval}
                    onChange={(e) => setRefreshInterval(Number(e.target.value))}
                    className="px-2 py-1 bg-dark-800 border border-dark-600 rounded text-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  >
                    <option value={10000}>10s</option>
                    <option value={30000}>30s</option>
                    <option value={60000}>1m</option>
                    <option value={300000}>5m</option>
                  </select>
                )}

                {/* Manual refresh button */}
                <button
                  onClick={onManualRefresh}
                  disabled={isRefreshing}
                  className="flex items-center space-x-2 px-3 py-2 bg-dark-800 hover:bg-dark-700 text-gray-300 rounded-lg transition-colors disabled:opacity-50"
                  title="Refresh watchlist data"
                >
                  <RefreshCw
                    size={16}
                    className={isRefreshing ? "animate-spin" : ""}
                  />
                  <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
                </button>

                {/* Add Symbol button */}
                <button
                  onClick={onAddSymbol}
                  disabled={addingSymbol}
                  className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  <Plus size={16} />
                  <span>{addingSymbol ? "Adding..." : "Add Symbol"}</span>
                </button>
              </div>
            )}
          </div>

          {/* Right side: Symbol count display */}
          <div className="text-sm text-gray-400">
            {sortedItems.length} of {watchlist.items?.length || 0} symbols
          </div>
        </div>
      </div>

      {/* Table Headers */}
      {/* This section defines the column headers for the symbols table */}
      <div className="bg-dark-900/50 border-b border-dark-700 px-4 py-3">
        {/* Main header row with flexible layout */}
        <div className="flex items-center justify-between text-xs font-medium text-gray-400 uppercase tracking-wider">
          {/* Left side: Symbol column (flexible width) */}
          <div className="flex items-center space-x-3 flex-1">
            <div className="w-6 flex-shrink-0"></div>{" "}
            {/* Space for drag handle */}
            <span>Symbol</span> {/* Column title */}
          </div>

          {/* Right side: Fixed-width data columns */}
          <div className="flex items-center space-x-6 text-right">
            <div className="w-28 flex-shrink-0">
              <span>Added Price & Date</span>
            </div>
            <div className="w-28 flex-shrink-0">
              <span>Current Price & Last Updated</span>
            </div>
            <div className="w-24 flex-shrink-0">
              <span>Change Since Added</span>
            </div>
            <div className="w-20 flex-shrink-0">
              <span>Alerts</span>
            </div>
            <div className="w-24 flex-shrink-0">
              <span>Notes</span>
            </div>
            <div className="w-16 flex-shrink-0 text-center">
              <span>Actions</span>
            </div>
          </div>
        </div>
      </div>

      {/* Symbols Table */}
      {/* This section displays the actual symbols data in a scrollable table */}
      <div className="flex-1 overflow-auto">
        {/* Conditional rendering: show empty state or data table */}
        {sortedItems.length === 0 ? (
          /* Empty state when no symbols match the current filter */
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <AlertTriangle size={48} className="mx-auto text-gray-600 mb-4" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">
                No Symbols Found
              </h3>
              <p className="text-gray-400 mb-6">
                {searchTerm
                  ? "Try adjusting your search terms"
                  : "Add some symbols to get started"}
              </p>
              {/* Show Add Symbol button when no symbols or no search results */}
              {onAddSymbol && (
                <button
                  onClick={onAddSymbol}
                  disabled={addingSymbol}
                  className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors mx-auto disabled:opacity-50"
                >
                  <Plus size={16} />
                  <span>{addingSymbol ? "Adding..." : "Add Symbol"}</span>
                </button>
              )}
            </div>
          </div>
        ) : (
          /* Drag and Drop Table - allows reordering symbols by dragging */
          <DragDropContext onDragEnd={handleDragEnd}>
            {/* Droppable area - defines where items can be dropped */}
            <Droppable droppableId="watchlist-items">
              {/* Render prop pattern - provided contains drag/drop props */}
              {(provided) => (
                <div
                  {...provided.droppableProps} // Spread drag/drop props
                  ref={provided.innerRef} // Reference for drag/drop library
                  className="divide-y divide-dark-700" // Visual separators between rows
                >
                  {/* Map over each symbol to create a table row */}
                  {sortedItems.map((item, index) => {
                    // Calculate if price change is positive or negative for styling
                    const isPositive =
                      parseFloat(item.price_change_percent_since_added || 0) >
                      0;
                    const isNegative =
                      parseFloat(item.price_change_percent_since_added || 0) <
                      0;

                    return (
                      /* Draggable row - each symbol can be dragged to reorder */
                      <Draggable
                        key={item.id}
                        draggableId={item.id.toString()}
                        index={index}
                      >
                        {/* Render prop pattern - provided contains drag props, snapshot contains drag state */}
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef} // Reference for drag library
                            {...provided.draggableProps} // Spread drag props
                            className={`group hover:bg-dark-800/50 transition-colors ${
                              snapshot.isDragging ? "bg-dark-800" : ""
                            } ${
                              removingSymbol === item.id
                                ? "opacity-50 bg-red-900/20"
                                : ""
                            }`}
                          >
                            {/* Main row content with flexible layout */}
                            <div className="flex items-center justify-between px-4 py-3">
                              {/* Left side: Symbol info with drag handle */}
                              <div className="flex items-center space-x-3 flex-1 min-w-0">
                                {/* Drag handle - allows user to grab and drag the row */}
                                <div
                                  {...provided.dragHandleProps}
                                  className="text-gray-500 hover:text-gray-400 cursor-grab active:cursor-grabbing"
                                >
                                  <GripVertical size={16} />
                                </div>

                                {/* Symbol name and company info */}
                                <div className="flex-1 min-w-0">
                                  <h4 className="text-sm font-medium text-gray-100">
                                    {item.company_name || "Unknown Company"}
                                  </h4>
                                  <p className="text-xs text-gray-400 truncate">
                                    {item.symbol}
                                  </p>
                                </div>
                              </div>
                              {/* Right side: Data columns with fixed widths */}
                              <div className="flex items-center space-x-6 text-sm">
                                {/* Added Price & Date Column */}
                                <div className="text-right w-28 flex-shrink-0">
                                  <div className="text-gray-100 font-medium">
                                    ${item.added_price || "N/A"}
                                  </div>
                                  <div className="text-xs text-gray-400">
                                    Added {formatDate(item.added_date)}
                                  </div>
                                  <div className="text-xs text-gray-400">
                                    Days {item.days_since_added || 0}
                                  </div>
                                </div>

                                {/* Current Price & Last Updated Column */}
                                <div className="text-right w-28 flex-shrink-0">
                                  <div className="text-gray-100 font-medium">
                                    ${item.current_price || "0.00"}
                                  </div>
                                  <div className="text-xs text-gray-400">
                                    Updated {formatDateTime(item.updated_at)}
                                  </div>
                                </div>

                                {/* Change Since Added Column */}
                                <div className="text-right w-24 flex-shrink-0">
                                  <div
                                    className={`font-medium ${getChangeColor(
                                      item.price_change_percent_since_added
                                    )}`}
                                  >
                                    {isPositive ? "+" : ""}
                                    {item.price_change_percent_since_added ||
                                      "0.00"}
                                    %
                                  </div>
                                  <div
                                    className={`text-xs ${getChangeColor(
                                      item.price_change_since_added
                                    )}`}
                                  >
                                    {isPositive ? "+" : ""}
                                    {item.price_change_since_added || "0.00"}
                                  </div>
                                </div>

                                {/* Alerts Column */}
                                <div className="text-right w-20 flex-shrink-0">
                                  <div className="text-gray-100 font-medium">
                                    {item.alerts?.length || 0}
                                  </div>
                                  <div className="text-xs text-gray-400">
                                    Alerts
                                  </div>
                                </div>

                                {/* Notes Column - clickable if notes exist */}
                                <div className="text-right w-24 flex-shrink-0">
                                  <div
                                    className={`font-medium cursor-pointer transition-colors ${
                                      item.notes
                                        ? "text-blue-400 hover:text-blue-300"
                                        : "text-gray-500"
                                    }`}
                                    onClick={() =>
                                      item.notes && handleShowNotes(item)
                                    }
                                    title={
                                      item.notes
                                        ? "Click to view notes"
                                        : "No notes"
                                    }
                                  >
                                    {item.notes ? "Yes" : "No"}
                                  </div>
                                  <div className="text-xs text-gray-400">
                                    Notes
                                  </div>
                                </div>

                                {/* Actions Column - dropdown menu */}
                                <div className="relative w-16 text-center flex-shrink-0">
                                  {/* Three-dot menu button */}
                                  <button
                                    onClick={() =>
                                      setShowDropdown(
                                        showDropdown === item.id
                                          ? null
                                          : item.id
                                      )
                                    }
                                    className="p-1 rounded hover:bg-dark-600 transition-colors opacity-0 group-hover:opacity-100"
                                  >
                                    <MoreVertical
                                      size={14}
                                      className="text-gray-400"
                                    />
                                  </button>

                                  {/* Dropdown menu - only show for this item */}
                                  {showDropdown === item.id && (
                                    <div className="absolute right-0 top-8 w-48 bg-dark-800 border border-dark-600 rounded-lg shadow-lg z-10">
                                      <button
                                        onClick={() => handleEditSymbol(item)}
                                        className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-gray-300 hover:bg-dark-700 transition-colors"
                                      >
                                        <Edit3 size={14} />
                                        <span>Edit</span>
                                      </button>
                                      <button
                                        onClick={() =>
                                          handleDeleteSymbol(item.id)
                                        }
                                        disabled={removingSymbol === item.id}
                                        className="w-full flex items-center space-x-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                                      >
                                        <Trash2 size={14} />
                                        <span>
                                          {removingSymbol === item.id
                                            ? "Removing..."
                                            : "Remove"}
                                        </span>
                                      </button>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </Draggable>
                    );
                  })}
                  {/* Placeholder for drag and drop - shows where item will be dropped */}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        )}
      </div>

      {/* ===== MODALS ===== */}
      {/* Edit Symbol Modal - allows editing symbol details */}
      <EditSymbolModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setEditingSymbol(null);
        }}
        symbol={editingSymbol}
        onUpdate={handleUpdateSymbol}
      />

      {/* Notes Modal - displays symbol notes */}
      {showNotesModal && selectedNotes && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-dark-900 border border-dark-700 rounded-lg w-full max-w-md mx-4">
            {/* Modal header */}
            <div className="flex items-center justify-between p-6 border-b border-dark-700">
              <h2 className="text-lg font-semibold text-gray-100">
                Notes for {selectedNotes.symbol}
              </h2>
              <button
                onClick={() => {
                  setShowNotesModal(false);
                  setSelectedNotes(null);
                }}
                className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
              >
                <X size={20} className="text-gray-400" />
              </button>
            </div>

            {/* Modal content */}
            <div className="p-6">
              <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
                <p className="text-gray-100 whitespace-pre-wrap">
                  {selectedNotes.notes || "No notes available for this symbol."}
                </p>
              </div>

              {/* Edit notes button */}
              <div className="mt-4 text-center">
                <button
                  onClick={() => {
                    setShowNotesModal(false);
                    setSelectedNotes(null);
                    setShowEditModal(true);
                    setEditingSymbol(selectedNotes);
                  }}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
                >
                  Edit Notes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WatchlistContent;
