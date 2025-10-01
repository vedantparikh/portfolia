import {
  Activity,
  ArrowLeft,
  BarChart3,
  DollarSign,
  PieChart,
  Plus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { portfolioAPI, transactionAPI } from "../../services/api";
import {
  formatCurrency,
  formatDateTime,
  formatQuantity,
} from "../../utils/formatters";
import { Sidebar } from "../shared";
import CreatePortfolioModal from "./CreatePortfolioModal";
import EditPortfolioModal from "./EditPortfolioModal";
import PortfolioAssets from "./PortfolioAssets";
import PortfolioCard from "./PortfolioCard";
import PortfolioChart from "./PortfolioChart";
import PortfolioDetail from "./PortfolioDetail";
import PortfolioPerformanceMetrics from "./PortfolioPerformanceMetrics";

const Portfolio = () => {
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingPortfolio, setEditingPortfolio] = useState(null);
  const [viewMode, setViewMode] = useState("overview"); // overview, detail, chart, assets, performance
  const [portfolioStats, setPortfolioStats] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Load portfolios on component mount
  useEffect(() => {
    loadPortfolios();
  }, []);

  // Load portfolio details when selected
  useEffect(() => {
    if (selectedPortfolio) {
      loadPortfolioDetails(selectedPortfolio.id);
    }
  }, [selectedPortfolio]);

  // Check for mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const loadPortfolios = async () => {
    try {
      setLoading(true);
      console.log("[Portfolio] Loading portfolios...");
      const response = await portfolioAPI.getPortfolios();
      console.log("[Portfolio] Portfolios response:", response);

      // Use consistent API response format
      const portfolios = Array.isArray(response) ? response : [];

      console.log("[Portfolio] Processed portfolios:", portfolios);
      setPortfolios(portfolios);

      // Select first portfolio by default
      if (portfolios.length > 0) {
        console.log("[Portfolio] Selecting first portfolio:", portfolios[0]);
        setSelectedPortfolio(portfolios[0]);
      } else {
        console.log("[Portfolio] No portfolios found");
        setSelectedPortfolio(null);
      }
    } catch (error) {
      console.error("Failed to load portfolios:", error);
      // Show more specific error message
      if (error.response?.status === 401) {
        toast.error("Authentication failed. Please login again.");
      } else if (error.response?.status === 404) {
        toast.error(
          "Portfolio service not found. Please check if the backend is running."
        );
      } else if (error.response?.status >= 500) {
        toast.error("Server error. Please try again later.");
      } else if (
        error.code === "NETWORK_ERROR" ||
        error.message.includes("Network Error")
      ) {
        toast.error(
          "Network error. Please check if the backend server is running on http://localhost:8000"
        );
      } else {
        toast.error(`Failed to load portfolios: ${error.message}`);
      }
      setPortfolios([]);
      setSelectedPortfolio(null);
    } finally {
      setLoading(false);
    }
  };

  const loadPortfolioDetails = async (portfolioId) => {
    try {
      console.log("[Portfolio] Loading details for portfolio:", portfolioId);

      // Load portfolio summary
      try {
        const summaryResponse = await portfolioAPI.getPortfolioSummary(
          portfolioId
        );
        console.log("[Portfolio] Summary response:", summaryResponse);
        setPortfolioStats(summaryResponse);
      } catch (summaryError) {
        console.warn("Failed to load portfolio summary:", summaryError);
        // Set default stats if summary fails
        setPortfolioStats({
          total_value: 0,
          total_cost: 0,
          day_change: 0,
          total_assets: 0,
          total_transactions: 0,
        });
      }

      // Load recent transactions
      try {
        const transactionsResponse =
          await transactionAPI.getPortfolioTransactions(portfolioId, {
            limit: 10,
            order_by: "created_at",
            order: "desc",
          });
        console.log("[Portfolio] Transactions response:", transactionsResponse);

        // Use consistent API response format
        const transactions = Array.isArray(transactionsResponse)
          ? transactionsResponse
          : [];

        setTransactions(transactions);
      } catch (transactionError) {
        console.warn("Failed to load transactions:", transactionError);
        setTransactions([]);
      }
    } catch (error) {
      console.error("Failed to load portfolio details:", error);
      if (error.response?.status === 404) {
        toast.error("Portfolio not found");
      } else if (
        error.code === "NETWORK_ERROR" ||
        error.message.includes("Network Error")
      ) {
        toast.error("Network error. Please check backend connectivity.");
      } else {
        toast.error(`Failed to load portfolio details: ${error.message}`);
      }
      setPortfolioStats(null);
      setTransactions([]);
    }
  };

  const handleCreatePortfolio = async (portfolioData) => {
    try {
      console.log("[Portfolio] Creating portfolio with data:", portfolioData);
      const response = await portfolioAPI.createPortfolio(portfolioData);
      console.log("[Portfolio] Create response:", response);

      // Use consistent API response format
      const newPortfolio = response;

      setPortfolios((prev) => [...prev, newPortfolio]);
      setSelectedPortfolio(newPortfolio);
      setShowCreateModal(false);
      toast.success("Portfolio created successfully");

      // Load details for the new portfolio
      if (newPortfolio && newPortfolio.id) {
        loadPortfolioDetails(newPortfolio.id);
      }
    } catch (error) {
      console.error("Failed to create portfolio:", error);
      if (error.response?.status === 400) {
        toast.error("Invalid portfolio data. Please check your inputs.");
      } else if (error.response?.status === 401) {
        toast.error("Authentication failed. Please login again.");
      } else if (
        error.code === "NETWORK_ERROR" ||
        error.message.includes("Network Error")
      ) {
        toast.error("Network error. Please check backend connectivity.");
      } else {
        toast.error(
          `Failed to create portfolio: ${
            error.response?.data?.detail || error.message
          }`
        );
      }
    }
  };

  const handleUpdatePortfolio = async (portfolioId, portfolioData) => {
    try {
      console.log("[Portfolio] Updating portfolio with data:", portfolioData);
      const response = await portfolioAPI.updatePortfolio(
        portfolioId,
        portfolioData
      );
      console.log("[Portfolio] Update response:", response);

      // Handle different response formats
      let updatedPortfolio = response;
      if (response && response.portfolio) {
        updatedPortfolio = response.portfolio;
      } else if (response && response.data) {
        updatedPortfolio = response.data;
      }

      setPortfolios((prev) =>
        prev.map((p) => (p.id === portfolioId ? updatedPortfolio : p))
      );

      // Update selected portfolio if it's the one being edited
      if (selectedPortfolio && selectedPortfolio.id === portfolioId) {
        setSelectedPortfolio(updatedPortfolio);
      }

      setShowEditModal(false);
      setEditingPortfolio(null);
      toast.success("Portfolio updated successfully");

      // Reload portfolio details to reflect changes
      if (updatedPortfolio && updatedPortfolio.id) {
        loadPortfolioDetails(updatedPortfolio.id);
      }
    } catch (error) {
      console.error("Failed to update portfolio:", error);
      if (error.response?.status === 400) {
        toast.error("Invalid portfolio data. Please check your inputs.");
      } else if (error.response?.status === 401) {
        toast.error("Authentication failed. Please login again.");
      } else if (error.response?.status === 404) {
        toast.error("Portfolio not found.");
      } else if (
        error.code === "NETWORK_ERROR" ||
        error.message.includes("Network Error")
      ) {
        toast.error("Network error. Please check backend connectivity.");
      } else {
        toast.error(
          `Failed to update portfolio: ${
            error.response?.data?.detail || error.message
          }`
        );
      }
    }
  };

  const handleDeletePortfolio = async (portfolioId) => {
    try {
      console.log("[Portfolio] Deleting portfolio:", portfolioId);
      await portfolioAPI.deletePortfolio(portfolioId);

      const updatedPortfolios = portfolios.filter((p) => p.id !== portfolioId);
      setPortfolios(updatedPortfolios);

      // If deleted portfolio was selected, select another one
      if (selectedPortfolio && selectedPortfolio.id === portfolioId) {
        if (updatedPortfolios.length > 0) {
          setSelectedPortfolio(updatedPortfolios[0]);
          loadPortfolioDetails(updatedPortfolios[0].id);
        } else {
          setSelectedPortfolio(null);
          setPortfolioStats(null);
          setTransactions([]);
        }
      }

      toast.success("Portfolio deleted successfully");
    } catch (error) {
      console.error("Failed to delete portfolio:", error);
      if (error.response?.status === 401) {
        toast.error("Authentication failed. Please login again.");
      } else if (error.response?.status === 404) {
        toast.error("Portfolio not found or already deleted.");
      } else if (error.response?.status === 403) {
        toast.error("Permission denied. You cannot delete this portfolio.");
      } else if (
        error.code === "NETWORK_ERROR" ||
        error.message.includes("Network Error")
      ) {
        toast.error("Network error. Please check backend connectivity.");
      } else {
        toast.error(
          `Failed to delete portfolio: ${
            error.response?.data?.detail || error.message
          }`
        );
      }
    }
  };

  const handleEditPortfolio = (portfolio) => {
    setEditingPortfolio(portfolio);
    setShowEditModal(true);
  };

  const handleRefresh = () => {
    loadPortfolios();
    if (selectedPortfolio) {
      loadPortfolioDetails(selectedPortfolio.id);
    }
    toast.success("Portfolio data refreshed");
  };

  const handleQuickAction = (action) => {
    switch (action) {
      case "create-portfolio":
        setShowCreateModal(true);
        break;
      case "refresh":
        handleRefresh();
        break;
      default:
        break;
    }
  };

  const getTotalStats = () => {
    if (!portfolioStats) return null;

    const totalValue = portfolioStats.total_current_value || 0;
    const totalCost = portfolioStats.total_cost_basis || 0;
    const totalGainLoss = portfolioStats.total_unrealized_pnl || 0;
    const totalGainLossPercent = portfolioStats.total_unrealized_pnl_percent || 0;
    const dayChange = portfolioStats.today_pnl || 0;
    const dayChangePercent = portfolioStats.today_pnl_percent || 0;

    return {
      totalValue,
      totalCost,
      totalGainLoss,
      totalGainLossPercent,
      dayChange,
      dayChangePercent,
      totalHoldings: portfolioStats.total_assets || 0,
      totalTransactions: portfolioStats.total_transactions || 0,
    };
  };

  const stats = getTotalStats();

  if (loading) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading portfolios...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex">
      <Sidebar
        currentView="portfolio"
        portfolios={portfolios}
        selectedPortfolio={selectedPortfolio}
        onPortfolioChange={setSelectedPortfolio}
        onRefresh={handleRefresh}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        showFilters={showFilters}
        onToggleFilters={() => setShowFilters(!showFilters)}
        stats={stats}
        recentTransactions={transactions.slice(0, 5)}
        onQuickAction={handleQuickAction}
        isMobile={isMobile}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      {/* Mobile Overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <div className="flex-1 overflow-y-auto">
        {/* Mobile Header */}
        {isMobile && (
          <div className="bg-dark-900 border-b border-dark-700 p-4 flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
            >
              <BarChart3 size={20} className="text-gray-400" />
            </button>
            <h1 className="text-lg font-semibold text-gray-100">Portfolio</h1>
            <div className="w-10" /> {/* Spacer for centering */}
          </div>
        )}
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
                  onClick={() => setShowCreateModal(true)}
                  className="btn-primary flex items-center space-x-2"
                >
                  <Plus size={16} />
                  <span>New Portfolio</span>
                </button>
              </div>
            </div>

            <div className="mb-4">
              <h1 className="text-3xl font-bold text-gray-100 mb-2">
                Portfolio
              </h1>
              <p className="text-gray-400">Manage your investment portfolios</p>
            </div>

            {/* Portfolio Selector */}
            {portfolios.length > 0 && (
              <div className="flex items-center space-x-4 mb-6">
                <label className="text-sm font-medium text-gray-300">
                  Active Portfolio:
                </label>
                <select
                  value={selectedPortfolio?.id || ""}
                  onChange={(e) => {
                    const portfolio = portfolios.find(
                      (p) => p.id === parseInt(e.target.value)
                    );
                    setSelectedPortfolio(portfolio);
                  }}
                  className="input-field"
                >
                  {portfolios.map((portfolio) => (
                    <option key={portfolio.id} value={portfolio.id}>
                      {portfolio.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {portfolios.length === 0 ? (
            /* Empty State */
            <div className="space-y-6">
              <div className="card p-12 text-center">
                <Wallet className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-300 mb-2">
                  No portfolios yet
                </h3>
                <p className="text-gray-500 mb-6">
                  Create your first portfolio to start tracking your investments
                </p>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn-primary flex items-center space-x-2 mx-auto"
                >
                  <Plus size={16} />
                  <span>Create Portfolio</span>
                </button>
              </div>

              {/* Debug Info */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold text-gray-100 mb-4">
                  Debug Info
                </h3>
                <div className="space-y-2 text-sm">
                  <div>Loading: {loading ? "true" : "false"}</div>
                  <div>Portfolios count: {portfolios.length}</div>
                  <div>
                    Selected portfolio:{" "}
                    {selectedPortfolio ? selectedPortfolio.name : "none"}
                  </div>
                  <div>
                    Portfolio stats: {portfolioStats ? "loaded" : "not loaded"}
                  </div>
                  <div>Transactions count: {transactions.length}</div>
                </div>
              </div>
            </div>
          ) : (
            <>
              {/* Portfolio Stats */}
              {stats && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                  <div className="card p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">Total Value</p>
                        <p className="text-2xl font-bold text-gray-100">
                          ${stats.totalValue.toLocaleString()}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                        <DollarSign size={24} className="text-primary-400" />
                      </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm">
                      <span
                        className={
                          stats.totalGainLoss >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                        }
                      >
                        {stats.totalGainLoss >= 0 ? "+" : ""}$
                        {stats.totalGainLoss.toLocaleString()}
                      </span>
                      <span className="text-gray-400 ml-2">
                        ({stats.totalGainLossPercent.toFixed(2)}%)
                      </span>
                    </div>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">Day Change</p>
                        <p
                          className={`text-2xl font-bold ${
                            stats.dayChange >= 0
                              ? "text-success-400"
                              : "text-danger-400"
                          }`}
                        >
                          {stats.dayChange >= 0 ? "+" : ""}$
                          {stats.dayChange.toLocaleString()}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                        {stats.dayChange >= 0 ? (
                          <TrendingUp size={24} className="text-success-400" />
                        ) : (
                          <TrendingDown size={24} className="text-danger-400" />
                        )}
                      </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm">
                      <span
                        className={
                          stats.dayChangePercent >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                        }
                      >
                        {stats.dayChangePercent >= 0 ? "+" : ""}
                        {stats.dayChangePercent.toFixed(2)}%
                      </span>
                      <span className="text-gray-400 ml-2">today</span>
                    </div>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">Holdings</p>
                        <p className="text-2xl font-bold text-gray-100">
                          {stats.totalHoldings}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-warning-600/20 rounded-lg flex items-center justify-center">
                        <BarChart3 size={24} className="text-warning-400" />
                      </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm">
                      <span className="text-gray-400">Active positions</span>
                    </div>
                  </div>

                  <div className="card p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-400">Transactions</p>
                        <p className="text-2xl font-bold text-gray-100">
                          {stats.totalTransactions}
                        </p>
                      </div>
                      <div className="w-12 h-12 bg-gray-600/20 rounded-lg flex items-center justify-center">
                        <Activity size={24} className="text-gray-400" />
                      </div>
                    </div>
                    <div className="mt-4 flex items-center text-sm">
                      <span className="text-gray-400">Total trades</span>
                    </div>
                  </div>
                </div>
              )}

              {/* View Mode Toggle */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setViewMode("overview")}
                    className={`p-2 rounded-lg transition-colors ${
                      viewMode === "overview"
                        ? "bg-primary-600 text-white"
                        : "bg-dark-700 text-gray-400 hover:bg-dark-600"
                    }`}
                    title="Overview"
                  >
                    <BarChart3 size={16} />
                  </button>
                  <button
                    onClick={() => setViewMode("detail")}
                    className={`p-2 rounded-lg transition-colors ${
                      viewMode === "detail"
                        ? "bg-primary-600 text-white"
                        : "bg-dark-700 text-gray-400 hover:bg-dark-600"
                    }`}
                    title="Holdings Detail"
                  >
                    <PieChart size={16} />
                  </button>
                  <button
                    onClick={() => setViewMode("assets")}
                    className={`p-2 rounded-lg transition-colors ${
                      viewMode === "assets"
                        ? "bg-primary-600 text-white"
                        : "bg-dark-700 text-gray-400 hover:bg-dark-600"
                    }`}
                    title="Portfolio Assets"
                  >
                    <Wallet size={16} />
                  </button>
                  <button
                    onClick={() => setViewMode("chart")}
                    className={`p-2 rounded-lg transition-colors ${
                      viewMode === "chart"
                        ? "bg-primary-600 text-white"
                        : "bg-dark-700 text-gray-400 hover:bg-dark-600"
                    }`}
                    title="Performance Chart"
                  >
                    <Activity size={16} />
                  </button>
                  <button
                    onClick={() => setViewMode("performance")}
                    className={`p-2 rounded-lg transition-colors ${
                      viewMode === "performance"
                        ? "bg-primary-600 text-white"
                        : "bg-dark-700 text-gray-400 hover:bg-dark-600"
                    }`}
                    title="Performance Metrics"
                  >
                    <BarChart3 size={16} />
                  </button>
                </div>
              </div>

              {/* Portfolio Content */}
              {selectedPortfolio && (
                <div className="space-y-6">
                  {viewMode === "overview" && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <PortfolioCard
                        portfolio={selectedPortfolio}
                        stats={stats}
                        onEdit={handleEditPortfolio}
                        onDelete={handleDeletePortfolio}
                        onAddPosition={(portfolio) => {
                          // TODO: Implement add position functionality
                          toast.info("Add position functionality coming soon!");
                        }}
                        onViewDetails={(portfolio) => {
                          setViewMode("detail");
                        }}
                      />
                      <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4">
                          Recent Transactions
                        </h3>
                        {transactions.length > 0 ? (
                          <div className="space-y-3">
                            {transactions.slice(0, 5).map((transaction) => (
                              <div
                                key={transaction.id}
                                className="flex items-center justify-between p-3 bg-dark-800 rounded-lg"
                              >
                                <div className="flex items-center space-x-3">
                                  <div
                                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                      transaction.transaction_type === "buy"
                                        ? "bg-success-400/20"
                                        : "bg-danger-400/20"
                                    }`}
                                  >
                                    {transaction.transaction_type === "buy" ? (
                                      <TrendingUp
                                        size={16}
                                        className="text-success-400"
                                      />
                                    ) : (
                                      <TrendingDown
                                        size={16}
                                        className="text-danger-400"
                                      />
                                    )}
                                  </div>
                                  <div>
                                    <p className="text-sm font-medium text-gray-100">
                                      {transaction.transaction_type.toUpperCase()}{" "}
                                      - {transaction.asset.symbol}
                                    </p>
                                    <p className="text-xs text-gray-400">
                                      {formatDateTime(transaction.created_at)}
                                    </p>
                                  </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                  <p className="text-sm text-gray-400">
                                    {transaction.portfolio.name}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p
                                    className={`text-sm font-medium ${
                                      transaction.transaction_type === "buy"
                                        ? "text-success-400"
                                        : "text-danger-400"
                                    }`}
                                  >
                                    {transaction.transaction_type === "buy"
                                      ? "-"
                                      : "+"}
                                    {formatCurrency(transaction.total_amount)}
                                  </p>
                                  <p className="text-xs text-gray-400">
                                    {formatQuantity(transaction.quantity)} @{" "}
                                    {formatCurrency(transaction.price)}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-gray-400 text-center py-8">
                            No transactions yet
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {viewMode === "detail" && selectedPortfolio && (
                    <PortfolioDetail
                      portfolio={selectedPortfolio}
                      stats={stats}
                      transactions={transactions}
                    />
                  )}

                  {viewMode === "assets" && selectedPortfolio && (
                    <PortfolioAssets
                      portfolio={selectedPortfolio}
                      onRefresh={handleRefresh}
                    />
                  )}

                  {viewMode === "chart" && selectedPortfolio && (
                    <PortfolioChart
                      portfolio={selectedPortfolio}
                      stats={stats}
                    />
                  )}

                  {viewMode === "performance" && selectedPortfolio && (
                    <PortfolioPerformanceMetrics
                      portfolio={selectedPortfolio}
                    />
                  )}
                </div>
              )}
            </>
          )}

          {/* Create Portfolio Modal */}
          {showCreateModal && (
            <CreatePortfolioModal
              onClose={() => setShowCreateModal(false)}
              onCreate={handleCreatePortfolio}
            />
          )}

          {/* Edit Portfolio Modal */}
          {showEditModal && editingPortfolio && (
            <EditPortfolioModal
              isOpen={showEditModal}
              onClose={() => {
                setShowEditModal(false);
                setEditingPortfolio(null);
              }}
              portfolio={editingPortfolio}
              onUpdate={handleUpdatePortfolio}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Portfolio;
