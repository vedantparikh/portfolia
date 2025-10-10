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
import React, { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { ClientSideAssetSearch } from "../shared";

const ParsedDataTable = ({
  parsedData,
  onSave,
  onCancel,
  portfolios = [],
  allAssets = [],
}) => {
  const [transactions, setTransactions] = useState([]);
  const [editingRow, setEditingRow] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveErrors, setSaveErrors] = useState({}); // e.g., { 'temp_id_123': 'Invalid symbol' }

  const transactionTypes = [
    { value: "buy", label: "Buy" },
    { value: "sell", label: "Sell" },
    { value: "dividend", label: "Dividend" },
    { value: "split", label: "Stock Split" },
    { value: "merger", label: "Merger" },
    { value: "spin_off", label: "Spin-off" },
    { value: "rights_issue", label: "Rights Issue" },
    { value: "stock_option_exercise", label: "Option Exercise" },
    { value: "transfer_in", label: "Transfer In" },
    { value: "transfer_out", label: "Transfer Out" },
    { value: "fee", label: "Fee" },
    { value: "other", label: "Other" },
  ];

  const allAssetsJson = JSON.stringify(allAssets);

  const assetSymbolMap = useMemo(() => {
    if (allAssets.length === 0) {
      return new Map();
    }
    return new Map(allAssets.map((asset) => [asset.symbol.toUpperCase(), asset]));
  }, [allAssetsJson]);

  const transactionsJson = JSON.stringify(parsedData?.transactions);

  useEffect(() => {
    const parsedTransactions = transactionsJson ? JSON.parse(transactionsJson) : [];
    if (!parsedTransactions || parsedTransactions.length === 0) {
      setTransactions([]);
      return;
    }
    const initialTransactions = parsedTransactions.map((t, index) => {
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
  }, [transactionsJson, assetSymbolMap]);

  const handleEdit = (index) => setEditingRow(index);
  const handleSave = (index) => setEditingRow(null);
  const handleCancel = () => setEditingRow(null);

  const handleDelete = (index) => {
    setTransactions(transactions.filter((_, i) => i !== index));
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
    setTransactions([newTransaction, ...transactions]);
    setEditingRow(0);
  };

  const handleFieldChange = (index, field, value) => {
    const newTransactions = [...transactions];
    const updatedTransaction = { ...newTransactions[index], [field]: value };

    if (["quantity", "price", "fees"].includes(field)) {
      const quantity = parseFloat(updatedTransaction.quantity) || 0;
      const price = parseFloat(updatedTransaction.price) || 0;
      const fees = parseFloat(updatedTransaction.fees) || 0;
      updatedTransaction.total_amount = quantity * price + fees;
    }
    newTransactions[index] = updatedTransaction;
    setTransactions(newTransactions);
  };

  const handleSymbolSelect = (asset, index) => {
    handleFieldChange(index, "symbol", asset.symbol);
    handleFieldChange(index, "name", asset.name);
    handleFieldChange(index, "asset_id", asset.id);
  };

  const handleSymbolChange = (value, index) => {
    const newTransactions = [...transactions];
    const updatedTransaction = { ...newTransactions[index], symbol: value };
    const matchedAsset = assetSymbolMap.get(value?.trim().toUpperCase());
    if (matchedAsset) {
      updatedTransaction.asset_id = matchedAsset.id;
      updatedTransaction.name = matchedAsset.name;
    } else {
      updatedTransaction.asset_id = null;
      if (!value) updatedTransaction.name = "";
    }
    newTransactions[index] = updatedTransaction;
    setTransactions(newTransactions);
  };

  const handleBulkSave = async () => {
    if (!selectedPortfolio) return toast.error("Please select a portfolio");
    if (transactions.length === 0) return toast.error("No transactions to save");

    // This pre-save validation is good to keep.
    const transactionsWithUnmatchedSymbol = transactions.filter(
      (txn) => txn.symbol && !txn.asset_id
    );

    if (transactionsWithUnmatchedSymbol.length > 0) {
      return toast.error(
        `Error: ${transactionsWithUnmatchedSymbol.length} transaction(s) have an unmatched symbol. Please correct them before importing.`
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

      // The 'onSave' call now receives the actual API response.
      const response = await onSave(selectedPortfolio, transactionData);

      // --- NEW LOGIC STARTS HERE ---

      // 1. Use the ACTUAL keys from your API response, defaulting to 0 for safety.
      const totalSucceeded = response?.summary?.total_created ?? 0;
      const totalFailed = response?.summary?.total_failed ?? 0;
      const errors = response?.summary?.errors || [];

      // 2. Check if the response format is what we expect.
      if (!response?.summary) {
        toast.error("Received an invalid response from the server.");
        setIsSaving(false); // Stop the spinner
        return;
      }
      
      // 3. Process and display errors on the failed rows.
      // This assumes your `errors` array contains objects like { temp_id: '...', error: '...' }
      const newSaveErrors = {};
      errors.forEach(err => {
        if (err.temp_id) {
          newSaveErrors[err.temp_id] = err.error || 'An unknown error occurred.';
        }
      });
      setSaveErrors(newSaveErrors);

      // 4. Display toast messages based on the outcome.
      if (totalSucceeded > 0) {
        toast.success(`${totalSucceeded} transaction(s) imported successfully.`);
      }
      if (totalFailed > 0) {
        toast.error(`${totalFailed} transaction(s) failed. Please review the highlighted rows.`);
      }

      // 5. IMPORTANT: Only close the modal on a FULL success.
      // If any transactions failed, the modal stays open for the user to review.
      if (totalSucceeded > 0 && totalFailed === 0) {
        onCancel(); // Close the modal
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

  const filteredTransactions = transactions.filter((txn) => {
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
            <thead className="bg-gray-700 sticky top-0">
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
              {filteredTransactions.map((transaction, index) => {
                const saveError = saveErrors[transaction.id];
                const needsAsset = !transaction.asset_id;

                let rowClassName = "hover:bg-gray-700/50 transition-colors";
                if (saveError) {
                  rowClassName += " bg-danger-900/40 border-l-2 border-danger-400";
                } else if (needsAsset) {
                  rowClassName += " bg-danger-900/20";
                }

                return (
                  <tr key={transaction.id} className={rowClassName} title={saveError ? `Error: ${saveError}` : "This transaction is ready to be imported."}>
                    <td className="px-4 py-3 text-sm text-gray-300">{editingRow === index ? <input type="date" value={transaction.transaction_date} onChange={(e) => handleFieldChange(index, "transaction_date", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : transaction.transaction_date}</td>
                    <td className="px-4 py-3 text-sm">{editingRow === index ? <select value={transaction.transaction_type} onChange={(e) => handleFieldChange(index, "transaction_type", e.target.value)} className="input-field py-1 px-2 text-sm w-full">{transactionTypes.map((type) => (<option key={type.value} value={type.value}>{type.label}</option>))}</select> : <span className={`px-2 py-1 rounded-full text-xs font-medium ${transaction.transaction_type === "buy" ? "bg-success-500/20 text-success-400" : transaction.transaction_type === "sell" ? "bg-danger-500/20 text-danger-400" : "bg-primary-500/20 text-primary-400"}`}>{transactionTypes.find((t) => t.value === transaction.transaction_type)?.label || transaction.transaction_type}</span>}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{editingRow === index ? <input type="text" value={transaction.name} onChange={(e) => handleFieldChange(index, "name", e.target.value)} className="input-field py-1 px-2 text-sm w-full" placeholder="Company name" /> : transaction.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {editingRow === index ? (<div className="relative flex items-center"><ClientSideAssetSearch value={transaction.symbol || ""} onChange={(value) => handleSymbolChange(value, index)} onSelect={(asset) => handleSymbolSelect(asset, index)} placeholder="Search symbol..." showSuggestions={true} preloadAssets={true} />{transaction.symbol && (<div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">{transaction.asset_id ? (<CheckCircle className="text-success-400" size={16} />) : (<AlertTriangle className="text-danger-400" size={16} />)}</div>)}</div>) : !transaction.asset_id && transaction.symbol ? (<div className="flex items-center space-x-2 text-danger-400" title="Symbol not found. Please edit and select a valid asset."><span>{transaction.symbol}</span><AlertTriangle size={14} /></div>) : (transaction.symbol || "-")}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">{editingRow === index ? <input type="number" step="0.0001" value={transaction.quantity} onChange={(e) => handleFieldChange(index, "quantity", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : transaction.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{editingRow === index ? <input type="number" step="0.01" value={transaction.price} onChange={(e) => handleFieldChange(index, "price", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : `$${transaction.price || "0.00"}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{editingRow === index ? <input type="number" step="0.01" value={transaction.fees} onChange={(e) => handleFieldChange(index, "fees", e.target.value)} className="input-field py-1 px-2 text-sm w-full" /> : `$${transaction.fees || "0.00"}`}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">${transaction.total_amount || "0.00"}</td>
                    <td className="px-4 py-3 text-sm text-gray-300 max-w-xs truncate">{editingRow === index ? <input type="text" value={transaction.notes} onChange={(e) => handleFieldChange(index, "notes", e.target.value)} className="input-field py-1 px-2 text-sm w-full" placeholder="Add a note..." /> : transaction.notes || "-"}</td>
                    <td className="px-4 py-3 text-sm"><div className="flex items-center space-x-2">{editingRow === index ? (<><button onClick={() => handleSave(index)} className="text-success-400 hover:text-success-300"><Save size={16} /></button><button onClick={handleCancel} className="text-gray-400 hover:text-gray-300"><X size={16} /></button></>) : (<><button onClick={() => handleEdit(index)} className="text-primary-400 hover:text-primary-300"><Edit2 size={16} /></button><button onClick={() => handleDelete(index)} className="text-danger-400 hover:text-danger-300"><Trash2 size={16} /></button></>)}</div></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-6 border-t border-gray-700">
          <div className="text-sm text-gray-400">{filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? "s" : ""} ready to import</div>
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