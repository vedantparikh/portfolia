import {
  Bell,
  Activity,
  BarChart3,
  Bookmark,
  Clock,
  Layers,
  Menu,
  Plus,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  User,
  Wallet,
} from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useAuth } from "../../contexts/AuthContext";
import {
  marketAPI,
  portfolioAPI,
  portfolioCalculationsAPI,
  transactionAPI,
  watchlistAPI,
} from "../../services/api";
import {
  formatCurrency,
  formatDateTime,
  formatPercentage,
  formatQuantity,
  formatVolume,
  getChangeColor,
} from "../../utils/formatters";
import { useShell } from "../../app/chrome";
import EmailVerificationPrompt from "../../features/auth/EmailVerificationPrompt";
import { LoadingSpinner, Sparkline, StatCard } from "../shared";

const CardLoader = ({ text = "Loading..." }) => (
  <div className="flex items-center justify-center py-8">
    <LoadingSpinner type="analyst" size="md" text={text} />
  </div>
);

const Dashboard = () => {
  const { user, profile, refreshUser } = useAuth();
  const { toggleSidebar } = useShell();

  const [dashboardData, setDashboardData] = useState({
    portfolios: [],
    recentTransactions: [],
    topAssets: [],
  });
  const [overview, setOverview] = useState(null);
  const [unreadAlerts, setUnreadAlerts] = useState(0);
  const [movers, setMovers] = useState(null);
  const [marketStatus, setMarketStatus] = useState(null);
  const [loadingStates, setLoadingStates] = useState({
    portfolios: true,
    transactions: true,
    assets: true,
  });

  // Load dashboard data
  useEffect(() => {
    loadDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once on mount
  }, []);

  const loadDashboardData = async () => {
    // Reset all loading states to true on refresh
    setLoadingStates({
      portfolios: true,
      transactions: true,
      assets: true,
    });

    // Independent sections load in parallel so a slow one doesn't block the others
    await Promise.all([
      loadTransactions(),
      loadTopAssets(),
      loadPortfolios(),
      loadOverview(),
      loadMovers(),
    ]);
  };

  const loadMovers = async () => {
    try {
      const portfolios = await portfolioAPI.getPortfolios();
      const results = await Promise.allSettled(
        portfolios.map((p) => portfolioAPI.getPortfolioHoldings(p.id))
      );
      const bySymbol = new Map();
      results
        .filter((r) => r.status === "fulfilled")
        .flatMap((r) => r.value || [])
        .filter((h) => h.today_pnl_percent != null)
        .forEach((h) => bySymbol.set(h.symbol, h));
      const sorted = [...bySymbol.values()].sort(
        (a, b) => b.today_pnl_percent - a.today_pnl_percent
      );
      setMovers({
        gainers: sorted.filter((h) => h.today_pnl_percent > 0).slice(0, 3),
        losers: sorted
          .filter((h) => h.today_pnl_percent < 0)
          .reverse()
          .slice(0, 3),
      });
    } catch (error) {
      console.error("Failed to load movers:", error);
      setMovers({ gainers: [], losers: [] });
    }
  };

  const loadOverview = async () => {
    const [stats, status, alerts] = await Promise.allSettled([
      portfolioAPI.getStatisticsOverview(),
      marketAPI.getMarketStatus(),
      watchlistAPI.getAlerts(true, 1),
    ]);
    setOverview(stats.status === "fulfilled" ? stats.value : null);
    setMarketStatus(status.status === "fulfilled" ? status.value : null);
    setUnreadAlerts(alerts.status === "fulfilled" ? alerts.value.unread_count : 0);
  };

  const loadTransactions = async () => {
    try {
      const transactionsResponse = await transactionAPI.getTransactions({
        limit: 5,
        order_by: "transaction_date",
        order: "desc",
      });
      setDashboardData((prev) => ({
        ...prev,
        recentTransactions: transactionsResponse || [],
      }));
    } catch (error) {
      console.error("Failed to load transactions:", error);
      toast.error("Failed to load recent transactions.");
    } finally {
      setLoadingStates((prev) => ({ ...prev, transactions: false }));
    }
  };

  const loadTopAssets = async () => {
    try {
      const assetsResponse = await marketAPI.getAssets({
        limit: 10,
        sort: "market_cap",
        include_detail: true,
      });
      setDashboardData((prev) => ({
        ...prev,
        topAssets: assetsResponse || [],
      }));
    } catch (error) {
      console.error("Failed to load assets:", error);
      toast.error("Failed to load top market assets.");
    } finally {
      setLoadingStates((prev) => ({ ...prev, assets: false }));
    }
  };

  const loadPortfolios = async () => {
    try {
      const portfolios = await portfolioAPI.getPortfolios();
      if (portfolios && portfolios.length > 0) {
        const [portfolioSummaries, histories] = await Promise.all([
          Promise.allSettled(
            portfolios.map((p) => portfolioAPI.getPortfolioSummary(p.id))
          ),
          Promise.allSettled(
            portfolios.map((p) =>
              portfolioCalculationsAPI.getPerformanceSeries(p.id, "3m")
            )
          ),
        ]);
        const portfoliosWithStats = portfolios.map((portfolio, index) => ({
          ...portfolio,
          stats:
            portfolioSummaries[index].status === "fulfilled"
              ? portfolioSummaries[index].value
              : null,
          history:
            histories[index].status === "fulfilled"
              ? histories[index].value.points.map((p) => p.value)
              : [],
        }));
        setDashboardData((prev) => ({
          ...prev,
          portfolios: portfoliosWithStats,
        }));
      } else {
        setDashboardData((prev) => ({ ...prev, portfolios: [] }));
      }
    } catch (error) {
      console.error("Failed to load portfolios:", error);
      toast.error("Failed to load portfolios.");
    } finally {
      setLoadingStates((prev) => ({ ...prev, portfolios: false }));
    }
  };

  const handleRefresh = () => {
    refreshUser();
    loadDashboardData();
    toast.success("Dashboard data refreshed");
  };

  // Helper component for displaying P&L stats to avoid repetitive code
  const PnlDisplay = ({ value, percent, label, currency }) => {
    const isPositive = value >= 0;
    const valueColor = isPositive ? "text-success-400" : "text-danger-400";

    return (
      <div className="text-right">
        <p className={`font-medium ${valueColor}`}>
          {formatCurrency(value, { signDisplay: "exceptZero", currency })}
        </p>
        <p className={`text-sm ${valueColor}`}>
          {formatPercentage(percent, { showSign: true })}
        </p>
        {label && <p className="text-xs text-gray-500 mt-1">{label}</p>}
      </div>
    );
  };

  const isAnythingLoading = Object.values(loadingStates).some(
    (state) => state === true
  );

  return (
    <div className="min-h-screen gradient-bg flex">
      {/* Main Content */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Top Header */}
        <header className="bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleSidebar}
                className="lg:hidden p-2 rounded-lg hover:bg-dark-800 transition-colors"
              >
                <Menu size={20} className="text-gray-400" />
              </button>
              <h2 className="text-xl font-semibold text-gray-100">Dashboard</h2>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleRefresh}
                disabled={isAnythingLoading}
                className="btn-secondary flex items-center space-x-2"
              >
                <RefreshCw
                  size={16}
                  className={isAnythingLoading ? "animate-spin" : ""}
                />
                <span>Refresh</span>
              </button>
            </div>

            <div className="flex items-center space-x-4">
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
                Here&apos;s what&apos;s happening with your portfolio today.
              </p>
              {unreadAlerts > 0 && (
                <a
                  href="/watchlist"
                  className="inline-flex items-center gap-2 mt-2 text-sm text-warning-300 hover:text-warning-200"
                >
                  <Bell size={16} />
                  {unreadAlerts} new watchlist {unreadAlerts === 1 ? "alert" : "alerts"}
                </a>
              )}
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard
                label="Total Value"
                icon={Wallet}
                className="col-span-2 lg:col-span-1"
                value={
                  overview?.totals?.length
                    ? overview.totals
                        .map((t) => formatCurrency(t.total_value, { currency: t.currency }))
                        .join(" · ")
                    : "—"
                }
                sub={
                  overview?.totals?.length
                    ? overview.totals
                        .map(
                          (t) =>
                            `${formatCurrency(t.today_pnl, { signDisplay: "exceptZero", currency: t.currency })} (${formatPercentage(t.today_pnl_percent)})`
                        )
                        .join(" · ") + " today"
                    : "Across all portfolios"
                }
              />
              <StatCard
                label="Portfolios"
                icon={Layers}
                tone="gray"
                value={overview ? overview.active_portfolios : "—"}
                sub={
                  overview && overview.total_portfolios !== overview.active_portfolios
                    ? `${overview.total_portfolios} including inactive`
                    : "Active"
                }
              />
              <StatCard
                label="Holdings"
                icon={BarChart3}
                tone="gray"
                value={overview ? overview.total_assets : "—"}
                sub="Positions across portfolios"
              />
              <StatCard
                label="US Market"
                icon={Clock}
                className="col-span-2 lg:col-span-1"
                tone={marketStatus?.is_open ? "success" : "gray"}
                value={marketStatus ? (marketStatus.is_open ? "Open" : "Closed") : "—"}
                sub="Mon–Fri 9:30–16:00 ET"
              />
            </div>

            <>
              {/* Main Content Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                {/* Portfolio Overview */}
                <div className="card p-6 flex flex-col">
                  <div className="flex items-center justify-between mb-6">
                    {/* --- MODIFICATION START --- */}
                    <h3 className="text-lg font-semibold text-gray-100">
                      Your Portfolios
                      {!loadingStates.portfolios && (
                        <span className="text-gray-400 font-normal ml-2">
                          ({dashboardData.portfolios.length})
                        </span>
                      )}
                    </h3>
                    {/* --- MODIFICATION END --- */}
                    <a
                      href="/portfolio"
                      className="btn-primary text-sm flex items-center space-x-2"
                    >
                      <Plus size={16} />
                      <span>New Portfolio</span>
                    </a>
                  </div>

                  {loadingStates.portfolios ? (
                    <CardLoader text="Loading portfolios..." />
                  ) : dashboardData.portfolios.length === 0 ? (
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
                    <div className="space-y-4 max-h-80 overflow-y-auto">
                      <div className="hidden md:grid grid-cols-4 gap-4 px-4 text-xs text-gray-400 font-medium sticky top-0 bg-dark-900 z-10 py-2">
                        <span>Portfolio</span>
                        <span className="text-right">Total Value</span>
                        <span className="text-right">Today&apos;s P&L</span>
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
                              {formatCurrency(portfolio.stats?.total_current_value, {
                                currency: portfolio.currency,
                              })}
                            </p>
                            <Sparkline
                              values={portfolio.history}
                              width={72}
                              height={18}
                              className="ml-auto mt-1 text-primary-400"
                              title="Value, last 3 months"
                            />
                            <p className="text-xs text-gray-500 mt-1 md:hidden">
                              Total Value
                            </p>
                          </div>
                          <PnlDisplay
                            currency={portfolio.currency}
                            value={portfolio.stats?.today_pnl ?? 0}
                            percent={portfolio.stats?.today_pnl_percent ?? 0}
                          />
                          <div className="hidden md:block">
                            <PnlDisplay
                              currency={portfolio.currency}
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

                  {loadingStates.transactions ? (
                    <CardLoader text="Loading transactions..." />
                  ) : dashboardData.recentTransactions.length === 0 ? (
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
                              className={`w-8 h-8 rounded-full flex items-center justify-center ${transaction.transaction_type === "buy"
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
                                {formatDateTime(transaction.transaction_date)}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium text-gray-100">
                              {transaction.transaction_type === "buy"
                                ? "-"
                                : "+"}
                              {formatCurrency(transaction.total_amount, {
                                currency: transaction.currency,
                              })}
                            </p>
                            <p className="text-xs text-gray-400">
                              {formatQuantity(transaction.quantity)} @{" "}
                              {formatCurrency(transaction.price, {
                                currency: transaction.currency,
                              })}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="card p-6 mb-8">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-gray-100">
                    Today&apos;s Movers
                  </h3>
                  <span className="text-xs text-gray-500">
                    Your holdings, by today&apos;s change
                  </span>
                </div>
                {!movers ? (
                  <CardLoader text="Loading holdings..." />
                ) : movers.gainers.length + movers.losers.length === 0 ? (
                  <p className="text-center py-6 text-gray-500">
                    No price changes for your holdings yet today.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {[
                      ["Gainers", movers.gainers],
                      ["Losers", movers.losers],
                    ].map(([title, rows]) => (
                      <div key={title}>
                        <p className="text-xs font-medium text-gray-400 mb-2">
                          {title}
                        </p>
                        {rows.length === 0 ? (
                          <p className="text-sm text-gray-500 py-2">None today</p>
                        ) : (
                          <div className="space-y-2">
                            {rows.map((h) => (
                              <div
                                key={h.symbol}
                                className="flex items-center justify-between gap-3 px-4 py-2.5 bg-dark-800 rounded-lg"
                              >
                                <div className="min-w-0">
                                  <p className="font-medium text-gray-100">
                                    {h.symbol}
                                  </p>
                                  <p className="text-xs text-gray-400 truncate">
                                    {h.name}
                                  </p>
                                </div>
                                <p
                                  className={`font-medium shrink-0 ${getChangeColor(h.today_pnl_percent)}`}
                                >
                                  {formatPercentage(h.today_pnl_percent, {
                                    showSign: true,
                                  })}
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

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

                {loadingStates.assets ? (
                  <CardLoader text="Loading market data..." />
                ) : dashboardData.topAssets.length > 0 ? (
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
                              className={`text-xs px-2 py-1 rounded shrink-0 ${(asset.detail?.price_change_percentage_24h ??
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
                            {formatCurrency(asset.detail?.current_price, {
                              currency: asset.currency,
                            })}
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
                          <div className="flex justify-between items-center text-xs">
                            <span className="text-gray-400">52w Range</span>
                            <span className="font-medium text-gray-100">
                              {asset.detail?.low_52w && asset.detail?.high_52w
                                ? `${formatCurrency(asset.detail.low_52w, {
                                  compact: true,
                                  currency: asset.currency,
                                })} - ${formatCurrency(
                                  asset.detail.high_52w,
                                  { compact: true, currency: asset.currency }
                                )}`
                                : "N/A"}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No market data could be loaded.
                  </div>
                )}
              </div>

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
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;