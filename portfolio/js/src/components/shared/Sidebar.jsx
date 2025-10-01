import {
  Activity,
  BarChart3,
  Bookmark,
  BookOpen,
  LogOut,
  Plus,
  RefreshCw,
  Search,
  TrendingUp,
  User,
  Wallet,
  X,
} from "lucide-react";
import React from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useNavigationPreloader } from "../../hooks/useAssetPreloader";

const Sidebar = ({
  currentView = "dashboard",
  portfolios = [],
  selectedPortfolio = null,
  onPortfolioChange = () => {},
  onRefresh = () => {},
  onSearch = () => {},
  searchQuery = "",
  onSearchChange = () => {},
  showFilters = false,
  onToggleFilters = () => {},
  stats = null,
  recentTransactions = [],
  onQuickAction = () => {},
  isMobile = false,
  isOpen = true,
  onClose = () => {},
  onToggleSidebar = () => {},
}) => {
  const { user, logout } = useAuth();
  const { profile } = useAuth();
  const { transactionButtonProps, portfolioButtonProps, quickCreateProps } =
    useNavigationPreloader();

  const navigationItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: BarChart3,
      href: "/dashboard",
    },
    {
      id: "portfolio",
      label: "Portfolio",
      icon: TrendingUp,
      href: "/portfolio",
    },
    { id: "assets", label: "Assets", icon: Wallet, href: "/assets" },
    {
      id: "transactions",
      label: "Transactions",
      icon: Activity,
      href: "/transactions",
    },
    { id: "watchlist", label: "Watchlist", icon: Bookmark, href: "/watchlist" },
    {
      id: "concepts",
      label: "Financial Concepts",
      icon: BookOpen,
      href: "/concepts",
    },
  ];

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  if (isMobile && !isOpen) {
    return null;
  }

  return (
    <div
      className={`
            fixed lg:static inset-y-0 left-0 z-50 w-64 bg-dark-900 border-r border-dark-700 
            transform transition-transform duration-300 ease-in-out lg:translate-x-0
            ${isOpen ? "translate-x-0" : "-translate-x-full"}
        `}
    >
      {/* Sidebar Header */}
      <div className="flex items-center justify-between p-6 border-b border-dark-700">
        <h1 className="text-2xl font-bold text-gradient">Portfolia</h1>
        <button
          onClick={isMobile ? onClose : onToggleSidebar}
          className="lg:hidden p-2 rounded-lg hover:bg-dark-800 transition-colors"
        >
          <X size={20} className="text-gray-400" />
        </button>
      </div>

      {/* User Profile Section */}
      <div className="p-6 border-b border-dark-700">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-primary-600 rounded-full flex items-center justify-center">
            <User size={20} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-100 truncate">
              {profile?.first_name} {profile?.last_name}
            </p>
            <p className="text-xs text-gray-400 truncate">@{user?.username}</p>
          </div>
        </div>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-4 space-y-2">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          // Get preloader props based on item type
          const getPreloaderProps = () => {
            if (item.id === "transactions") return transactionButtonProps;
            if (item.id === "portfolio") return portfolioButtonProps;
            return {};
          };

          return (
            <Link
              key={item.id}
              to={item.href}
              className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? "bg-primary-600/20 text-primary-400"
                  : "text-gray-300 hover:bg-dark-800"
              }`}
              {...getPreloaderProps()}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Portfolio Selector (for Portfolio and Transactions views) */}
      {(currentView === "portfolio" || currentView === "transactions") &&
        portfolios.length > 0 && (
          <div className="p-4 border-t border-dark-700">
            <h3 className="text-sm font-medium text-gray-300 mb-3">
              Active Portfolio
            </h3>
            <select
              value={selectedPortfolio?.id || ""}
              onChange={(e) => {
                const portfolio = portfolios.find(
                  (p) => p.id === parseInt(e.target.value)
                );
                onPortfolioChange(portfolio);
              }}
              className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {portfolios.map((portfolio) => (
                <option key={portfolio.id} value={portfolio.id}>
                  {portfolio.name}
                </option>
              ))}
            </select>
          </div>
        )}

      {/* Search */}
      <div className="p-4 border-t border-dark-700">
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
            size={16}
          />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-4 border-t border-dark-700">
        <h3 className="text-sm font-medium text-gray-300 mb-3">
          Quick Actions
        </h3>
        <div className="space-y-2">
          <button
            onClick={() => onQuickAction("create-portfolio")}
            className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
          >
            <Plus size={16} />
            <span className="text-sm">New Portfolio</span>
          </button>
          <button
            onClick={() => onQuickAction("create-transaction")}
            className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
            {...quickCreateProps}
          >
            <Plus size={16} />
            <span className="text-sm">New Transaction</span>
          </button>
          <button
            onClick={() => onQuickAction("refresh")}
            className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
          >
            <RefreshCw size={16} />
            <span className="text-sm">Refresh Data</span>
          </button>
        </div>
      </div>

      {/* Logout Button */}
      <div className="p-4 border-t border-dark-700">
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center space-x-3 px-4 py-2 rounded-lg bg-danger-600/20 text-danger-400 hover:bg-danger-600/30 transition-colors"
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
