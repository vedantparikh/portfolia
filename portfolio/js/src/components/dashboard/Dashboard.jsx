import {
  Activity,
  BarChart3,
  Bell,
  Bookmark,
  Menu,
  Plus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  User,
  Wallet,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useAuth } from "../../contexts/AuthContext";
import {
  marketAPI,
  portfolioAPI,
  transactionAPI,
} from "../../services/api";
import {
  formatCurrency,
  formatDateTime,
  formatPercentage,
  formatQuantity,
  formatVolume,
} from "../../utils/formatters";
import EmailVerificationPrompt from "../auth/EmailVerificationPrompt";
import { Sidebar } from "../shared";
const Dashboard = () => {
  const { user } = useAuth();
  const { profile } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const [dashboardData, setDashboardData] = useState({
    portfolios: [],
    recentTransactions: [],
    topAssets: [],
    loading: true,
  });

  // Load dashboard data
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Check for mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const loadDashboardData = async () => {
    try {
      setDashboardData((prev) => ({ ...prev, loading: true }));

      // Load all data in parallel
      const [
        portfoliosResponse,
        transactionsResponse,
        assetsResponse,
      ] = await Promise.allSettled([
        portfolioAPI.getPortfolios(),
        transactionAPI.getTransactions({
          limit: 5,
          order_by: "transaction_date",
          order: "desc",
        }),
        marketAPI.getAssets({
          limit: 10,
          sort: "market_cap",
          include_detail: true,
        })
      ]);

      const portfolios =
        portfoliosResponse.status === "fulfilled"
          ? portfoliosResponse.value || []
          : [];
      const recentTransactions =
        transactionsResponse.status === "fulfilled"
          ? transactionsResponse.value || []
          : [];
      const topAssets =
        assetsResponse.status === "fulfilled" ? assetsResponse.value || [] : [];

      // Calculate portfolio summaries
      const portfolioSummaries = await Promise.allSettled(
        portfolios.map((portfolio) =>
          portfolioAPI.getPortfolioSummary(portfolio.id)
        )
      );

      const portfoliosWithStats = portfolios.map((portfolio, index) => ({
        ...portfolio,
        stats:
          portfolioSummaries[index].status === "fulfilled"
            ? portfolioSummaries[index].value
            : null,
      }));

      setDashboardData({
        portfolios: portfoliosWithStats,
        recentTransactions,
        topAssets,
        loading: false,
      });
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
      setDashboardData((prev) => ({ ...prev, loading: false }));
    }
  };

  const handleRefresh = () => {
    loadDashboardData();
    toast.success("Dashboard data refreshed");
  };

  const handleQuickAction = (action) => {
    switch (action) {
      case "create-portfolio":
        // Navigate to portfolio page or open modal
        window.location.href = "/portfolio";
        break;
      case "create-transaction":
        // Navigate to transactions page or open modal
        window.location.href = "/transactions";
        break;
      case "refresh":
        handleRefresh();
        break;
      default:
        break;
    }
  };

  return (
    <div className="min-h-screen gradient-bg flex">
      {/* Mobile sidebar overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Shared Sidebar */}
      <Sidebar
        currentView="dashboard"
        portfolios={dashboardData.portfolios}
        onRefresh={handleRefresh}
        onQuickAction={handleQuickAction}
        isMobile={isMobile}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="lg:hidden p-2 rounded-lg hover:bg-dark-800 transition-colors"
              >
                <Menu size={20} className="text-gray-400" />
              </button>
              <h2 className="text-xl font-semibold text-gray-100">Dashboard</h2>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleRefresh}
                disabled={dashboardData.loading}
                className="btn-secondary flex items-center space-x-2"
              >
                <RefreshCw
                  size={16}
                  className={dashboardData.loading ? "animate-spin" : ""}
                />
                <span>Refresh</span>
              </button>
            </div>

            <div className="flex items-center space-x-4">
              <button className="p-2 rounded-lg hover:bg-dark-800 transition-colors relative">
                <Bell size={20} className="text-gray-400" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-primary-500 rounded-full"></span>
              </button>

              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                  <User size={16} className="text-white" />
                </div>
                <span className="text-sm text-gray-300 hidden md:block">
                  {profile?.first_name} {profile?.last_name}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Main Dashboard Content */}
        <main className="flex-1 p-6 overflow-auto">
          <div className="max-w-7xl mx-auto">
            {/* Email Verification Prompt */}
            {user && !user.is_verified && (
              <EmailVerificationPrompt user={user} />
            )}

            {/* Welcome Section */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-100 mb-2">
                Welcome back, {profile?.first_name}! 👋
              </h1>
              <p className="text-gray-400">
                Here's what's happening with your portfolio today.
              </p>
            </div>

            {dashboardData.loading ? (
              <div className="flex items-center justify-center py-12">
                <RefreshCw className="w-8 h-8 text-primary-400 animate-spin" />
                <span className="ml-3 text-gray-400">
                  Loading dashboard data...
                </span>
              </div>
            ) : (
              <>

                {/* Main Content Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                  {/* Portfolio Overview */}
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-gray-100">
                        Your Portfolios
                      </h3>
                      <a
                        href="/portfolio"
                        className="btn-primary text-sm flex items-center space-x-2"
                      >
                        <Plus size={16} />
                        <span>New Portfolio</span>
                      </a>
                    </div>

                    {dashboardData.portfolios.length === 0 ? (
                      <div className="text-center py-8">
                        <Wallet className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <h4 className="text-lg font-semibold text-gray-300 mb-2">
                          No portfolios yet
                        </h4>
                        <p className="text-gray-500 mb-4">
                          Create your first portfolio to start tracking
                          investments
                        </p>
                        <a href="/portfolio" className="btn-primary">
                          Create Portfolio
                        </a>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {dashboardData.portfolios
                          .slice(0, 3)
                          .map((portfolio) => (
                            <div
                              key={portfolio.id}
                              className="flex items-center justify-between p-4 bg-dark-800 rounded-lg"
                            >
                              <div>
                                <h4 className="font-medium text-gray-100">
                                  {portfolio.name}
                                </h4>
                                <p className="text-sm text-gray-400">
                                  {portfolio.description || "No description"}
                                </p>
                              </div>
                              <div className="text-right">
                                <p className="font-semibold text-gray-100">
                                  $
                                  {(
                                    portfolio.stats?.total_value || 0
                                  ).toLocaleString()}
                                </p>
                                <p
                                  className={`text-sm ${
                                    (portfolio.stats?.total_value || 0) >=
                                    (portfolio.stats?.total_cost || 0)
                                      ? "text-success-400"
                                      : "text-danger-400"
                                  }`}
                                >
                                  {portfolio.stats?.total_value &&
                                  portfolio.stats?.total_cost
                                    ? `${(
                                        ((portfolio.stats.total_value -
                                          portfolio.stats.total_cost) /
                                          portfolio.stats.total_cost) *
                                        100
                                      ).toFixed(2)}%`
                                    : "0.00%"}
                                </p>
                              </div>
                            </div>
                          ))}
                        {dashboardData.portfolios.length > 3 && (
                          <div className="text-center">
                            <a
                              href="/portfolio"
                              className="text-primary-400 hover:text-primary-300 text-sm"
                            >
                              View all {dashboardData.portfolios.length}{" "}
                              portfolios →
                            </a>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Recent Transactions */}
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-gray-100">
                        Recent Transactions
                      </h3>
                      <a
                        href="/transactions"
                        className="text-primary-400 hover:text-primary-300 text-sm"
                      >
                        View all →
                      </a>
                    </div>

                    {dashboardData.recentTransactions.length === 0 ? (
                      <div className="text-center py-8">
                        <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <h4 className="text-lg font-semibold text-gray-300 mb-2">
                          No transactions yet
                        </h4>
                        <p className="text-gray-500 mb-4">
                          Start trading to see your transaction history
                        </p>
                        <a href="/transactions" className="btn-primary">
                          Create Transaction
                        </a>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {dashboardData.recentTransactions.map((transaction) => (
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
                                  {transaction.transaction_type.toUpperCase()} -{" "}
                                  {transaction.asset.symbol}
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
                    )}
                  </div>
                </div>

                {/* Top Assets */}
                {dashboardData.topAssets.length > 0 && (
                  <div className="card p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-lg font-semibold text-gray-100">
                        Top Market Assets
                      </h3>
                      <a
                        href="/assets"
                        className="text-primary-400 hover:text-primary-300 text-sm"
                      >
                        View all assets →
                      </a>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                      {dashboardData.topAssets.slice(0, 5).map((asset) => (
                        <div
                          key={asset.id}
                          className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors cursor-pointer"
                        >
                          {/* --- Top Section --- */}
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="font-medium text-gray-100">
                              {asset.symbol}
                            </h4>
                            <span
                              className={`text-xs px-2 py-1 rounded ${
                                (asset.detail.price_change_percentage_24h ||
                                  0) >= 0
                                  ? "bg-success-400/20 text-success-400"
                                  : "bg-danger-400/20 text-danger-400"
                              }`}
                            >
                              {formatPercentage(
                                asset.detail.price_change_percentage_24h,
                                {
                                  precision: 2,
                                  showSign: true,
                                }
                              )}
                            </span>
                          </div>
                          <p className="text-sm text-gray-400 mb-1">
                            {asset.name}
                          </p>
                          <p className="text-lg font-semibold text-gray-100">
                            {formatCurrency(asset.detail.current_price)}
                          </p>

                          {/* --- NEW STATS SECTION --- */}
                          <div className="mt-4 pt-4 border-t border-dark-700 space-y-1">
                            {/* 24h Volume */}
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-gray-400">Vol (24h)</span>
                              <span className="font-medium text-gray-100">
                                {formatVolume(asset.detail.volume_24h)}
                              </span>
                            </div>

                            {/* 52w High */}
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-gray-400">52w H</span>
                              <span className="font-medium text-gray-100">
                                {formatCurrency(asset.detail.high_52w)}
                              </span>
                            </div>

                            {/* 52w Low */}
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-gray-400">52w L</span>
                              <span className="font-medium text-gray-100">
                                {formatCurrency(asset.detail.low_52w)}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Quick Actions */}
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-6">
                    Quick Actions
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <a
                      href="/portfolio"
                      className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center"
                    >
                      <Wallet className="w-8 h-8 text-primary-400 mx-auto mb-2" />
                      <h4 className="font-medium text-gray-100">
                        Create Portfolio
                      </h4>
                      <p className="text-sm text-gray-400">
                        Start a new investment portfolio
                      </p>
                    </a>
                    <a
                      href="/transactions"
                      className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center"
                    >
                      <Plus className="w-8 h-8 text-success-400 mx-auto mb-2" />
                      <h4 className="font-medium text-gray-100">
                        Add Transaction
                      </h4>
                      <p className="text-sm text-gray-400">
                        Record a buy or sell transaction
                      </p>
                    </a>
                    <a
                      href="/assets"
                      className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center"
                    >
                      <BarChart3 className="w-8 h-8 text-warning-400 mx-auto mb-2" />
                      <h4 className="font-medium text-gray-100">
                        Browse Assets
                      </h4>
                      <p className="text-sm text-gray-400">
                        Explore market opportunities
                      </p>
                    </a>
                    <a
                      href="/watchlist"
                      className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center"
                    >
                      <Bookmark className="w-8 h-8 text-danger-400 mx-auto mb-2" />
                      <h4 className="font-medium text-gray-100">
                        Manage Watchlists
                      </h4>
                      <p className="text-sm text-gray-400">
                        Track your favorite assets
                      </p>
                    </a>
                  </div>
                </div>

              </>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;
