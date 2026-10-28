import { CurrencyProvider } from "../../contexts/CurrencyContext";
import {
  Activity,
  ArrowLeft,
  BarChart3,
  PieChart,
  Plus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router";
import { API_BASE_URL, apiErrorMessage, portfolioAPI } from "../../services/api";
import {
  portfolioKeys,
  usePortfolioAccountSummary,
  usePortfolios,
  useRecentPortfolioTransactions,
} from "../../shared/api/queries";
import {
  formatCurrency,
  formatDateTime,
  formatQuantity,
} from "../../utils/formatters";
import { usePageChrome, useShell } from "../../app/chrome";
import { LoadingSpinner } from "../../components/shared";
import CreatePortfolioModal from "./CreatePortfolioModal";
import EditPortfolioModal from "./EditPortfolioModal";
import PortfolioAssets from "./PortfolioAssets";
import PortfolioCard from "./PortfolioCard";
import PortfolioChart from "./PortfolioChart";
import PortfolioDetail from "./PortfolioDetail";
import PortfolioPerformanceMetrics from "./PortfolioPerformanceMetrics";

const noPortfolios = [];

const Portfolio = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const portfoliosQuery = usePortfolios();
  const portfolios = portfoliosQuery.data ?? noPortfolios;
  const [selectedId, setSelectedId] = useState(null);
  const selectedPortfolio =
    portfolios.find((portfolio) => portfolio.id === selectedId) ?? null;
  const summaryQuery = usePortfolioAccountSummary(selectedId);
  const recentQuery = useRecentPortfolioTransactions(selectedId);
  const portfolioStats = summaryQuery.data ?? null;
  const transactions = recentQuery.data ?? noPortfolios;
  const detailsLoading =
    selectedPortfolio !== null &&
    (summaryQuery.isPending || recentQuery.isPending);
  const [showCreateModal, setShowCreateModal] = useState(
    () => location.state?.action === "createPortfolio"
  );
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    if (location.state?.action === "createPortfolio") {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);
  const [editingPortfolio, setEditingPortfolio] = useState(null);
  const [viewMode, setViewMode] = useState("overview"); // overview, detail, chart, assets, performance
  const [searchQuery, setSearchQuery] = useState("");
  const [isMobile, setIsMobile] = useState(false);
  const { openSidebar } = useShell();

  useEffect(() => {
    const list = portfoliosQuery.data;
    if (!list) return;
    setSelectedId((current) => {
      if (list.length === 0) return null;
      if (current != null && list.some((portfolio) => portfolio.id === current)) {
        return current;
      }
      return list[0].id;
    });
  }, [portfoliosQuery.data]);

  useEffect(() => {
    const error = portfoliosQuery.error;
    if (!error) return;
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
      error.message?.includes("Network Error")
    ) {
      toast.error(
        `Network error: is the API at ${API_BASE_URL} reachable from this browser?`
      );
    } else {
      toast.error(`Failed to load portfolios: ${error.message}`);
    }
  }, [portfoliosQuery.error]);

  // Check for mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const refreshPortfolios = () =>
    queryClient.invalidateQueries({ queryKey: portfolioKeys.all });

  const handleCreatePortfolio = async (portfolioData) => {
    try {
      console.log("[Portfolio] Creating portfolio with data:", portfolioData);
      const response = await portfolioAPI.createPortfolio(portfolioData);
      console.log("[Portfolio] Create response:", response);

      const newPortfolio = response;

      await refreshPortfolios();
      if (newPortfolio?.id) setSelectedId(newPortfolio.id);
      setShowCreateModal(false);
      toast.success("Portfolio created successfully");
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
            apiErrorMessage(error, error.message)
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

      await refreshPortfolios();

      setShowEditModal(false);
      setEditingPortfolio(null);
      toast.success("Portfolio updated successfully");
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
            apiErrorMessage(error, error.message)
          }`
        );
      }
    }
  };

  const handleDeletePortfolio = async (portfolioId) => {
    try {
      console.log("[Portfolio] Deleting portfolio:", portfolioId);
      await portfolioAPI.deletePortfolio(portfolioId);
      if (selectedId === portfolioId) setSelectedId(null);
      await refreshPortfolios();

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
            apiErrorMessage(error, error.message)
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
    refreshPortfolios();
    toast.success("Portfolio data refreshed");
  };

  const handleQuickAction = (action) => {
    if (action === "create-portfolio") setShowCreateModal(true);
    else if (action === "refresh") handleRefresh();
    else return false;
    return true;
  };

  usePageChrome({
    portfolios,
    selectedPortfolio,
    searchQuery,
    onPortfolioChange: (portfolio) => setSelectedId(portfolio?.id ?? null),
    onSearchChange: setSearchQuery,
    onQuickAction: handleQuickAction,
  });

  const getTotalStats = () => {
    if (!portfolioStats) return null;

    const totalValue = portfolioStats.total_current_value || 0;
    const totalCost = portfolioStats.total_cost_basis || 0;
    const totalGainLoss = portfolioStats.total_unrealized_pnl || 0;
    const totalGainLossPercent =
      portfolioStats.total_unrealized_pnl_percent || 0;
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

  // Use portfoliosLoading for the initial full-screen spinner
  if (portfoliosQuery.isPending) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner
            type="analyst"
            size="lg"
            text="Loading portfolios..."
            centered
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex">
      <div className="flex-1 min-w-0 overflow-y-auto">
        {/* Mobile Header */}
        {isMobile && (
          <div className="bg-dark-900 border-b border-dark-700 p-4 flex items-center justify-between">
            <button
              onClick={openSidebar}
              className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
            >
              <BarChart3 size={20} className="text-gray-400" />
            </button>
            <h1 className="text-lg font-semibold text-gray-100">Portfolio</h1>
            <div className="w-10" /> {/* Spacer for centering */}
          </div>
        )}
        <div className="max-w-7xl mx-auto p-4 sm:p-6">
          {/* Header */}
          <div className="mb-8">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex items-center space-x-4">
                <a
                  href="/dashboard"
                  className="flex items-center space-x-2 text-gray-400 hover:text-gray-300 transition-colors"
                  aria-label="Back to Dashboard"
                >
                  <ArrowLeft size={20} />
                  <span className="hidden sm:inline">Back to Dashboard</span>
                </a>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleRefresh}
                  className="btn-secondary flex items-center space-x-2 whitespace-nowrap"
                >
                  <RefreshCw size={16} />
                  <span>Refresh</span>
                </button>
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="btn-primary flex items-center space-x-2 whitespace-nowrap"
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
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 mb-6">
                <label className="text-sm font-medium text-gray-300">
                  Active Portfolio:
                </label>
                <select
                  value={selectedPortfolio?.id || ""}
                  onChange={(e) => {
                    const portfolio = portfolios.find(
                      (p) => p.id === parseInt(e.target.value)
                    );
                    setSelectedId(portfolio.id);
                  }}
                  className="input-field w-full sm:w-auto max-w-full"
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
            </div>
          ) : (
            <>
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
                <CurrencyProvider currency={selectedPortfolio.currency}>
                <div className="space-y-6">
                  {viewMode === "overview" && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      {/* CHANGED: Conditional rendering for Portfolio Card */}
                      {detailsLoading || !stats ? (
                        <div className="card p-6 flex items-center justify-center min-h-[300px]">
                          <LoadingSpinner
                            type="analyst"
                            text="Loading portfolio stats..."
                            centered
                          />
                        </div>
                      ) : (
                        <PortfolioCard
                          portfolio={selectedPortfolio}
                          stats={stats}
                          isLoading={detailsLoading}
                          onEdit={handleEditPortfolio}
                          onDelete={handleDeletePortfolio}
                          onAddPosition={(portfolio) => {
                            navigate("/transactions", {
                              state: {
                                action: "createTransaction",
                                portfolioId: portfolio.id,
                              },
                            });
                          }}
                          onViewDetails={() => {
                            setViewMode("detail");
                          }}
                        />
                      )}
                      <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4">
                          Recent Transactions
                        </h3>
                        {/* CHANGED: Conditional rendering for Transactions List */}
                        {detailsLoading ? (
                          <div className="flex justify-center items-center min-h-[300px]">
                            <LoadingSpinner
                              type="transaction"
                              text="Fetching transactions..."
                              centered
                            />
                          </div>
                        ) : transactions.length > 0 ? (
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
                                      - {transaction.asset.name}
                                    </p>
                                    <p className="text-xs text-gray-400">
                                      {formatDateTime(
                                        transaction.transaction_date
                                      )}
                                    </p>
                                  </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                  <p className="text-sm text-gray-400">
                                    {transaction.portfolio.name}
                                  </p>
                                </div>
                                <div className="text-right">
                                  <p className="text-sm font-medium text-gray-100">
                                    {transaction.transaction_type === "buy"
                                      ? "-"
                                      : "+"}
                                    {formatCurrency(transaction.total_amount, { currency: selectedPortfolio.currency })}
                                  </p>
                                  <p className="text-xs text-gray-400">
                                    {formatQuantity(transaction.quantity)} @{" "}
                                    {formatCurrency(transaction.price, { currency: selectedPortfolio.currency })}
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

                  {/* Unified loading state for other views */}
                  {viewMode !== "overview" &&
                    (detailsLoading ? (
                      <div className="card p-12 flex items-center justify-center min-h-[400px]">
                        <LoadingSpinner
                          type="analyst"
                          text={`Loading ${viewMode} data...`}
                          centered
                        />
                      </div>
                    ) : (
                      <>
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
                          <PortfolioChart portfolio={selectedPortfolio} />
                        )}

                        {viewMode === "performance" && selectedPortfolio && (
                          <PortfolioPerformanceMetrics
                            portfolio={selectedPortfolio}
                          />
                        )}
                      </>
                    ))}
                </div>
                </CurrencyProvider>
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
