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
import { marketAPI, portfolioAPI, transactionAPI } from "../../services/api";
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
  const { user, profile } = useAuth();
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
      const [portfoliosResponse, transactionsResponse, assetsResponse] =
        await Promise.allSettled([
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
          }),
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

      // Calculate portfolio summaries asynchronously
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
      toast.error("Failed to load dashboard data.");
      setDashboardData((prev) => ({ ...prev, loading: false }));
    }
  };

  const handleRefresh = () => {
    loadDashboardData();
    toast.success("Dashboard data refreshed");
  };

  // Helper component for displaying P&L stats to avoid repetitive code
  const PnlDisplay = ({ value, percent, label }) => {
    const isPositive = value >= 0;
    const valueColor = isPositive ? "text-success-400" : "text-danger-400";

    return (
      <div className="text-right">
        <p className={`font-medium ${valueColor}`}>
          {formatCurrency(value, { showSign: true })}
        </p>
        <p className={`text-sm ${valueColor}`}>
          {formatPercentage(percent, { showSign: true })}
        </p>
        {label && <p className="text-xs text-gray-500 mt-1">{label}</p>}
      </div>
    );
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
                  <div className="card p-6 flex flex-col">
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
                      /* --- MODIFICATION START --- */
                      // Removed pr-2 and changed max-h-[300px] to max-h-80
                      <div className="space-y-4 max-h-80 overflow-y-auto">
                        {/* --- END MODIFICATION --- */}
                        <div className="hidden md:grid grid-cols-4 gap-4 px-4 text-xs text-gray-400 font-medium sticky top-0 bg-dark-900 z-10 py-2">
                          <span>Portfolio</span>
                          <span className="text-right">Total Value</span>
                          <span className="text-right">Today's P&L</span>
                          <span className="text-right">Total P&L</span>
                        </div>
                        {dashboardData.portfolios.map((portfolio) => (
                          <div
                            key={portfolio.id}
                            className="grid grid-cols-2 md:grid-cols-4 gap-4 items-center p-4 bg-dark-800 rounded-lg"
                          >
                            <div className="col-span-2 md:col-span-1">
                              <h4 className="font-medium text-gray-100 truncate">
                                {portfolio.name}
                              </h4>
                              <p className="text-sm text-gray-400">
                                {portfolio.stats?.total_assets ?? 0} Assets
                              </p>
                            </div>

                            <div className="text-right">
                              <p className="font-semibold text-gray-100">
                                {formatCurrency(
                                  portfolio.stats?.total_current_value
                                )}
                              </p>
                              <p className="text-xs text-gray-500 mt-1 md:hidden">
                                Total Value
                              </p>
                            </div>

                            <PnlDisplay
                              value={portfolio.stats?.today_pnl ?? 0}
                              percent={
                                portfolio.stats?.today_pnl_percent ?? 0
                              }
                            />

                            <div className="hidden md:block">
                              <PnlDisplay
                                value={
                                  portfolio.stats?.total_unrealized_pnl ?? 0
                                }
                                percent={
                                  portfolio.stats
                                    ?.total_unrealized_pnl_percent ?? 0
                                }
                              />
                            </div>
                          </div>
                        ))}
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
                            <div className="text-right">
                              <p
                                className={`text-sm font-medium ${
                                  transaction.transaction_type === "buy"
                                    ? "text-danger-400"
                                    : "text-success-400"
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

                {dashboardData.topAssets.length > 0 && (
                  <div className="card p-6 mb-8">
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
                      {dashboardData.topAssets.map((asset) => (
                        <div
                          key={asset.id}
                          className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors cursor-pointer flex flex-col justify-between"
                        >
                          <div>
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex-1 pr-2 min-w-0">
                                <h4 className="font-medium text-gray-100 truncate">
                                  {asset.symbol}
                                </h4>
                                <p className="text-xs text-gray-400 truncate">
                                  {asset.name}
                                </p>
                              </div>
                              <span
                                className={`text-xs px-2 py-1 rounded shrink-0 ${
                                  (asset.detail?.price_change_percentage_24h ??
                                    0) >= 0
                                    ? "bg-success-400/20 text-success-400"
                                    : "bg-danger-400/20 text-danger-400"
                                }`}
                              >
                                {formatPercentage(
                                  asset.detail?.price_change_percentage_24h,
                                  {
                                    precision: 2,
                                    showSign: true,
                                  }
                                )}
                              </span>
                            </div>
                            <p className="text-lg font-semibold text-gray-100">
                              {formatCurrency(asset.detail?.current_price)}
                            </p>
                          </div>

                          <div className="mt-4 pt-4 border-t border-dark-700 space-y-1">
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-gray-400">Mkt Cap</span>
                              <span className="font-medium text-gray-100">
                                {asset.detail?.market_cap
                                  ? formatVolume(asset.detail.market_cap)
                                  : "N/A"}
                              </span>
                            </div>

                            <div className="flex justify-between items-center text-xs">
                              <span className="text-gray-400">P/E Ratio</span>
                              <span className="font-medium text-gray-100">
                                {asset.detail?.trailing_PE
                                  ? Number(asset.detail.trailing_PE).toFixed(2)
                                  : "N/A"}
                              </span>
                            </div>

                            {/* --- ADDED 52 WEEK RANGE LINE --- */}
                            <div className="flex justify-between items-center text-xs">
                              <span className="text-gray-400">52w Range</span>
                              <span className="font-medium text-gray-100">
                                {asset.detail?.low_52w && asset.detail?.high_52w
                                  ? `${formatCurrency(asset.detail.low_52w, {
                                      compact: true,
                                    })} - ${formatCurrency(
                                      asset.detail.high_52w,
                                      { compact: true }
                                    )}`
                                  : "N/A"}
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