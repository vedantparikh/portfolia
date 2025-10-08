import { ChevronDown, ChevronUp, HelpCircle, Plus, Trash2 } from "lucide-react";
import PropTypes from "prop-types";
import { useEffect, useMemo, useState } from "react"; // Import useMemo
import toast from "react-hot-toast";
import assetCache from "../../services/assetCache";
import { ClientSideAssetSearch } from "../shared";

/**
 * Creates a blank transaction object with a unique temporary ID for React's key prop.
 */
const createEmptyTransaction = () => ({
  id: Date.now() + Math.random(),
  asset_id: null,
  asset: null,
  transaction_type: "buy",
  quantity: "",
  price: "",
  total_amount: "",
  fees: "",
  notes: "",
  transaction_date: new Date().toISOString().split("T")[0], // Default to today
});

const BulkTransactionModal = ({ isOpen, onClose, onSave, portfolios }) => {
  const [transactions, setTransactions] = useState([createEmptyTransaction()]);
  const [portfolioId, setPortfolioId] = useState(
    portfolios?.[0]?.id.toString() || ""
  );
  const [isSaving, setIsSaving] = useState(false);
  const [showTips, setShowTips] = useState(true);
  const [focusedRow, setFocusedRow] = useState(null);

  useEffect(() => {
    // Preload assets to make the asset dropdowns responsive
    assetCache.preloadAssets();
  }, []);

  // CHANGE 1: Use useMemo to efficiently filter for complete transactions on every render.
  // A transaction is complete if its essential fields are filled.
  const completeTransactions = useMemo(() => {
    return transactions.filter(
      (t) =>
        t.asset_id &&
        t.transaction_type &&
        t.transaction_date &&
        parseFloat(t.quantity) > 0 &&
        parseFloat(t.price) > 0
    );
  }, [transactions]);

  if (!isOpen) return null;

  /**
   * Handles input changes for any field in any row and performs automatic calculations.
   */
  const handleInputChange = (index, field, value) => {
    const newTransactions = [...transactions];
    const transaction = { ...newTransactions[index] };
    transaction[field] = value;

    // --- Automatic Calculation Logic ---
    const qty = parseFloat(transaction.quantity) || 0;
    const prc = parseFloat(transaction.price) || 0;
    const total = parseFloat(transaction.total_amount) || 0;
    const fees = parseFloat(transaction.fees) || 0;

    // Only calculate if we have valid numbers
    if (field === "quantity" || field === "price" || field === "fees") {
      // If quantity, price, or fees is changed, calculate total amount
      if (qty > 0 && prc > 0) {
        transaction.total_amount = (qty * prc + fees).toFixed(4);
      }
    } else if (field === "total_amount") {
      // If total amount is changed, calculate price or quantity
      if (total > 0) {
        if (qty > 0 && prc === 0) {
          // Calculate price: (total - fees) / quantity
          transaction.price = ((total - fees) / qty).toFixed(4);
        } else if (prc > 0 && qty === 0) {
          // Calculate quantity: (total - fees) / price
          transaction.quantity = ((total - fees) / prc).toFixed(6);
        }
      }
    }

    newTransactions[index] = transaction;
    setTransactions(newTransactions);
  };

  /**
   * Adds a new, empty transaction row to the form.
   */
  const addRow = () => {
    setTransactions([...transactions, createEmptyTransaction()]);
  };

  /**
   * Removes a transaction row from the form.
   */
  const removeRow = (index) => {
    if (transactions.length <= 1) return; // Always keep at least one row
    const newTransactions = transactions.filter((_, i) => i !== index);
    setTransactions(newTransactions);
  };

  /**
   * Validates all rows and calls the onSave prop with the formatted data.
   */
  const handleSave = async () => {
    if (!portfolioId) {
      toast.error("Please select a portfolio.");
      return;
    }

    // CHANGE 2: Check if there are any complete transactions to save.
    if (completeTransactions.length === 0) {
      toast.error("No complete transaction rows to save.");
      return;
    }

    setIsSaving(true);
    try {
      // CHANGE 3: Map only the 'completeTransactions' to the format for the API.
      const transactionsToSave = completeTransactions.map((t) => ({
        asset_id: t.asset_id,
        transaction_type: t.transaction_type,
        quantity: parseFloat(t.quantity),
        price: parseFloat(t.price),
        fees: parseFloat(t.fees) || 0,
        transaction_date: t.transaction_date,
        notes: t.notes | "Manual Bulk Creation",
        total_amount: parseFloat(t.total_amount),
      }));

      await onSave(parseInt(portfolioId), transactionsToSave);
    } catch (error) {
      // Error toast is handled in the parent component
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <h2 className="text-xl font-semibold text-gray-100">
            Bulk Transaction Entry
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-300 transition-colors"
          >
            <span className="text-3xl leading-none">&times;</span>
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto">
          {/* Portfolio Selector */}
          <div>
            <label
              htmlFor="portfolio"
              className="block text-sm font-medium text-gray-300 mb-2"
            >
              Select Portfolio
            </label>
            <select
              id="portfolio"
              value={portfolioId}
              onChange={(e) => setPortfolioId(e.target.value)}
              className="input-field w-full md:w-1/3"
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Collapsible Quick Tips */}
          <div className="bg-gray-700/50 p-4 rounded-lg">
            <button
              onClick={() => setShowTips(!showTips)}
              className="flex items-center justify-between w-full text-left text-gray-300"
            >
              <div className="flex items-center space-x-2">
                <HelpCircle size={18} />
                <span className="font-semibold">Quick Tips</span>
              </div>
              {showTips ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
            {showTips && (
              <div className="mt-3 space-y-2 text-sm text-gray-400">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <p className="font-medium text-gray-300">
                      Auto-calculation:
                    </p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>
                        Enter <strong>Quantity</strong> & <strong>Price</strong>{" "}
                        → calculates <strong>Total</strong> (includes fees)
                      </li>
                      <li>
                        Enter <strong>Total</strong> & <strong>Quantity</strong>{" "}
                        → calculates <strong>Price</strong>
                      </li>
                      <li>
                        Enter <strong>Total</strong> & <strong>Price</strong> →
                        calculates <strong>Quantity</strong>
                      </li>
                      <li>
                        <strong>Fees</strong> are added to the total amount
                      </li>
                    </ul>
                  </div>
                  <div className="space-y-1">
                    <p className="font-medium text-gray-300">Tips:</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>
                        Use the <strong>+</strong> button to add more rows
                      </li>
                      <li>Search for assets by symbol or name</li>
                      <li>
                        Only rows with Asset, Type, Quantity, Price, and Date
                        will be saved.
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Transaction Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-700 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[250px]">
                    Asset
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[100px]">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[120px]">
                    Quantity
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[120px]">
                    Price
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[100px]">
                    Fees
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[120px]">
                    Total
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[150px]">
                    Date
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[200px]">
                    Notes
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider min-w-[80px]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {transactions.map((transaction, index) => (
                  <tr key={transaction.id} className="hover:bg-gray-700/50">
                    <td
                      className={`px-4 py-3 text-sm text-gray-300 ${
                        focusedRow === index ? "relative z-20" : "relative z-10"
                      }`}
                    >
                      <div
                        onFocus={() => setFocusedRow(index)}
                        onBlur={() => setFocusedRow(null)}
                      >
                        <ClientSideAssetSearch
                          value={transaction.asset?.symbol || ""}
                          onChange={(symbol) => {
                            const newTransactions = [...transactions];
                            newTransactions[index].asset = {
                              ...newTransactions[index].asset,
                              symbol,
                            };
                            setTransactions(newTransactions);
                          }}
                          onSelect={(asset) => {
                            const newTransactions = [...transactions];
                            newTransactions[index].asset = asset;
                            newTransactions[index].asset_id = asset.id;
                            setTransactions(newTransactions);
                          }}
                          placeholder="Search assets..."
                          showSuggestions={true}
                          preloadAssets={true}
                        />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <select
                        value={transaction.transaction_type}
                        onChange={(e) =>
                          handleInputChange(
                            index,
                            "transaction_type",
                            e.target.value
                          )
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                      >
                        <option value="buy">Buy</option>
                        <option value="sell">Sell</option>
                      </select>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      <input
                        type="number"
                        placeholder="0.0000"
                        value={transaction.quantity}
                        onChange={(e) =>
                          handleInputChange(index, "quantity", e.target.value)
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                        step="0.000001"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      <input
                        type="number"
                        placeholder="0.00"
                        value={transaction.price}
                        onChange={(e) =>
                          handleInputChange(index, "price", e.target.value)
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                        step="0.01"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      <input
                        type="number"
                        placeholder="0.00"
                        value={transaction.fees}
                        onChange={(e) =>
                          handleInputChange(index, "fees", e.target.value)
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                        step="0.01"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      <input
                        type="number"
                        placeholder="0.00"
                        value={transaction.total_amount}
                        onChange={(e) =>
                          handleInputChange(
                            index,
                            "total_amount",
                            e.target.value
                          )
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                        step="0.01"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      <input
                        type="date"
                        value={transaction.transaction_date}
                        onChange={(e) =>
                          handleInputChange(
                            index,
                            "transaction_date",
                            e.target.value
                          )
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      <input
                        type="text"
                        placeholder="Optional notes"
                        value={transaction.notes}
                        onChange={(e) =>
                          handleInputChange(index, "notes", e.target.value)
                        }
                        className="input-field py-1 px-2 text-sm w-full"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => removeRow(index)}
                          disabled={transactions.length <= 1}
                          className="text-danger-400 hover:text-danger-300 disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button
            onClick={addRow}
            className="btn-outline flex items-center space-x-2"
          >
            <Plus size={16} />
            <span>Add Another Transaction</span>
          </button>
        </div>

        <div className="flex items-center justify-between p-6 border-t border-gray-700 mt-auto">
          {/* CHANGE 4: Update the footer text to use the count of complete transactions. */}
          <div className="text-sm text-gray-400">
            {completeTransactions.length} transaction
            {completeTransactions.length !== 1 ? "s" : ""} ready to save
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || completeTransactions.length === 0}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus size={16} />
              <span>
                {isSaving
                  ? "Saving..."
                  : `Save ${completeTransactions.length} Transactions`}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

BulkTransactionModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  portfolios: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      name: PropTypes.string.isRequired,
    })
  ).isRequired,
};

export default BulkTransactionModal;
