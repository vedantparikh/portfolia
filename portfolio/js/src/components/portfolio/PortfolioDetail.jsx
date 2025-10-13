import {
  Activity,
  BarChart3,
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Download,
  Plus,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import { analyticsAPI, portfolioAPI } from "../../services/api";
import { formatCurrency } from "../../utils/formatters.jsx";
import {
  BenchmarkComparison,
  PortfolioAllocationManager,
  PortfolioAnalytics,
  RebalancingRecommendations,
} from "../analytics";
import LoadingSpinner from "../shared/LoadingSpinner";

const PortfolioDetail = ({ portfolio }) => {
  const [holdings, setHoldings] = useState([]);
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [sortConfig, setSortConfig] = useState({
    key: "value",
    direction: "descending",
  });

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

      // Get holdings from the API
      const holdingsResponse = await portfolioAPI.getPortfolioHoldings(
        portfolio.id
      );
      console.log("[PortfolioDetail] Holdings response:", holdingsResponse);

      // Process holdings data from API response
      let processedHoldings = [];
      if (
        holdingsResponse &&
        Array.isArray(holdingsResponse) &&
        holdingsResponse.length > 0
      ) {
        processedHoldings = holdingsResponse.map((holding) => ({
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
      }

      setHoldings(processedHoldings);
    } catch (error) {
      console.warn("[PortfolioDetail] Failed to load holdings:", error);
      // Set empty holdings on error to prevent crashes
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

  const sortedHoldings = useMemo(() => {
    let sortableHoldings = [...holdings];
    if (sortConfig.key) {
      sortableHoldings.sort((a, b) => {
        const valA = a[sortConfig.key];
        const valB = b[sortConfig.key];

        if (valA === null || valA === undefined) return 1;
        if (valB === null || valB === undefined) return -1;

        if (valA < valB) {
          return sortConfig.direction === "ascending" ? -1 : 1;
        }
        if (valA > valB) {
          return sortConfig.direction === "ascending" ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableHoldings;
  }, [holdings, sortConfig]);

  const requestSort = (key) => {
    let direction = "ascending";
    if (sortConfig.key === key && sortConfig.direction === "ascending") {
      direction = "descending";
    }
    setSortConfig({ key, direction });
  };

  const getSortIndicator = (columnKey) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronsUpDown size={14} className="ml-2 text-gray-500" />;
    }
    if (sortConfig.direction === "descending") {
      return <ChevronDown size={14} className="ml-2" />;
    }
    return <ChevronUp size={14} className="ml-2" />;
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
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-left">
                      <button
                        onClick={() => requestSort("name")}
                        className="flex items-center hover:text-gray-200"
                      >
                        Name {getSortIndicator("name")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("quantity")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Quantity {getSortIndicator("quantity")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("avgPrice")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Avg Price {getSortIndicator("avgPrice")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("currentPrice")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Current Price {getSortIndicator("currentPrice")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("value")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Value {getSortIndicator("value")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("gainLoss")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Unrealized G/L {getSortIndicator("gainLoss")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("todayGainLoss")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Today's G/L {getSortIndicator("todayGainLoss")}
                      </button>
                    </th>
                    <th className="py-3 px-4 text-sm font-medium text-gray-400 text-right">
                      <button
                        onClick={() => requestSort("realizedGainLoss")}
                        className="flex items-center ml-auto hover:text-gray-200"
                      >
                        Realized G/L {getSortIndicator("realizedGainLoss")}
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {loadingHoldings ? (
                    <tr>
                      <td colSpan="8" className="py-8 text-center">
                        <LoadingSpinner size="md" text="Loading holdings..." centered />
                      </td>
                    </tr>
                  ) : holdings.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="py-8 text-center">
                        <span className="text-gray-400">
                          No holdings found in this portfolio
                        </span>
                      </td>
                    </tr>
                  ) : (
                    sortedHoldings.map((holding, index) => (
                      <tr
                        key={holding.id || index}
                        className="border-b border-dark-800 hover:bg-dark-800/50 transition-colors"
                      >
                        <td className="py-3 px-4">
                          <span className="font-medium text-gray-100">
                            {holding.name}
                          </span>
                          <div className="text-xs text-gray-500">
                            {holding.symbol}
                          </div>
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
                            {(holding.realizedGainLossPercent || 0).toFixed(2)}
                            %
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
                        className={`text-lg font-bold ${totalRealizedGainLoss >= 0
                          ? "text-success-400"
                          : "text-danger-400"
                          }`}
                      >
                        {totalRealizedGainLoss >= 0 ? "+" : ""}
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

          {/* Portfolio Allocation Chart & Performance Summary */}
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
                            <div className="text-xs text-gray-500">
                              {holding.symbol}
                            </div>
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
                  <span className="text-sm text-gray-400">
                    Total Gain/Loss
                  </span>
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