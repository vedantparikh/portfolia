import {
  Activity,
  BarChart3,
  Download,
  Plus,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import { analyticsAPI, portfolioAPI } from "../../services/api";
import {
  formatCurrency,
  formatDateTime,
  getTransactionColor,
  getTransactionIcon,
} from "../../utils/formatters.jsx";
import {
  BenchmarkComparison,
  PortfolioAllocationManager,
  PortfolioAnalytics,
  RebalancingRecommendations,
} from "../analytics";

const PortfolioDetail = ({ portfolio, stats, transactions }) => {
  const [showAllTransactions, setShowAllTransactions] = useState(false);
  const [transactionFilter, setTransactionFilter] = useState("all");
  const [holdings, setHoldings] = useState([]);
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  const filteredTransactions = transactions.filter((transaction) => {
    if (transactionFilter === "all") return true;
    return transaction.transaction_type === transactionFilter;
  });

  const displayedTransactions = showAllTransactions
    ? filteredTransactions
    : filteredTransactions.slice(0, 10);

  // Load portfolio holdings and analytics
  useEffect(() => {
    if (portfolio && portfolio.id) {
      loadHoldings();
      loadAnalyticsData();
    }
  }, [portfolio]);

  const loadHoldings = async () => {
    if (!portfolio || !portfolio.id) return;

    try {
      setLoadingHoldings(true);
      console.log(
        "[PortfolioDetail] Loading holdings for portfolio:",
        portfolio.id
      );

      // Try to get holdings from the API
      const holdingsResponse = await portfolioAPI.getPortfolioHoldings(
        portfolio.id
      );
      console.log("[PortfolioDetail] Holdings response:", holdingsResponse);

      // Process holdings data from API response
      let holdings = [];
      if (
        holdingsResponse &&
        Array.isArray(holdingsResponse) &&
        holdingsResponse.length > 0
      ) {
        holdings = holdingsResponse.map((holding) => ({
          id: holding.asset_id,
          symbol: holding.symbol,
          name: holding.name,
          quantity: holding.quantity,
          avgPrice: holding.cost_basis,
          currentPrice: holding.current_value / holding.quantity,
          value: holding.current_value,
          change: holding.unrealized_pnl_percent,
          gainLoss: holding.unrealized_pnl,
          todayGainLoss: holding.today_pnl,
          todayGainLossPercent: holding.today_pnl_percent,
          realizedGainLoss: holding.realized_pnl,
          realizedGainLossPercent: holding.realized_pnl_percent,
        }));
      } else {
        // Mock holdings data fallback - replace with real API data when available
        const mockHoldings = [
          {
            id: 1,
            symbol: "AAPL",
            name: "Apple Inc.",
            quantity: 10,
            avgPrice: 150.0,
            currentPrice: 175.5,
            value: 1755.0,
            change: 16.67,
            gainLoss: 255.0,
            todayGainLoss: 100.0,
            todayGainLossPercent: 10.0,
            realizedGainLoss: 100.0,
            realizedGainLossPercent: 10.0,
          },
          {
            id: 2,
            symbol: "GOOGL",
            name: "Alphabet Inc.",
            quantity: 5,
            avgPrice: 2800.0,
            currentPrice: 2950.0,
            value: 14750.0,
            change: 5.36,
            gainLoss: 750.0,
            todayGainLoss: 200.0,
            todayGainLossPercent: 10.0,
            realizedGainLoss: 200.0,
            realizedGainLossPercent: 10.0,
          },
          {
            id: 3,
            symbol: "MSFT",
            name: "Microsoft Corporation",
            quantity: 8,
            avgPrice: 300.0,
            currentPrice: 320.0,
            value: 2560.0,
            change: 6.67,
            gainLoss: 160.0,
            todayGainLoss: 50.0,
            todayGainLossPercent: 10.0,
            realizedGainLoss: 50.0,
            realizedGainLossPercent: 10.0,
          },
          {
            id: 4,
            symbol: "TSLA",
            name: "Tesla Inc.",
            quantity: 3,
            avgPrice: 800.0,
            currentPrice: 750.0,
            value: 2250.0,
            change: -6.25,
            gainLoss: -150.0,
            todayGainLoss: -50.0,
            todayGainLossPercent: 10.0,
            realizedGainLoss: -50.0,
            realizedGainLossPercent: 10.0,
          },
          {
            id: 5,
            symbol: "NVDA",
            name: "NVIDIA Corporation",
            quantity: 6,
            avgPrice: 400.0,
            currentPrice: 450.0,
            value: 2700.0,
            change: 12.5,
            gainLoss: 300.0,
            todayGainLoss: 100.0,
            todayGainLossPercent: 10.0,
            realizedGainLoss: 100.0,
            realizedGainLossPercent: 10.0,
          },
        ];
        holdings = mockHoldings;
      }

      setHoldings(holdings);
    } catch (error) {
      console.warn("[PortfolioDetail] Failed to load holdings:", error);
      // Set empty holdings on error
      setHoldings([]);
    } finally {
      setLoadingHoldings(false);
    }
  };

  const loadAnalyticsData = async () => {
    if (!portfolio || !portfolio.id) return;

    try {
      setLoadingAnalytics(true);
      const [summary, performanceSnapshot] = await Promise.allSettled([
        analyticsAPI.getPortfolioAnalyticsSummary(portfolio.id),
        analyticsAPI.getPerformanceSnapshot(portfolio.id),
      ]);

      setAnalyticsData({
        summary: summary.status === "fulfilled" ? summary.value : null,
        performanceSnapshot:
          performanceSnapshot.status === "fulfilled"
            ? performanceSnapshot.value
            : null,
      });
    } catch (error) {
      console.warn("[PortfolioDetail] Failed to load analytics data:", error);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  const totalHoldingsValue = holdings.reduce(
    (sum, holding) => sum + (holding.value || 0),
    0
  );
  const totalCost = holdings.reduce(
    (sum, holding) => sum + (holding.quantity || 0) * (holding.avgPrice || 0),
    0
  );
  const totalGainLoss = totalHoldingsValue - totalCost;
  const totalGainLossPercent =
    totalCost > 0 ? (totalGainLoss / totalCost) * 100 : 0;

  const totalTodayGainLoss = holdings.reduce(
    (sum, holding) => sum + (holding.todayGainLoss || 0),
    0
  );
  const startOfDayValue = totalHoldingsValue - totalTodayGainLoss;
  const totalTodayGainLossPercent =
    startOfDayValue > 0 ? (totalTodayGainLoss / startOfDayValue) * 100 : 0;

  const totalRealizedGainLoss = holdings.reduce(
    (sum, holding) => sum + (holding.realizedGainLoss || 0),
    0
  );
  const totalRealizedGainLossPercent =
    totalCost > 0 ? (totalRealizedGainLoss / totalCost) * 100 : 0;

  const tabs = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "analytics", label: "Analytics", icon: TrendingUp },
    { id: "allocations", label: "Allocations", icon: Target },
    { id: "rebalancing", label: "Rebalancing", icon: Activity },
    { id: "benchmarks", label: "Benchmarks", icon: BarChart3 },
  ];

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-dark-700">
        <nav className="flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === tab.id
                    ? "border-primary-500 text-primary-400"
                    : "border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300"
                  }`}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <>
          {/* Holdings Overview */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-100">Holdings</h3>
              <div className="flex items-center space-x-2">
                <button
                  onClick={loadHoldings}
                  disabled={loadingHoldings}
                  className="btn-outline text-sm flex items-center space-x-2"
                >
                  <RefreshCw
                    size={16}
                    className={loadingHoldings ? "animate-spin" : ""}
                  />
                  <span>Refresh</span>
                </button>
                <button className="btn-outline text-sm flex items-center space-x-2">
                  <Download size={16} />
                  <span>Export</span>
                </button>
                <button className="btn-primary text-sm flex items-center space-x-2">
                  <Plus size={16} />
                  <span>Add Position</span>
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-700">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">
                      Symbol
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Quantity
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Avg Price
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Current Price
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Value
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Unrealized Gain/Loss
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Today's Gain/Loss
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">
                      Realized Gain/Loss
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {loadingHoldings ? (
                    <tr>
                      <td colSpan="9" className="py-8 text-center">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-primary-400" />
                        <span className="text-gray-400">
                          Loading holdings...
                        </span>
                      </td>
                    </tr>
                  ) : holdings.length === 0 ? (
                    <tr>
                      <td colSpan="9" className="py-8 text-center">
                        <span className="text-gray-400">
                          No holdings found in this portfolio
                        </span>
                      </td>
                    </tr>
                  ) : (
                    holdings.map((holding, index) => (
                      <tr
                        key={index}
                        className="border-b border-dark-800 hover:bg-dark-800/50 transition-colors"
                      >
                        <td className="py-3 px-4">
                          <span className="font-medium text-gray-100">
                            {holding.name}
                          </span>
                          <div className="text-xs text-gray-500">{holding.symbol}</div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-gray-100">
                            {holding.quantity}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-gray-100">
                            {formatCurrency(holding.avgPrice)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-gray-100">
                            {formatCurrency(holding.currentPrice)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-gray-100 font-medium">
                            {formatCurrency(holding.value)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span
                            className={`font-medium ${(holding.gainLoss || 0) >= 0
                                ? "text-success-400"
                                : "text-danger-400"
                              }`}
                          >
                            {(holding.gainLoss || 0) >= 0 ? "+" : ""}
                            {formatCurrency(holding.gainLoss || 0)}
                          </span>
                          <p
                            className={`font-medium ${(holding.change || 0) >= 0
                                ? "text-success-400"
                                : "text-danger-400"
                              }`}
                          >
                            {(holding.change || 0) >= 0 ? "+" : ""}
                            {(holding.change || 0).toFixed(2)}%
                          </p>
                        </td>

                        <td className="py-3 px-4 text-right">
                          <span
                            className={`font-medium ${(holding.todayGainLoss || 0) >= 0
                                ? "text-success-400"
                                : "text-danger-400"
                              }`}
                          >
                            {(holding.todayGainLoss || 0) >= 0 ? "+" : ""}
                            {formatCurrency(holding.todayGainLoss || 0)}
                          </span>
                          <p
                            className={`font-medium ${(holding.todayGainLossPercent || 0) >= 0
                                ? "text-success-400"
                                : "text-danger-400"
                              }`}
                          >
                            {(holding.todayGainLossPercent || 0) >= 0
                              ? "+"
                              : ""}
                            {(holding.todayGainLossPercent || 0).toFixed(2)}%
                          </p>
                        </td>

                        <td className="py-3 px-4 text-right">
                          <span
                            className={`font-medium ${(holding.realizedGainLoss || 0) >= 0
                                ? "text-success-400"
                                : "text-danger-400"
                              }`}
                          >
                            {(holding.realizedGainLoss || 0) >= 0 ? "+" : ""}
                            {formatCurrency(holding.realizedGainLoss || 0)}
                          </span>
                          <p
                            className={`font-medium ${(holding.realizedGainLossPercent || 0) >= 0
                                ? "text-success-400"
                                : "text-danger-400"
                              }`}
                          >
                            {(holding.realizedGainLossPercent || 0) >= 0
                              ? "+"
                              : ""}
                            {(holding.realizedGainLossPercent || 0).toFixed(2)}%
                          </p>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
                <tfoot>
                  <tr className="border-t border-dark-700">
                    <td
                      colSpan="4"
                      className="py-3 px-4 text-right font-medium text-gray-300"
                    >
                      Total:
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="text-lg font-bold text-gray-100">
                        {formatCurrency(totalHoldingsValue)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span
                        className={`text-lg font-bold ${totalGainLoss >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                          }`}
                      >
                        {totalGainLoss >= 0 ? "+" : ""}
                        {formatCurrency(totalGainLoss)}
                      </span>
                      <p
                        className={`text-lg font-bold ${totalGainLossPercent >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                          }`}
                      >
                        {totalGainLossPercent >= 0 ? "+" : ""}
                        {totalGainLossPercent.toFixed(2)}%
                      </p>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <span
                        className={`text-lg font-bold ${totalTodayGainLoss >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                          }`}
                      >
                        {totalTodayGainLoss >= 0 ? "+" : ""}
                        {formatCurrency(totalTodayGainLoss)}
                      </span>
                      <p
                        className={`text-lg font-bold ${totalTodayGainLossPercent >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                          }`}
                      >
                        {totalTodayGainLossPercent >= 0 ? "+" : ""}
                        {totalTodayGainLossPercent.toFixed(2)}%
                      </p>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <span
                        className={`text-lg font-bold ${totalRealizedGainLossPercent >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                          }`}
                      >
                        {totalRealizedGainLossPercent >= 0 ? "+" : ""}
                        {formatCurrency(totalRealizedGainLoss)}
                      </span>
                      <p
                        className={`text-lg font-bold ${totalRealizedGainLossPercent >= 0
                            ? "text-success-400"
                            : "text-danger-400"
                          }`}
                      >
                        {totalRealizedGainLossPercent >= 0 ? "+" : ""}
                        {totalRealizedGainLossPercent.toFixed(2)}%
                      </p>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Transaction History */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-100">
                Transaction History
              </h3>
              <div className="flex items-center space-x-3">
                <select
                  value={transactionFilter}
                  onChange={(e) => setTransactionFilter(e.target.value)}
                  className="input-field text-sm"
                >
                  <option value="all">All Transactions</option>
                  <option value="buy">Buys</option>
                  <option value="sell">Sells</option>
                </select>
                <button className="btn-outline text-sm flex items-center space-x-2">
                  <Download size={16} />
                  <span>Export</span>
                </button>
              </div>
            </div>

            {displayedTransactions.length > 0 ? (
              <div className="space-y-3">
                {displayedTransactions.map((transaction) => (
                  <div
                    key={transaction.id}
                    className="flex items-center justify-between p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center justify-center w-10 h-10 bg-dark-700 rounded-lg">
                        {getTransactionIcon(transaction.transaction_type)}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-100">
                          {transaction.transaction_type.toUpperCase()}{" - "}
                          {transaction.asset.name}
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
                        className={`text-sm font-medium ${getTransactionColor(
                          transaction.transaction_type
                        )}`}
                      >
                        {transaction.transaction_type === "buy" ? "-" : "+"}
                        {formatCurrency(transaction.total_amount)}
                      </p>
                      <p className="text-xs text-gray-400">
                        {transaction.quantity} @{" "}
                        {formatCurrency(transaction.price)}
                      </p>
                    </div>
                  </div>
                ))}

                {filteredTransactions.length > 10 && (
                  <div className="text-center pt-4">
                    <button
                      onClick={() =>
                        setShowAllTransactions(!showAllTransactions)
                      }
                      className="btn-outline text-sm"
                    >
                      {showAllTransactions
                        ? `Show Less (${filteredTransactions.length - 10
                        } hidden)`
                        : `Show All (${filteredTransactions.length - 10} more)`}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-300 mb-2">
                  No transactions found
                </h3>
                <p className="text-gray-500 mb-6">
                  {transactionFilter === "all"
                    ? "Start by adding your first position to this portfolio"
                    : `No ${transactionFilter} transactions found`}
                </p>
                <button className="btn-primary flex items-center space-x-2 mx-auto">
                  <Plus size={16} />
                  <span>Add Position</span>
                </button>
              </div>
            )}
          </div>

          {/* Portfolio Allocation Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">
                Asset Allocation
              </h3>
              <div className="space-y-4">
                {holdings.length > 0 ? (
                  holdings.map((holding, index) => {
                    const percentage =
                      totalHoldingsValue > 0
                        ? ((holding.value || 0) / totalHoldingsValue) * 100
                        : 0;
                    return (
                      <div key={holding.id || index} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-100">
                            {holding.name}
                            <div className="text-xs text-gray-500">{holding.symbol}</div>
                          </span>
                          <span className="text-sm text-gray-400">
                            {percentage.toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-dark-700 rounded-full h-2">
                          <div
                            className="bg-primary-400 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center text-gray-400 py-8">
                    No holdings to display allocation for
                  </div>
                )}
              </div>
            </div>

            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">
                Performance Summary
              </h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Invested</span>
                  <span className="text-sm font-medium text-gray-100">
                    {formatCurrency(totalCost)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Current Value</span>
                  <span className="text-sm font-medium text-gray-100">
                    {formatCurrency(totalHoldingsValue)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Gain/Loss</span>
                  <span
                    className={`text-sm font-medium ${totalGainLoss >= 0
                        ? "text-success-400"
                        : "text-danger-400"
                      }`}
                  >
                    {totalGainLoss >= 0 ? "+" : ""}
                    {formatCurrency(totalGainLoss)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Total Return</span>
                  <span
                    className={`text-sm font-medium ${totalGainLossPercent >= 0
                        ? "text-success-400"
                        : "text-danger-400"
                      }`}
                  >
                    {totalGainLossPercent >= 0 ? "+" : ""}
                    {totalGainLossPercent.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Analytics Tab */}
      {activeTab === "analytics" && (
        <PortfolioAnalytics portfolioId={portfolio?.id} />
      )}

      {/* Allocations Tab */}
      {activeTab === "allocations" && (
        <PortfolioAllocationManager portfolioId={portfolio?.id} />
      )}

      {/* Rebalancing Tab */}
      {activeTab === "rebalancing" && (
        <RebalancingRecommendations portfolioId={portfolio?.id} />
      )}

      {/* Benchmarks Tab */}
      {activeTab === "benchmarks" && (
        <BenchmarkComparison portfolioId={portfolio?.id} />
      )}
    </div>
  );
};

export default PortfolioDetail;