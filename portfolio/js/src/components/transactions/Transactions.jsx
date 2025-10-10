import {
  Activity,
  ArrowLeft,
  Download,
  FileText,
  Filter,
  Plus,
  RefreshCw,
  Search,
  Zap,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  accountStatementsAPI,
  portfolioAPI,
  transactionAPI,
} from "../../services/api";
import assetCache from "../../services/assetCache";
import { Sidebar } from "../shared";
import BulkTransactionModal from "./BulkTransactionModal";
import CreateTransactionModal from "./CreateTransactionModal";
import EditTransactionModal from "./EditTransactionModal";
import PDFUploadModal from "./PDFUploadModal";
import ParsedDataTable from "./ParsedDataTable";
import TransactionCard from "./TransactionCard";
import TransactionExportModal from "./TransactionExportModal";
import TransactionFilters from "./TransactionFilters";

const Transactions = () => {
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [showPDFUpload, setShowPDFUpload] = useState(false);
  const [showParsedData, setShowParsedData] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [filters, setFilters] = useState({
    portfolio: "all",
    type: "all",
    dateRange: "all",
    sortBy: "created_at",
    sortOrder: "desc",
  });

  // Load data on component mount and preload assets
  useEffect(() => {
    loadData();
    // Preload assets in the background for faster transaction creation
    assetCache.preloadAssets();
  }, []);

  // Filter transactions when search query or filters change
  useEffect(() => {
    filterTransactions();
  }, [transactions, searchQuery, filters]);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load portfolios
      const portfoliosResponse = await portfolioAPI.getPortfolios();
      setPortfolios(portfoliosResponse || []);

      // Load transactions
      const transactionsResponse = await transactionAPI.getTransactions({
        limit: 10000,
        order_by: "transaction_date",
        order: "desc",
      });
      setTransactions(transactionsResponse || []);
    } catch (error) {
      console.error("Failed to load data:", error);
      toast.error("Failed to load transaction data");
    } finally {
      setLoading(false);
    }
  };

  const filterTransactions = () => {
    let filtered = [...transactions];

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (transaction) =>
          (transaction.asset.symbol || "")
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          (transaction.asset.name || "")
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          (transaction.portfolio.name || "")
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          (transaction.notes || "")
            .toLowerCase()
            .includes(searchQuery.toLowerCase())
      );
    }

    // Portfolio filter
    if (filters.portfolio !== "all") {
      filtered = filtered.filter(
        (transaction) =>
          transaction.portfolio_id === parseInt(filters.portfolio)
      );
    }

    // Type filter
    if (filters.type !== "all") {
      filtered = filtered.filter(
        (transaction) =>
          transaction.transaction_type === filters.type ||
          transaction.type === filters.type
      );
    }

    // Date range filter
    if (filters.dateRange !== "all") {
      const now = new Date();
      const filterDate = new Date();

      switch (filters.dateRange) {
        case "today":
          filterDate.setHours(0, 0, 0, 0);
          break;
        case "week":
          filterDate.setDate(now.getDate() - 7);
          break;
        case "month":
          filterDate.setMonth(now.getMonth() - 1);
          break;
        case "quarter":
          filterDate.setMonth(now.getMonth() - 3);
          break;
        case "year":
          filterDate.setFullYear(now.getFullYear() - 1);
          break;
      }

      filtered = filtered.filter((transaction) => {
        const transactionDate = new Date(transaction.transaction_date);
        return transactionDate >= filterDate;
      });
    }

    // Sort
    filtered.sort((a, b) => {
      let aValue, bValue;

      switch (filters.sortBy) {
        case "created_at":
          aValue = new Date(a.transaction_date);
          bValue = new Date(b.transaction_date);
          break;
        case "amount":
          aValue = a.total_amount || 0;
          bValue = b.total_amount || 0;
          break;
        case "symbol":
          aValue = (a.symbol || "").toLowerCase();
          bValue = (b.symbol || "").toLowerCase();
          break;
        case "type":
          aValue = (a.transaction_type || a.type || "").toLowerCase();
          bValue = (b.transaction_type || b.type || "").toLowerCase();
          break;
        default:
          aValue = new Date(a.transaction_date);
          bValue = new Date(b.transaction_date);
      }

      if (filters.sortOrder === "asc") {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    setFilteredTransactions(filtered);
  };

  const handleCreateTransaction = async (transactionData) => {
    try {
      await transactionAPI.createTransaction(transactionData);
      setShowCreateModal(false);
      toast.success("Transaction created successfully");
      await loadData(); // Reload data to get the new transaction
    } catch (error) {
      console.error("Failed to create transaction:", error);
      const errorMessage =
        error.response?.data?.detail ||
        error.message ||
        "Failed to create transaction";
      toast.error(errorMessage);
      throw error;
    }
  };

  const handleUpdateTransaction = async (transactionId, transactionData) => {
    try {
      const response = await transactionAPI.updateTransaction(
        transactionId,
        transactionData
      );
      setTransactions((prev) =>
        prev.map((t) => (t.id === transactionId ? response : t))
      );
      setShowEditModal(false);
      setEditingTransaction(null);
      toast.success("Transaction updated successfully");
    } catch (error) {
      console.error("Failed to update transaction:", error);
      toast.error("Failed to update transaction");
    }
  };

  const handleDeleteTransaction = async (transactionId) => {
    try {
      await transactionAPI.deleteTransaction(transactionId);
      setTransactions((prev) => prev.filter((t) => t.id !== transactionId));
      toast.success("Transaction deleted successfully");
    } catch (error) {
      console.error("Failed to delete transaction:", error);
      toast.error("Failed to delete transaction");
    }
  };

  const handleEditTransaction = (transaction) => {
    setEditingTransaction(transaction);
    setShowEditModal(true);
  };

  const handleRefresh = () => {
    loadData();
    toast.success("Transaction data refreshed");
  };

  const handleQuickAction = (action) => {
    switch (action) {
      case "create-transaction":
        setShowCreateModal(true);
        break;
      case "refresh":
        handleRefresh();
        break;
      case "upload-pdf":
        setShowPDFUpload(true);
        break;
      case "bulk-transaction":
        setShowBulkModal(true);
        break;
      case "export-pdf":
        setShowExportModal(true);
        break;
      default:
        break;
    }
  };

  const handleParsedData = (data) => {
    setParsedData(data);
    setShowPDFUpload(false);
    setShowParsedData(true);
  };

  const handleCancelParsedData = () => {
    setShowParsedData(false);
    setParsedData(null);
  };

  // ✅ CORRECTED FUNCTION
  // This function now waits for the bulk creation and then triggers a full, safe data reload.
  const handleBulkCreate = async (portfolioId, transactionData, options) => {
    const { onSuccess, context } = options;

    try {
      const response = await accountStatementsAPI.bulkCreateTransactions(
        portfolioId,
        transactionData
      );

      // Call the specific success handler passed in options (e.g., to close the modal)
      onSuccess();

      const verb = context === "import" ? "imported" : "created";
      toast.success(
        `Successfully ${verb} ${
          response.summary?.total_created || transactionData.length
        } transactions. Refreshing list...`
      );

      // Instead of adding partial data, we reload everything to ensure data integrity.
      await loadData();
    } catch (error) {
      const verb = context === "import" ? "import" : "create";
      console.error(`Failed to bulk ${verb} transactions:`, error);
      toast.error(`Failed to ${verb} transactions`);
      throw error;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading transactions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex">
      <Sidebar
        currentView="transactions"
        portfolios={portfolios}
        selectedPortfolio={
          portfolios.find((p) => p.id === parseInt(filters.portfolio)) || null
        }
        onPortfolioChange={(portfolio) =>
          setFilters((prev) => ({ ...prev, portfolio: portfolio?.id || "all" }))
        }
        onRefresh={handleRefresh}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        showFilters={showFilters}
        onToggleFilters={() => setShowFilters(!showFilters)}
        stats={null}
        recentTransactions={filteredTransactions.slice(0, 5)}
        onQuickAction={handleQuickAction}
      />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto p-6">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-4">
                <a
                  href="/dashboard"
                  className="flex items-center space-x-2 text-gray-400 hover:text-gray-300 transition-colors"
                >
                  <ArrowLeft size={20} />
                  <span>Back to Dashboard</span>
                </a>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleRefresh}
                  className="btn-secondary flex items-center space-x-2"
                >
                  <RefreshCw size={16} />
                  <span>Refresh</span>
                </button>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="btn-outline flex items-center space-x-2"
                >
                  <Filter size={16} />
                  <span>Filters</span>
                </button>
                <button
                  onClick={() => setShowPDFUpload(true)}
                  className="btn-outline flex items-center space-x-2"
                >
                  <FileText size={16} />
                  <span>Upload PDF</span>
                </button>
                <button
                  onClick={() => setShowBulkModal(true)}
                  className="btn-outline flex items-center space-x-2"
                >
                  <Zap size={16} />
                  <span>Bulk Entry</span>
                </button>
                <button
                  onClick={() => setShowExportModal(true)}
                  className="btn-outline flex items-center space-x-2"
                >
                  <Download size={16} />
                  <span>Export PDF</span>
                </button>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn-primary flex items-center space-x-2"
                >
                  <Plus size={16} />
                  <span>New Transaction</span>
                </button>
              </div>
            </div>

            <div className="mb-4">
              <h1 className="text-3xl font-bold text-gray-100 mb-2">
                Transactions
              </h1>
              <p className="text-gray-400">
                Track and manage your trading activity
              </p>
            </div>

            {/* Search Bar */}
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                size={20}
              />
              <input
                type="text"
                placeholder="Search transactions by symbol, asset name, or portfolio..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field w-full pl-10 pr-4 py-3"
              />
            </div>
          </div>

          {/* Filters */}
          {showFilters && (
            <div className="card p-6 mb-8">
              <TransactionFilters
                filters={filters}
                portfolios={portfolios}
                onFilterChange={setFilters}
              />
            </div>
          )}

          {/* Transactions List */}
          {filteredTransactions.length === 0 ? (
            <div className="space-y-6">
              <div className="card p-12 text-center">
                <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-300 mb-2">
                  No transactions found
                </h3>
                <p className="text-gray-500 mb-6">
                  {searchQuery
                    ? "Try adjusting your search criteria"
                    : "Start by creating your first transaction"}
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn-primary flex items-center space-x-2 mx-auto"
                >
                  <Plus size={16} />
                  <span>Create Transaction</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredTransactions.map((transaction) => (
                <TransactionCard
                  key={transaction.id}
                  transaction={transaction}
                  onEdit={() => handleEditTransaction(transaction)}
                  onDelete={() => handleDeleteTransaction(transaction.id)}
                />
              ))}
            </div>
          )}

          {/* Create Transaction Modal */}
          {showCreateModal && (
            <CreateTransactionModal
              portfolios={portfolios}
              onClose={() => setShowCreateModal(false)}
              onCreate={handleCreateTransaction}
            />
          )}

          {/* Edit Transaction Modal */}
          {showEditModal && editingTransaction && (
            <EditTransactionModal
              isOpen={showEditModal}
              onClose={() => {
                setShowEditModal(false);
                setEditingTransaction(null);
              }}
              transaction={editingTransaction}
              portfolios={portfolios}
              onUpdate={handleUpdateTransaction}
            />
          )}

          {/* PDF Upload Modal */}
          {showPDFUpload && (
            <PDFUploadModal
              isOpen={showPDFUpload}
              onClose={() => setShowPDFUpload(false)}
              onParsedData={handleParsedData}
            />
          )}

          {/* Parsed Data Table Modal */}
          {showParsedData && parsedData && (
            <ParsedDataTable
              parsedData={parsedData}
              onSave={(portfolioId, data) =>
                handleBulkCreate(portfolioId, data, {
                  onSuccess: handleCancelParsedData,
                  context: "import",
                })
              }
              onCancel={handleCancelParsedData}
              portfolios={portfolios}
            />
          )}

          {/* Bulk Transaction Modal */}
          {showBulkModal && (
            <BulkTransactionModal
              isOpen={showBulkModal}
              onClose={() => setShowBulkModal(false)}
              onSave={(portfolioId, data) =>
                handleBulkCreate(portfolioId, data, {
                  onSuccess: () => setShowBulkModal(false),
                  context: "create",
                })
              }
              portfolios={portfolios}
            />
          )}

          {/* Export Modal */}
          {showExportModal && (
            <TransactionExportModal
              isOpen={showExportModal}
              onClose={() => setShowExportModal(false)}
              portfolios={portfolios}
              transactions={filteredTransactions}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Transactions;
