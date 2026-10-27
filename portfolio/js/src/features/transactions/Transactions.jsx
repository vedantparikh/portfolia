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
  Menu,
} from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { InView } from "react-intersection-observer";
import { useLocation } from "react-router";

import {
  accountStatementsAPI,
  apiErrorMessage,
  portfolioAPI,
  transactionAPI,
} from "../../services/api";
import { useQueryClient } from "@tanstack/react-query";
import { assetKeys, useAssets } from "../../shared/api/queries";
import { usePageChrome, useShell } from "../../app/chrome";
import useIsMobile from "../../hooks/useIsMobile";
import LoadingSpinner from "../../components/shared/LoadingSpinner";
import BulkTransactionModal from "./BulkTransactionModal";
import CreateTransactionModal from "./CreateTransactionModal";
import EditTransactionModal from "./EditTransactionModal";
import PDFUploadModal from "./PDFUploadModal";
import ParsedDataTable from "./ParsedDataTable";
import TransactionCard from "./TransactionCard";
import TransactionExportModal from "./TransactionExportModal";
import TransactionFilters from "./TransactionFilters";

const RENDER_PAGE_SIZE = 50; // How many items to render at a time

const Transactions = () => {
  const location = useLocation();
  const [allTransactions, setAllTransactions] = useState([]);
  const [visibleTransactions, setVisibleTransactions] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const isMobile = useIsMobile();
  const { openSidebar } = useShell();
  const [showPDFUpload, setShowPDFUpload] = useState(false);
  const [showParsedData, setShowParsedData] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [allAssets, setAllAssets] = useState([]);
  const queryClient = useQueryClient();
  const { data: cachedAssets } = useAssets();
  const [visibleCount, setVisibleCount] = useState(RENDER_PAGE_SIZE);
  const [initialPortfolioId, setInitialPortfolioId] = useState(null);

  const [filters, setFilters] = useState({
    portfolio: "all",
    type: "all",
    dateRange: "all",
    sortBy: "transaction_date",
    sortOrder: "desc",
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [portfoliosResponse, transactionsResponse] = await Promise.all([
        portfolioAPI.getPortfolios(),
        transactionAPI.getTransactions({
          limit: 10000, // Fetch all transactions
          order_by: "transaction_date",
          order: "desc",
        }),
      ]);
      setPortfolios(portfoliosResponse || []);
      setAllTransactions(transactionsResponse || []);
    } catch (error) {
      console.error("Failed to load data:", error);
      toast.error("Failed to load transaction data");
    } finally {
      setLoading(false);
    }
  };

  // Effect for initial data load and asset preloading
  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    setAllAssets(cachedAssets || []);
  }, [cachedAssets]);

  // This useEffect checks for navigation state on component load
  useEffect(() => {
    const navState = location.state;
    // If the action from Portfolio.js is present, open the modal
    if (navState?.action === "createTransaction" && navState?.portfolioId) {
      setInitialPortfolioId(navState.portfolioId);
      setShowCreateModal(true);

      // Clean up the state to prevent the modal from re-opening on refresh
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Effect for filtering and paginating the displayed transactions
  useEffect(() => {
    let filtered = [...allTransactions];

    // Apply search filter
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

    // Apply other filters
    if (filters.portfolio !== "all") {
      filtered = filtered.filter(
        (t) => t.portfolio_id === parseInt(filters.portfolio)
      );
    }
    if (filters.type !== "all") {
      filtered = filtered.filter(
        (t) => t.transaction_type === filters.type || t.type === filters.type
      );
    }
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
      filtered = filtered.filter(
        (t) => new Date(t.transaction_date) >= filterDate
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue, bValue;
      switch (filters.sortBy) {
        case "transaction_date":
          aValue = new Date(a.transaction_date);
          bValue = new Date(b.transaction_date);
          break;
        case "amount":
          aValue = a.total_amount || 0;
          bValue = b.total_amount || 0;
          break;
        case "symbol":
          aValue = (a.asset?.symbol || "").toLowerCase();
          bValue = (b.asset?.symbol || "").toLowerCase();
          break;
        case "type":
          aValue = (a.transaction_type || a.type || "").toLowerCase();
          bValue = (b.transaction_type || b.type || "").toLowerCase();
          break;
        default:
          aValue = new Date(a.transaction_date);
          bValue = new Date(b.transaction_date);
      }
      return filters.sortOrder === "asc"
        ? aValue > bValue
          ? 1
          : -1
        : aValue < bValue
        ? 1
        : -1;
    });

    setVisibleTransactions(filtered.slice(0, visibleCount));
  }, [allTransactions, filters, searchQuery, visibleCount]);

  // Effect to reset visible count when filters change
  useEffect(() => {
    setVisibleCount(RENDER_PAGE_SIZE);
  }, [filters, searchQuery]);

  const handleRefresh = () => {
    loadData();
    toast.success("Transaction data refreshed");
  };

  const handleCreateTransaction = async (transactionData) => {
    try {
      await transactionAPI.createTransaction(transactionData);
      setShowCreateModal(false);
      toast.success("Transaction created successfully");
      handleRefresh();
    } catch (error) {
      console.error("Failed to create transaction:", error);
      toast.error(
        apiErrorMessage(error, "Failed to create transaction")
      );
      throw error;
    }
  };

  const handleUpdateTransaction = async (transactionId, transactionData) => {
    try {
      const response = await transactionAPI.updateTransaction(
        transactionId,
        transactionData
      );
      setAllTransactions((prev) =>
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
      setAllTransactions((prev) => prev.filter((t) => t.id !== transactionId));
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

  const handleQuickAction = (action) => {
    if (action === "create-transaction") setShowCreateModal(true);
    if (action === "refresh") handleRefresh();
    if (action === "upload-pdf") setShowPDFUpload(true);
    if (action === "bulk-transaction") setShowBulkModal(true);
    if (action === "export-pdf") setShowExportModal(true);
  };

  usePageChrome({
    portfolios,
    selectedPortfolio:
      portfolios.find((p) => p.id === parseInt(filters.portfolio)) || null,
    searchQuery,
    onPortfolioChange: (portfolio) =>
      setFilters((prev) => ({ ...prev, portfolio: portfolio?.id || "all" })),
    onSearchChange: setSearchQuery,
    onQuickAction: handleQuickAction,
  });

  const handleParsedData = (data) => {
    setParsedData(data);
    setShowPDFUpload(false);
    setShowParsedData(true);
  };

  const handleCancelParsedData = () => {
    setShowParsedData(false);
    setParsedData(null);
    queryClient.removeQueries({ queryKey: assetKeys.all });
  };

  const handleBulkCreate = async (
    portfolioId,
    transactionData,
    options = {}
  ) => {
    const { context, onSuccess } = options;
    try {
      const response = await accountStatementsAPI.bulkCreateTransactions(
        portfolioId,
        transactionData
      );
      const created = response.summary?.total_created ?? 0;
      if (context === "create") {
        if (created > 0) {
          onSuccess();
          toast.success(`Created ${created} transaction(s).`);
        } else {
          toast.error("No transactions were created.");
        }
        (response.summary?.errors ?? []).forEach((message) =>
          toast.error(message, { duration: 5000 })
        );
      }
      if (created > 0) handleRefresh();
      return response;
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
        <LoadingSpinner
          type="transaction"
          size="lg"
          text="Loading transactions..."
          centered
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex">
      <div className="flex-1 min-w-0 overflow-y-auto">
        {isMobile && (
          <div className="bg-dark-900 border-b border-dark-700 p-4 flex items-center justify-between">
            <button
              onClick={openSidebar}
              aria-label="Open menu"
              className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
            >
              <Menu size={20} className="text-gray-400" />
            </button>
            <h1 className="text-lg font-semibold text-gray-100">Transactions</h1>
            <div className="w-10" />
          </div>
        )}
        <div className="max-w-7xl mx-auto p-4 sm:p-6">
          <div className="mb-8">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <a
                href="/dashboard"
                aria-label="Back to Dashboard"
                className="flex items-center space-x-2 text-gray-400 hover:text-gray-300"
              >
                <ArrowLeft size={20} />
                <span className="hidden sm:inline">Back to Dashboard</span>
              </a>
              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <button
                  onClick={handleRefresh}
                  className="btn-secondary flex items-center space-x-2"
                  aria-label="Refresh"
                  title="Refresh"
                >
                  <RefreshCw size={16} />
                  <span className="hidden sm:inline">Refresh</span>
                </button>
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="btn-outline flex items-center space-x-2"
                  aria-label="Filters"
                  title="Filters"
                >
                  <Filter size={16} />
                  <span className="hidden sm:inline">Filters</span>
                </button>
                <button
                  onClick={() => setShowPDFUpload(true)}
                  className="btn-outline flex items-center space-x-2"
                  aria-label="Import statement"
                  title="Import statement"
                >
                  <FileText size={16} />
                  <span className="hidden sm:inline">Import statement</span>
                </button>
                <button
                  onClick={() => setShowBulkModal(true)}
                  className="btn-outline flex items-center space-x-2"
                  aria-label="Bulk Entry"
                  title="Bulk Entry"
                >
                  <Zap size={16} />
                  <span className="hidden sm:inline">Bulk Entry</span>
                </button>
                <button
                  onClick={() => setShowExportModal(true)}
                  className="btn-outline flex items-center space-x-2"
                  aria-label="Export"
                  title="Export"
                >
                  <Download size={16} />
                  <span className="hidden sm:inline">Export</span>
                </button>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn-primary flex items-center space-x-2 whitespace-nowrap"
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
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                size={20}
              />
              <input
                type="text"
                placeholder="Search by symbol, name, portfolio, or notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field w-full pl-10 pr-4 py-3"
              />
            </div>
          </div>

          {showFilters && (
            <div className="card p-6 mb-8">
              <TransactionFilters
                filters={filters}
                portfolios={portfolios}
                onFilterChange={setFilters}
              />
            </div>
          )}

          {visibleTransactions.length === 0 ? (
            <div className="card p-12 text-center">
              <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-300 mb-2">
                No transactions found
              </h3>
              <p className="text-gray-500 mb-6">
                {searchQuery ||
                filters.portfolio !== "all" ||
                filters.type !== "all" ||
                filters.dateRange !== "all"
                  ? "Try adjusting your search or filter criteria"
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
          ) : (
            <div className="space-y-2">
              {visibleTransactions.map((transaction, index) => (
                <TransactionCard
                  key={`${transaction.id}-${index}`}
                  transaction={transaction}
                  onEdit={() => handleEditTransaction(transaction)}
                  onDelete={() => handleDeleteTransaction(transaction.id)}
                />
              ))}
            </div>
          )}

          <InView
            as="div"
            onChange={(inView) => {
              if (inView) {
                setVisibleCount((prevCount) => prevCount + RENDER_PAGE_SIZE);
              }
            }}
          >
            {visibleTransactions.length <
              allTransactions.filter((t) => {
                // A rough check to see if more can be loaded
                if (searchQuery)
                  return (t.asset.symbol || "")
                    .toLowerCase()
                    .includes(searchQuery.toLowerCase());
                return true;
              }).length && (
              <div className="flex justify-center items-center p-4 mt-4">
                <LoadingSpinner
                  type="transaction"
                  size="md"
                  text="Loading more transactions..."
                />
              </div>
            )}
          </InView>

          {/* MODALS */}
          {showCreateModal && (
            <CreateTransactionModal
              portfolios={portfolios}
              onClose={() => {
                setShowCreateModal(false), setInitialPortfolioId(null);
              }}
              onCreate={handleCreateTransaction}
              initialPortfolioId={initialPortfolioId}
            />
          )}
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
          {showPDFUpload && (
            <PDFUploadModal
              isOpen={showPDFUpload}
              onClose={() => setShowPDFUpload(false)}
              onParsedData={handleParsedData}
            />
          )}
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
              allAssets={allAssets}
            />
          )}
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
          {showExportModal && (
            <TransactionExportModal
              isOpen={showExportModal}
              onClose={() => setShowExportModal(false)}
              portfolios={portfolios}
              transactions={allTransactions} // Export all transactions
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Transactions;
