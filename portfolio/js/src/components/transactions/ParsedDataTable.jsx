import {
  AlertTriangle,
  CheckCircle,
  Edit2,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  X,
} from "lucide-react";
import React, { useEffect, useMemo, useState, useRef } from "react";
import toast from "react-hot-toast";
import { ClientSideAssetSearch } from "../shared";
import transactionTypes from "../../utils/transactionTypes";

const ParsedDataTable = ({
  parsedData,
  onSave,
  onCancel,
  portfolios = [],
  allAssets = [],
}) => {
  const [transactions, setTransactions] = useState([]);
  const [editingRowId, setEditingRowId] = useState(null); // Changed from index to ID for stability
  const [frozenTransactions, setFrozenTransactions] = useState([]); // Holds the sorted list when editing to "freeze" it
  const [originalTransaction, setOriginalTransaction] = useState(null); // Holds the state of a row before editing to allow for cancellation
  const [scrollToId, setScrollToId] = useState(null); // Stores the ID of the row to scroll to after saving
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveErrors, setSaveErrors] = useState({});

  const rowRefs = useRef({}); // To store DOM references for each table row for scrolling

  const allAssetsJson = JSON.stringify(allAssets);

  const assetSymbolMap = useMemo(() => {
    if (allAssets.length === 0) {
      return new Map();
    }
    return new Map(allAssets.map((asset) => [asset.symbol.toUpperCase(), asset]));
  }, [allAssetsJson]);

  const transactionsJson = JSON.stringify(parsedData?.transactions);

  useEffect(() => {
    // Guard clause: still useful to prevent running with incomplete data
    if (!parsedData?.transactions || allAssets.length === 0) {
      setTransactions([]); // Clear transactions if data is missing
      return;
    }

    // The asset map is now calculated inside the effect, as it depends on `allAssets`
    const assetSymbolMap = new Map(
      allAssets.map((asset) => [asset.symbol.toUpperCase(), asset])
    );

    const initialTransactions = parsedData.transactions.map((t, index) => {
      const cleanSymbol = t.symbol?.trim().toUpperCase();
      const matchedAsset = assetSymbolMap.get(cleanSymbol);
      return {
        ...t,
        symbol: t.symbol?.trim(),
        id: t.id || `initial_${index}`,
        asset_id: matchedAsset ? matchedAsset.id : null,
        name: matchedAsset ? matchedAsset.name : t.name,
      };
    });

    setTransactions(initialTransactions);
  }, [parsedData, allAssets]);

  // Helper function to identify incomplete transactions
  const isTransactionIncomplete = (txn) => {
    if (!txn.asset_id && txn.symbol) {
      return true; // Unmatched symbol
    }
    if (["buy", "sell"].includes(txn.transaction_type?.toLowerCase())) {
      const quantity = parseFloat(txn.quantity);
      const price = parseFloat(txn.price);
      if (isNaN(quantity) || quantity === 0 || isNaN(price) || price === 0) {
        return true; // Zero quantity or price for buy/sell
      }
    }
    return false;
  };

  // Memoized sorting logic
  const sortedTransactions = useMemo(() => {
    return [...transactions].sort((a, b) => {
      const aIsIncomplete = isTransactionIncomplete(a);
      const bIsIncomplete = isTransactionIncomplete(b);
      if (aIsIncomplete !== bIsIncomplete) {
        return aIsIncomplete ? -1 : 1; // Incomplete rows are always pushed to the top
      }
      // For rows of the same status (both complete or both incomplete), sort by date
      return new Date(b.transaction_date) - new Date(a.transaction_date);
    });
  }, [transactions]);

  // Decide whether to show the live sorted list or the "frozen" list during editing
  const transactionsToRender = editingRowId ? frozenTransactions : sortedTransactions;

  // Effect to handle scrolling to the saved row
  useEffect(() => {
    if (scrollToId && rowRefs.current[scrollToId]) {
      rowRefs.current[scrollToId].scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
      setScrollToId(null); // Reset after scrolling
    }
  }, [scrollToId, transactionsToRender]);

  const handleEdit = (id) => {
    const txToEdit = transactions.find(t => t.id === id);
    setOriginalTransaction(txToEdit); // Save state for potential cancellation
    setFrozenTransactions(sortedTransactions); // "Freeze" the current sort order
    setEditingRowId(id);
  };

  const handleSave = (id) => {
    setEditingRowId(null);
    setOriginalTransaction(null);
    setScrollToId(id); // Set the ID to scroll to after the list re-sorts
  };

  const handleCancel = (id) => {
    // Revert the transaction to its original state before editing began
    setTransactions((current) =>
      current.map((t) => (t.id === id ? originalTransaction : t))
    );
    setEditingRowId(null);
    setOriginalTransaction(null);
  };

  const handleDelete = (id) => {
    setTransactions(transactions.filter((t) => t.id !== id));
    toast.success("Transaction removed");
  };

  const handleAddNew = () => {
    const newTransaction = {
      id: `temp_${Date.now()}`,
      transaction_date: new Date().toISOString().split("T")[0],
      transaction_type: "buy",
      name: "",
      symbol: "",
      asset_id: null,
      total_amount: 0,
      quantity: 0,
      price: 0,
      fees: 0,
      notes: "",
    };
    const newMasterList = [newTransaction, ...transactions];
    setTransactions(newMasterList);

    // Freeze the view with the new transaction at the top for immediate editing
    const newFrozenList = [newTransaction, ...sortedTransactions];
    setFrozenTransactions(newFrozenList);
    setEditingRowId(newTransaction.id);
    setOriginalTransaction(newTransaction);
  };

  const handleFieldChange = (id, field, value) => {
    const updateFunction = (prev) =>
      prev.map(t => {
        if (t.id === id) {
          const updated = { ...t, [field]: value };
          if (["quantity", "price", "fees"].includes(field)) {
            const quantity = parseFloat(updated.quantity) || 0;
            const price = parseFloat(updated.price) || 0;
            const fees = parseFloat(updated.fees) || 0;
            updated.total_amount = quantity * price + fees;
          }
          return updated;
        }
        return t;
      });

    // Update both the master list and the frozen list to keep the UI in sync
    setTransactions(updateFunction);
    if (editingRowId) {
      setFrozenTransactions(updateFunction);
    }
  };

  const handleSymbolSelect = (asset, id) => {
    const changes = { symbol: asset.symbol, name: asset.name, asset_id: asset.id };
    const updateFunction = (prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...changes } : t));

    setTransactions(updateFunction);
    if (editingRowId) {
      setFrozenTransactions(updateFunction);
    }
  };

  const handleSymbolChange = (value, id) => {
    const matchedAsset = assetSymbolMap.get(value?.trim().toUpperCase());
    const changes = {
      symbol: value,
      asset_id: matchedAsset ? matchedAsset.id : null,
      name: matchedAsset ? matchedAsset.name : (value ? transactions.find(t => t.id === id)?.name : ''),
    };
    const updateFunction = (prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...changes } : t));

    setTransactions(updateFunction);
    if (editingRowId) {
      setFrozenTransactions(updateFunction);
    }
  };

  const handleBulkSave = async () => {
    if (!selectedPortfolio) return toast.error("Please select a portfolio");
    if (transactions.length === 0) return toast.error("No transactions to save");

    const incompleteTransactions = transactions.filter(isTransactionIncomplete);
    if (incompleteTransactions.length > 0) {
      return toast.error(
        `Error: ${incompleteTransactions.length} transaction(s) have incomplete data. Please correct them before importing.`
      );
    }

    setSaveErrors({});
    setIsSaving(true);

    try {
      const transactionData = transactions.map((txn) => ({
        temp_id: txn.id,
        transaction_date: txn.transaction_date,
        transaction_type: txn.transaction_type,
        symbol: txn.symbol,
        asset_id: txn.asset_id,
        quantity: parseFloat(txn.quantity) || 0,
        price: parseFloat(txn.price) || 0,
        fees: parseFloat(txn.fees) || 0,
        total_amount: parseFloat(txn.total_amount) || 0,
        notes: txn.notes || `Imported from ${parsedData.provider} statement`,
      }));

      const response = await onSave(selectedPortfolio, transactionData);

      const totalSucceeded = response?.summary?.total_created ?? 0;
      const totalFailed = response?.summary?.total_failed ?? 0;
      const errors = response?.summary?.errors || [];

      if (!response?.summary) {
        toast.error("Received an invalid response from the server.");
        setIsSaving(false);
        return;
      }

      const newSaveErrors = {};
      errors.forEach(err => {
        if (err.temp_id) {
          newSaveErrors[err.temp_id] = err.error || 'An unknown error occurred.';
        }
      });
      setSaveErrors(newSaveErrors);

      if (totalSucceeded > 0) {
        toast.success(`${totalSucceeded} transaction(s) imported successfully.`);
      }
      if (totalFailed > 0) {
        toast.error(`${totalFailed} transaction(s) failed. Please review the highlighted rows.`);
      }

      if (totalSucceeded > 0 && totalFailed === 0) {
        onCancel();
      } else if (totalSucceeded === 0 && totalFailed === 0) {
        toast.success("Import process finished. No new transactions were added.");
      }

    } catch (error) {
      console.error("Failed to save transactions:", error);
      toast.error("A critical error occurred while saving. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  // Apply search and type filters to the list being rendered
  const filteredTransactions = transactionsToRender.filter((txn) => {
    const matchesSearch = !searchQuery ||
      txn.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      txn.symbol?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterType === "all" || txn.transaction_type === filterType;
    return matchesSearch && matchesFilter;
  });

  if (!parsedData) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center"><CheckCircle className="w-5 h-5 text-white" /></div>
            <div>
              <h2 className="text-xl font-semibold text-gray-100">Review Parsed Transactions</h2>
              <p className="text-sm text-gray-400">{parsedData.provider} • {parsedData.metadata?.total_transactions || 0} transactions found</p>
            </div>
          </div>
          <button onClick={onCancel} className="text-gray-400 hover:text-gray-300 transition-colors"><X className="w-6 h-6" /></button>
        </div>
        <div className="p-6 border-b border-gray-700 space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="relative flex-1 min-w-64">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
              <input type="text" placeholder="Search transactions..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="input-field pl-10 pr-4 py-2 w-full" />
            </div>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="input-field py-2 px-3">
              <option value="all">All Types</option>
              {transactionTypes.map((type) => (<option key={type.value} value={type.value}>{type.label}</option>))}
            </select>
            <select value={selectedPortfolio} onChange={(e) => setSelectedPortfolio(e.target.value)} className="input-field py-2 px-3">
              <option value="">Select Portfolio</option>
              {portfolios.map((portfolio) => (<option key={portfolio.id} value={portfolio.id}>{portfolio.name}</option>))}
            </select>
            <button
              onClick={handleAddNew}
              className="btn-outline flex items-center space-x-2"
            >
              <Plus size={16} />
              <span>Add Transaction</span>
            </button>
          </div>
          <div className="flex items-center space-x-6 text-sm text-gray-400">
            <div className="flex items-center space-x-2">
              <span>Period:</span>
              <span className="font-medium">
                {parsedData.statement_period?.start_date} -{" "}
                {parsedData.statement_period?.end_date}
              </span>
            </div>
          </div>
        </div>
        <div className="overflow-auto flex-1">
          {parsedData.metadata?.warnings &&
            parsedData.metadata.warnings.length > 0 && (
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                <div className="flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />
                  <div className="text-sm text-yellow-200">
                    <div className="font-medium mb-1">Parsing Warnings:</div>
                    <ul className="space-y-1">
                      {parsedData.metadata.warnings.map((warning, index) => (
                        <li key={index} className="text-yellow-300/80">
                          • {warning}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          <table className="w-full">
            <thead className="bg-gray-700 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Symbol</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Quantity</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Price</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Fees</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Total</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Notes</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredTransactions.map((transaction) => {
                const saveError = saveErrors[transaction.id];
                const isIncomplete = isTransactionIncomplete(transaction);
                const isEditing = editingRowId === transaction.id;

                let rowClassName = "transition-colors";
                if (isEditing) {
                  rowClassName += " bg-primary-900/40";
                } else {
                  rowClassName += " hover:bg-gray-700/50";
                }

                if (saveError) {
                  rowClassName += " bg-danger-900/40 border-l-2 border-danger-400";
                } else if (isIncomplete) {
                  rowClassName += " bg-danger-900/20";
                }

                return (
                  <tr key={transaction.id} ref={el => (rowRefs.current[transaction.id] = el)} className={rowClassName} title={saveError ? `Error: ${saveError}` : (isIncomplete ? "This transaction has incomplete data and requires attention." : "This transaction is ready to be imported.")}>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="date" value={transaction.transaction_date} onChange={(e) => handleFieldChange(transaction.id, "transaction_date", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : transaction.transaction_date}</td>
                    <td className="px-4 py-3 text-sm">{isEditing ? <select value={transaction.transaction_type} onChange={(e) => handleFieldChange(transaction.id, "transaction_type", e.target.value)} className="input-field py-1 px-2 text-sm w-full">{transactionTypes.map((type) => (<option key={type.value} value={type.value}>{type.label}</option>))}</select> : <span className={`px-2 py-1 rounded-full text-xs font-medium ${transaction.transaction_type === "buy" ? "bg-success-500/20 text-success-400" : transaction.transaction_type === "sell" ? "bg-danger-500/20 text-danger-400" : "bg-primary-500/20 text-primary-400"}`}>{transactionTypes.find((t) => t.value === transaction.transaction_type)?.label || transaction.transaction_type}</span>}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="text" value={transaction.name} onChange={(e) => handleFieldChange(transaction.id, "name", e.target.value)} className="input-field py-1 px-2 text-sm w-full" placeholder="Company name" /> : transaction.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {isEditing ? (<div className="relative flex items-center"><ClientSideAssetSearch value={transaction.symbol || ""} onChange={(value) => handleSymbolChange(value, transaction.id)} onSelect={(asset) => handleSymbolSelect(asset, transaction.id)} placeholder="Search symbol..." showSuggestions={true} preloadAssets={true} /><div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">{transaction.symbol && (transaction.asset_id ? (<CheckCircle className="text-success-400" size={16} />) : (<AlertTriangle className="text-danger-400" size={16} />))}</div></div>) : !transaction.asset_id && transaction.symbol ? (<div className="flex items-center space-x-2 text-danger-400" title="Symbol not found. Please edit and select a valid asset."><span>{transaction.symbol}</span><AlertTriangle size={14} /></div>) : (transaction.symbol || "-")}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="number" step="any" value={transaction.quantity} onChange={(e) => handleFieldChange(transaction.id, "quantity", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : transaction.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="number" step="any" value={transaction.price} onChange={(e) => handleFieldChange(transaction.id, "price", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : `$${transaction.price?.toLocaleString() || "0.00"}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="number" step="any" value={transaction.fees} onChange={(e) => handleFieldChange(transaction.id, "fees", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : `$${transaction.fees?.toLocaleString() || "0.00"}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-300 font-medium">${transaction.total_amount?.toLocaleString() || "0.00"}</td>
                    <td className="px-4 py-3 text-sm text-gray-300 max-w-xs truncate">{isEditing ? <input type="text" value={transaction.notes} onChange={(e) => handleFieldChange(transaction.id, "notes", e.target.value)} className="input-field py-1 px-2 text-sm w-full" placeholder="Add a note..." /> : transaction.notes || "-"}</td>
                    <td className="px-4 py-3 text-sm"><div className="flex items-center space-x-2">{isEditing ? (<><button onClick={() => handleSave(transaction.id)} className="text-success-400 hover:text-success-300"><Save size={16} /></button><button onClick={() => handleCancel(transaction.id)} className="text-gray-400 hover:text-gray-300"><X size={16} /></button></>) : (<><button onClick={() => handleEdit(transaction.id)} className="text-primary-400 hover:text-primary-300"><Edit2 size={16} /></button><button onClick={() => handleDelete(transaction.id)} className="text-danger-400 hover:text-danger-300"><Trash2 size={16} /></button></>)}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-6 border-t border-gray-700">
          <div className="text-sm text-gray-400">{filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? "s" : ""} shown</div>
          <div className="flex items-center space-x-3">
            <button onClick={onCancel} className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors">Cancel</button>
            <button onClick={handleBulkSave} disabled={!selectedPortfolio || transactions.length === 0 || isSaving} className="btn-primary flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed min-w-[260px]">
              {isSaving ? (<><RefreshCw className="animate-spin" size={16} /><span>Importing...</span></>) : (<><Save size={16} /><span>Import {transactions.length} Transactions</span></>)}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParsedDataTable;