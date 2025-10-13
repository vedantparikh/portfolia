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
import React, { useEffect, useMemo, useRef, useState } from "react";
import toast from "react-hot-toast";
import assetCache from "../../services/assetCache";
import transactionTypes from "../../utils/transactionTypes";
import { ClientSideAssetSearch } from "../shared";

const ParsedDataTable = ({
  parsedData,
  onSave,
  onCancel,
  portfolios = [],
  allAssets = [],
}) => {
  const [transactions, setTransactions] = useState([]);
  const [transactionsToRender, setTransactionsToRender] = useState([]);
  const [editingRowId, setEditingRowId] = useState(null);
  const [originalRowData, setOriginalRowData] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const rowRefs = useRef({});

  // Sync allAssets with assetCache so ClientSideAssetSearch can use them
  useEffect(() => {
    if (allAssets && allAssets.length > 0) {
      assetCache.assets = allAssets;
      assetCache.lastFetched = Date.now();
      assetCache.notifySubscribers();
    }
  }, [allAssets]);

  // Process and match transactions against assets
  useEffect(() => {
    if (!parsedData?.transactions) {
      setTransactions([]);
      return;
    }

    // Build asset map inside the effect to ensure we have latest allAssets
    const assetSymbolMap = new Map(
      allAssets.map((asset) => [asset.symbol.toUpperCase(), asset])
    );

    const processedTransactions = parsedData.transactions.map((t, index) => {
      const cleanSymbol = t.symbol?.trim().toUpperCase();
      const matchedAsset = assetSymbolMap.get(cleanSymbol);
      return {
        ...t,
        symbol: t.symbol?.trim() || "",
        id: t.id || `initial_${index}`,
        asset_id: matchedAsset?.id || null,
        name: matchedAsset?.name || t.name || "",
        quantity: parseFloat(t.quantity) || 0,
        price: parseFloat(t.price) || 0,
        fees: parseFloat(t.fees) || 0,
        total_amount: parseFloat(t.total_amount) || 0,
        notes: t.notes || "",
      };
    });
    setTransactions(processedTransactions);
  }, [parsedData, allAssets]);

  // Build asset symbol map for handlers
  const assetSymbolMap = useMemo(() => {
    if (!allAssets || allAssets.length === 0) return new Map();
    return new Map(allAssets.map((asset) => [asset.symbol.toUpperCase(), asset]));
  }, [allAssets]);

  const isTransactionIncomplete = (txn) => {
    if (!txn.asset_id && txn.symbol) return true;
    if (["buy", "sell"].includes(txn.transaction_type?.toLowerCase())) {
      if (txn.quantity === 0 || txn.price === 0) return true;
    }
    return false;
  };

  const sortedTransactions = useMemo(() => {
    return [...transactions].sort((a, b) => {
      const aIsIncomplete = isTransactionIncomplete(a);
      const bIsIncomplete = isTransactionIncomplete(b);
      if (aIsIncomplete !== bIsIncomplete) return aIsIncomplete ? -1 : 1;
      return new Date(b.transaction_date) - new Date(a.transaction_date);
    });
  }, [transactions]);

  const filteredTransactions = useMemo(() => {
    return sortedTransactions.filter((txn) => {
      const search = searchQuery.toLowerCase();
      const matchesSearch = !search || txn.name?.toLowerCase().includes(search) || txn.symbol?.toLowerCase().includes(search);
      const matchesFilter = filterType === "all" || txn.transaction_type === filterType;
      return matchesSearch && matchesFilter;
    });
  }, [sortedTransactions, searchQuery, filterType]);

  useEffect(() => {
    if (!editingRowId) {
      setTransactionsToRender(filteredTransactions);
    }
  }, [filteredTransactions, editingRowId]);

  const handleEdit = (id) => {
    const rowToEdit = transactions.find((t) => t.id === id);
    setOriginalRowData(rowToEdit);
    setTransactionsToRender(filteredTransactions);
    setEditingRowId(id);
  };

  const handleCancel = (id) => {
    const newMasterList = transactions.map(t => t.id === id ? originalRowData : t);
    setTransactions(newMasterList);
    setEditingRowId(null);
    setOriginalRowData(null);
  };

  const handleSave = (id) => {
    setEditingRowId(null);
    setOriginalRowData(null);
    setTimeout(() => {
      rowRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  };

  const handleDelete = (id) => {
    setTransactions((current) => current.filter((t) => t.id !== id));
    toast.success("Transaction removed");
  };

  const handleAddNew = () => {
    const newId = `temp_${Date.now()}`;
    const newTransaction = {
      id: newId, transaction_date: new Date().toISOString().split("T")[0],
      transaction_type: "buy", name: "", symbol: "", asset_id: null,
      quantity: 0, price: 0, fees: 0, total_amount: 0, notes: "",
    };
    const newMasterList = [newTransaction, ...transactions];
    setTransactions(newMasterList);
    setTransactionsToRender([newTransaction, ...filteredTransactions]);
    setOriginalRowData(newTransaction);
    setEditingRowId(newId);
    setTimeout(() => {
      rowRefs.current[newId]?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  };

  const handleFieldChange = (id, field, value) => {
    const applyChanges = (t) => {
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
    };
    setTransactions(prev => prev.map(applyChanges));
    setTransactionsToRender(prev => prev.map(applyChanges));
  };

  const handleSymbolChange = (id, symbolValue) => {
    const matchedAsset = assetSymbolMap.get(symbolValue?.trim().toUpperCase());
    const applyChanges = t => {
      if (t.id === id) {
        return {
          ...t,
          symbol: symbolValue,
          asset_id: matchedAsset ? matchedAsset.id : null,
          name: matchedAsset ? matchedAsset.name : (symbolValue ? t.name : ''),
        };
      }
      return t;
    };
    setTransactions(prev => prev.map(applyChanges));
    setTransactionsToRender(prev => prev.map(applyChanges));
  };

  const handleSymbolSelect = (id, asset) => {
    const applyChanges = t => t.id === id ? { ...t, symbol: asset.symbol, name: asset.name, asset_id: asset.id } : t;
    setTransactions(prev => prev.map(applyChanges));
    setTransactionsToRender(prev => prev.map(applyChanges));
  };

  const handleBulkSave = async () => {
    if (!selectedPortfolio) return toast.error("Please select a portfolio.");
    const incompleteCount = transactions.filter(isTransactionIncomplete).length;
    if (incompleteCount > 0) {
      return toast.error(`${incompleteCount} transaction(s) have incomplete data and require attention.`);
    }

    setIsSaving(true);
    setSaveErrors({});
    const payload = transactions.map((txn) => ({
      transaction_date: txn.transaction_date,
      transaction_type: txn.transaction_type,
      asset_id: txn.asset_id,
      quantity: txn.quantity,
      price: txn.price,
      fees: txn.fees,
      total_amount: txn.total_amount,
      notes: txn.notes || `Imported from ${parsedData?.provider ?? 'unknown source'} statement`,
    }));

    try {
      const response = await onSave(parseInt(selectedPortfolio, 10), payload);
      if (!response?.summary) throw new Error("Invalid server response.");

      const { total_created = 0, total_failed = 0, errors = [] } = response.summary;

      // Display errors as toasts since backend returns error strings, not per-transaction errors
      if (errors.length > 0) {
        errors.forEach(errorMsg => toast.error(errorMsg, { duration: 5000 }));
      }

      if (total_created > 0) toast.success(`${total_created} transaction(s) imported.`);
      if (total_failed > 0 && errors.length === 0) {
        toast.error(`${total_failed} transaction(s) failed to import.`);
      }
      if (total_created > 0 && total_failed === 0) onCancel();

    } catch (error) {
      console.error("Bulk save failed:", error);
      toast.error("A critical error occurred while saving.");
    } finally {
      setIsSaving(false);
    }
  };

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
            <button onClick={handleAddNew} className="btn-outline flex items-center space-x-2"><Plus size={16} /><span>Add Transaction</span></button>
          </div>
        </div>

        <div className="overflow-auto flex-1 p-6">
          {parsedData.metadata?.warnings && parsedData.metadata.warnings.length > 0 && (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mb-4">
              <div className="flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />
                <div className="text-sm text-yellow-200">
                  <div className="font-medium mb-1">Parsing Warnings:</div>
                  <ul className="space-y-1">
                    {parsedData.metadata.warnings.map((warning, index) => (
                      <li key={index} className="text-yellow-300/80">• {warning}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          <table className="w-full">
            <thead className="bg-gray-700 sticky top-0 z-10">
              <tr>
                {["Date", "Type", "Name", "Symbol", "Quantity", "Price", "Fees", "Total", "Notes", "Actions"].map(h => <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{h}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {transactionsToRender.map((txn) => {
                const isEditing = editingRowId === txn.id;
                const isIncomplete = isTransactionIncomplete(txn);
                let rowClassName = "transition-colors";
                if (isEditing) rowClassName += " bg-primary-900/40";
                else rowClassName += " hover:bg-gray-700/50";
                if (isIncomplete) rowClassName += " bg-danger-900/20";

                return (
                  <tr key={txn.id} ref={el => (rowRefs.current[txn.id] = el)} className={rowClassName}>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="date" value={txn.transaction_date} onChange={(e) => handleFieldChange(txn.id, "transaction_date", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : txn.transaction_date}</td>
                    <td className="px-4 py-3 text-sm">{isEditing ? <select value={txn.transaction_type} onChange={(e) => handleFieldChange(txn.id, "transaction_type", e.target.value)} className="input-field py-1 px-2 text-sm w-full">{transactionTypes.map((t) => (<option key={t.value} value={t.value}>{t.label}</option>))}</select> : <span className={`px-2 py-1 rounded-full text-xs font-medium ${txn.transaction_type === "buy" ? "bg-success-500/20 text-success-400" : txn.transaction_type === "sell" ? "bg-danger-500/20 text-danger-400" : "bg-primary-500/20 text-primary-400"}`}>{transactionTypes.find((t) => t.value === txn.transaction_type)?.label || txn.transaction_type}</span>}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="text" value={txn.name} onChange={(e) => handleFieldChange(txn.id, "name", e.target.value)} className="input-field py-1 px-2 text-sm w-full" placeholder="Company name" /> : txn.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {isEditing ? (
                        <div className="relative flex items-center">
                          <ClientSideAssetSearch
                            key={`search-${txn.id}`}
                            value={txn.symbol}
                            onChange={(value) => handleSymbolChange(txn.id, value)}
                            onSelect={(asset) => handleSymbolSelect(txn.id, asset)}
                            preloadAssets={false}
                          />
                          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                            {txn.symbol && (txn.asset_id ? <CheckCircle className="text-success-400" size={16} /> : <AlertTriangle className="text-danger-400" size={16} />)}
                          </div>
                        </div>
                      ) : (
                        !txn.asset_id && txn.symbol ? (<div className="flex items-center space-x-2 text-danger-400" title="Symbol not found."><span>{txn.symbol}</span><AlertTriangle size={14} /></div>) : (txn.symbol || "-")
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="number" step="any" value={txn.quantity} onChange={(e) => handleFieldChange(txn.id, "quantity", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : txn.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="number" step="any" value={txn.price} onChange={(e) => handleFieldChange(txn.id, "price", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : `$${txn.price?.toLocaleString() || "0.00"}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{isEditing ? <input type="number" step="any" value={txn.fees} onChange={(e) => handleFieldChange(txn.id, "fees", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : `$${txn.fees?.toLocaleString() || "0.00"}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-300 font-medium">${txn.total_amount?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || "0.00"}</td>
                    <td className="px-4 py-3 text-sm text-gray-300 max-w-xs truncate">{isEditing ? <input type="text" value={txn.notes} onChange={(e) => handleFieldChange(txn.id, "notes", e.target.value)} className="input-field py-1 px-2 text-sm w-full" placeholder="Add a note..." /> : txn.notes || "-"}</td>
                    <td className="px-4 py-3 text-sm"><div className="flex items-center space-x-2">{isEditing ? (<><button onClick={() => handleSave(txn.id)} className="text-success-400 hover:text-success-300"><Save size={16} /></button><button onClick={() => handleCancel(txn.id)} className="text-gray-400 hover:text-gray-300"><X size={16} /></button></>) : (<><button onClick={() => handleEdit(txn.id)} className="text-primary-400 hover:text-primary-300"><Edit2 size={16} /></button><button onClick={() => handleDelete(txn.id)} className="text-danger-400 hover:text-danger-300"><Trash2 size={16} /></button></>)}</div></td>
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