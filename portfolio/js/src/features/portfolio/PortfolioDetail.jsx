import { useMoney } from "../../hooks/useMoney";
import {
  Activity,
  BarChart3,
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  RefreshCw,
  Target,
  TrendingUp,
} from "lucide-react";
import { useMemo, useState } from "react";
import { usePortfolioAccountSummary, usePortfolioHoldings } from "./queries";
import { formatPercentage, getChangeColor } from "../../utils/formatters.jsx";
import {
  BenchmarkComparison,
  PortfolioAllocationManager,
  PortfolioAnalytics,
  RebalancingRecommendations,
} from "../analytics";
import LoadingSpinner from "../../shared/ui/Spinner";
import StatCard from "../../components/shared/StatCard";
import AllocationDonut from "./AllocationDonut";
import ValueVsInvestedChart from "./ValueVsInvestedChart";

const PortfolioDetail = ({ portfolio }) => {
  const money = useMoney();
  const [activeTab, setActiveTab] = useState("overview");
  const [sortConfig, setSortConfig] = useState({
    key: "value",
    direction: "descending",
  });

  const holdingsQuery = usePortfolioHoldings(portfolio?.id);
  const { data: summary = null } = usePortfolioAccountSummary(portfolio?.id ?? null);
  const loadingHoldings = holdingsQuery.isPending || holdingsQuery.isFetching;
  const loadHoldings = () => holdingsQuery.refetch();

  const holdings = useMemo(
    () =>
      Array.isArray(holdingsQuery.data)
        ? holdingsQuery.data.map((holding) => ({
            id: holding.asset_id,
            symbol: holding.symbol,
            name: holding.name,
            quantity: holding.quantity,
            avgPrice: holding.cost_basis,
            currentPrice: holding.current_price,
            value: holding.current_value,
            change: holding.unrealized_pnl_percent,
            gainLoss: holding.unrealized_pnl,
            todayGainLoss: holding.today_pnl,
            todayGainLossPercent: holding.today_pnl_percent,
            realizedGainLoss: holding.realized_pnl,
            realizedGainLossPercent: holding.realized_pnl_percent,
          }))
        : [],
    [holdingsQuery.data],
  );

  const [showClosed, setShowClosed] = useState(false);
  const closedCount = useMemo(
    () => holdings.filter((holding) => !(Number(holding.quantity) > 0)).length,
    [holdings],
  );

  const sortedHoldings = useMemo(() => {
    let sortableHoldings = showClosed
      ? [...holdings]
      : holdings.filter((holding) => Number(holding.quantity) > 0);
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
  }, [holdings, sortConfig, showClosed]);

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

  const totalHoldingsValue = summary?.total_current_value ?? 0;
  const totalRealizedGainLoss = summary?.total_realized_pnl ?? 0;

  const signed = (v) => money(v, { signDisplay: "exceptZero" });

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
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Value" info="value"
              className="col-span-2 lg:col-span-1"
              value={summary ? money(summary.total_current_value) : "—"}
              sub={summary ? `${summary.total_assets} holdings` : null}
            />
            <StatCard
              label="Invested" info="cost_basis"
              value={summary ? money(summary.total_cost_basis) : "—"}
              sub="Cost basis"
            />
            <StatCard
              label="Unrealized P&L" info="unrealized_pnl"
              value={summary ? signed(summary.total_unrealized_pnl) : "—"}
              valueClassName={getChangeColor(summary?.total_unrealized_pnl)}
              sub={
                summary
                  ? formatPercentage(summary.total_unrealized_pnl_percent, { showSign: true })
                  : null
              }
            />
            <StatCard
              label="Today" info="today_pnl"
              value={summary ? signed(summary.today_pnl) : "—"}
              valueClassName={getChangeColor(summary?.today_pnl)}
              sub={
                summary
                  ? formatPercentage(summary.today_pnl_percent, { showSign: true })
                  : null
              }
            />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              label="Realized P&L" info="realized_pnl"
              value={summary ? signed(summary.total_realized_pnl) : "—"}
              valueClassName={getChangeColor(summary?.total_realized_pnl)}
              sub="Sales, before tax"
            />
            <StatCard
              label="Dividends" info="dividends"
              value={summary ? money(summary.total_dividends) : "—"}
              sub="Before tax"
            />
            <StatCard
              label="Taxes paid" info="taxes_paid"
              value={summary ? money(summary.net_taxes_paid) : "—"}
              sub={
                summary
                  ? summary.tax_adjustments
                    ? `${money(summary.taxes_withheld)} withheld, ${signed(summary.tax_adjustments)} adjusted`
                    : "Withheld on sales and dividends"
                  : null
              }
            />
            <StatCard
              label="Realized after tax" info="realized_after_tax"
              value={summary ? signed(summary.realized_after_tax) : "—"}
              valueClassName={getChangeColor(summary?.realized_after_tax)}
              sub="Realized + dividends − taxes"
            />
          </div>

          {/* Holdings Overview */}
          <div className="card p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-100">Holdings</h3>
              <div className="flex items-center space-x-4">
                {closedCount > 0 && (
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <input
                      type="checkbox"
                      checked={showClosed}
                      onChange={(e) => setShowClosed(e.target.checked)}
                    />
                    Show closed positions ({closedCount})
                  </label>
                )}
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
                        Today&apos;s G/L {getSortIndicator("todayGainLoss")}
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
                        <LoadingSpinner type="analyst" size="md" text="Loading holdings..." centered />
                      </td>
                    </tr>
                  ) : sortedHoldings.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="py-8 text-center">
                        <span className="text-gray-400">
                          {holdings.length === 0
                            ? "No holdings found in this portfolio"
                            : "All positions are closed"}
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
                            {money(holding.avgPrice)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-gray-100">
                            {money(holding.currentPrice)}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-gray-100 font-medium">
                            {money(holding.value)}
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
                            {money(holding.gainLoss || 0)}
                          </span>
                          <p
                            className={`font-medium ${(holding.change || 0) >= 0
                              ? "text-success-400"
                              : "text-danger-400"
                              }`}
                          >
                            {(holding.change || 0) >= 0 ? "+" : ""}
                            {formatPercentage(holding.change || 0, { showSign: false })}
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
                            {money(holding.todayGainLoss || 0)}
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
                            {formatPercentage(holding.todayGainLossPercent || 0, { showSign: false })}
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
                            {money(holding.realizedGainLoss || 0)}
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
                            {formatPercentage(holding.realizedGainLossPercent || 0, { showSign: false })}
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
                        {money(totalHoldingsValue)}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-bold">
                      <p className={getChangeColor(summary?.total_unrealized_pnl)}>
                        {signed(summary?.total_unrealized_pnl)}
                      </p>
                      <p className={`text-sm ${getChangeColor(summary?.total_unrealized_pnl_percent)}`}>
                        {formatPercentage(summary?.total_unrealized_pnl_percent, { showSign: true })}
                      </p>
                    </td>
                    <td className="py-3 px-4 text-right font-bold">
                      <p className={getChangeColor(summary?.today_pnl)}>
                        {signed(summary?.today_pnl)}
                      </p>
                      <p className={`text-sm ${getChangeColor(summary?.today_pnl_percent)}`}>
                        {formatPercentage(summary?.today_pnl_percent, { showSign: true })}
                      </p>
                    </td>
                    <td className="py-3 px-4 text-right font-bold">
                      <p className={getChangeColor(totalRealizedGainLoss)}>
                        {signed(totalRealizedGainLoss)}
                      </p>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>

          {/* Portfolio Allocation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">
                Asset Allocation
              </h3>
              <AllocationDonut portfolioId={portfolio?.id} />
            </div>
            <div className="card p-6">
              <ValueVsInvestedChart portfolioId={portfolio?.id} />
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
        <BenchmarkComparison portfolioId={portfolio?.id} currency={portfolio?.currency} />
      )}
    </div>
  );
};

export default PortfolioDetail;