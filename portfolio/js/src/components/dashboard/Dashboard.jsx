import {
    Activity,
    BarChart3,
    Bell,
    Bookmark,
    DollarSign,
    LogOut,
    Menu,
    Plus,
    RefreshCw,
    Settings,
    TrendingDown,
    TrendingUp,
    User,
    Wallet,
    X
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useAuth } from '../../contexts/AuthContext';
import { marketAPI, portfolioAPI, transactionAPI, watchlistAPI } from '../../services/api';
import EmailVerificationPrompt from '../auth/EmailVerificationPrompt';
import MarketInsights from './MarketInsights';
import PortfolioPerformance from './PortfolioPerformance';

const Dashboard = () => {
    const { user, logout } = useAuth();
    const { profile } = useAuth();
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [dashboardData, setDashboardData] = useState({
        portfolios: [],
        recentTransactions: [],
        topAssets: [],
        watchlists: [],
        marketStats: null,
        loading: true
    });

    const handleLogout = async () => {
        try {
            await logout();
            toast.success('Logged out successfully');
        } catch (error) {
            toast.error('Logout failed');
        }
    };

    const toggleSidebar = () => {
        setSidebarOpen(!sidebarOpen);
    };

    // Load dashboard data
    useEffect(() => {
        loadDashboardData();
    }, []);

    const loadDashboardData = async () => {
        try {
            setDashboardData(prev => ({ ...prev, loading: true }));

            // Load all data in parallel
            const [
                portfoliosResponse,
                transactionsResponse,
                assetsResponse,
                watchlistsResponse
            ] = await Promise.allSettled([
                portfolioAPI.getPortfolios(),
                transactionAPI.getTransactions({ limit: 5, order_by: 'created_at', order: 'desc' }),
                marketAPI.getAssets({ limit: 10, sort: 'market_cap' }),
                watchlistAPI.getWatchlists(true)
            ]);

            const portfolios = portfoliosResponse.status === 'fulfilled' ? portfoliosResponse.value.portfolios || [] : [];
            const recentTransactions = transactionsResponse.status === 'fulfilled' ? transactionsResponse.value.transactions || [] : [];
            const topAssets = assetsResponse.status === 'fulfilled' ? assetsResponse.value.assets || [] : [];
            const watchlists = watchlistsResponse.status === 'fulfilled' ? watchlistsResponse.value.watchlists || [] : [];

            // Calculate portfolio summaries
            const portfolioSummaries = await Promise.allSettled(
                portfolios.map(portfolio => portfolioAPI.getPortfolioSummary(portfolio.id))
            );

            const portfoliosWithStats = portfolios.map((portfolio, index) => ({
                ...portfolio,
                stats: portfolioSummaries[index].status === 'fulfilled' ? portfolioSummaries[index].value : null
            }));

            setDashboardData({
                portfolios: portfoliosWithStats,
                recentTransactions,
                topAssets,
                watchlists,
                marketStats: calculateMarketStats(topAssets),
                loading: false
            });
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            setDashboardData(prev => ({ ...prev, loading: false }));
        }
    };

    const calculateMarketStats = (assets) => {
        if (!assets || assets.length === 0) return null;

        const totalMarketCap = assets.reduce((sum, asset) => sum + (asset.market_cap || 0), 0);
        const totalVolume = assets.reduce((sum, asset) => sum + (asset.total_volume || 0), 0);
        const gainers = assets.filter(asset => (asset.price_change_percentage_24h || 0) > 0).length;
        const losers = assets.filter(asset => (asset.price_change_percentage_24h || 0) < 0).length;

        return {
            totalMarketCap,
            totalVolume,
            gainers,
            losers,
            totalAssets: assets.length
        };
    };

    const getTotalPortfolioValue = () => {
        return dashboardData.portfolios.reduce((sum, portfolio) => {
            return sum + (portfolio.stats?.total_value || 0);
        }, 0);
    };

    const getTotalGainLoss = () => {
        return dashboardData.portfolios.reduce((sum, portfolio) => {
            const totalValue = portfolio.stats?.total_value || 0;
            const totalCost = portfolio.stats?.total_cost || 0;
            return sum + (totalValue - totalCost);
        }, 0);
    };

    const getTotalGainLossPercent = () => {
        const totalValue = getTotalPortfolioValue();
        const totalCost = dashboardData.portfolios.reduce((sum, portfolio) => {
            return sum + (portfolio.stats?.total_cost || 0);
        }, 0);

        if (totalCost === 0) return 0;
        return ((totalValue - totalCost) / totalCost) * 100;
    };

    const handleRefresh = () => {
        loadDashboardData();
        toast.success('Dashboard data refreshed');
    };

    return (
        <div className="min-h-screen gradient-bg flex">
            {/* Mobile sidebar overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
                    onClick={toggleSidebar}
                />
            )}

            {/* Left Sidebar */}
            <div className={`
        fixed lg:static inset-y-0 left-0 z-50 w-64 bg-dark-900 border-r border-dark-700 
        transform transition-transform duration-300 ease-in-out lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
                {/* Sidebar Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <h1 className="text-2xl font-bold text-gradient">Portfolia</h1>
                    <button
                        onClick={toggleSidebar}
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
                            <p className="text-xs text-gray-400 truncate">
                                @{user?.username}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Navigation Menu */}
                <nav className="flex-1 p-4 space-y-2">
                    <a
                        href="#dashboard"
                        className="flex items-center space-x-3 px-3 py-2 rounded-lg bg-primary-600/20 text-primary-400 hover:bg-primary-600/30 transition-colors"
                    >
                        <BarChart3 size={18} />
                        <span>Dashboard</span>
                    </a>

                    <a
                        href="/portfolio"
                        className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
                    >
                        <TrendingUp size={18} />
                        <span>Portfolio</span>
                    </a>

                    <a
                        href="/assets"
                        className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
                    >
                        <Wallet size={18} />
                        <span>Assets</span>
                    </a>

                    <a
                        href="/transactions"
                        className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
                    >
                        <Activity size={18} />
                        <span>Transactions</span>
                    </a>
                    <a
                        href="/watchlist"
                        className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
                    >
                        <Bookmark size={18} />
                        <span>Watchlist</span>
                    </a>
                    <a
                        href="#settings"
                        className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gray-300 hover:bg-dark-800 transition-colors"
                    >
                        <Settings size={18} />
                        <span>Settings</span>
                    </a>
                </nav>

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

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
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
                                disabled={dashboardData.loading}
                                className="btn-secondary flex items-center space-x-2"
                            >
                                <RefreshCw size={16} className={dashboardData.loading ? 'animate-spin' : ''} />
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
                                <span className="ml-3 text-gray-400">Loading dashboard data...</span>
                            </div>
                        ) : (
                            <>
                                {/* Portfolio Stats Grid */}
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                                    <div className="card p-6">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-sm text-gray-400">Total Portfolio Value</p>
                                                <p className="text-2xl font-bold text-gray-100">
                                                    ${getTotalPortfolioValue().toLocaleString()}
                                                </p>
                                            </div>
                                            <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                                <TrendingUp size={24} className="text-primary-400" />
                                            </div>
                                        </div>
                                        <div className="mt-4 flex items-center text-sm">
                                            <span className={getTotalGainLossPercent() >= 0 ? 'text-success-400' : 'text-danger-400'}>
                                                {getTotalGainLossPercent() >= 0 ? '+' : ''}{getTotalGainLossPercent().toFixed(2)}%
                                            </span>
                                            <span className="text-gray-400 ml-2">total return</span>
                                        </div>
                                    </div>

                                    <div className="card p-6">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-sm text-gray-400">Total Gain/Loss</p>
                                                <p className={`text-2xl font-bold ${getTotalGainLoss() >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                                    {getTotalGainLoss() >= 0 ? '+' : ''}${getTotalGainLoss().toLocaleString()}
                                                </p>
                                            </div>
                                            <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                                                {getTotalGainLoss() >= 0 ? (
                                                    <TrendingUp size={24} className="text-success-400" />
                                                ) : (
                                                    <TrendingDown size={24} className="text-danger-400" />
                                                )}
                                            </div>
                                        </div>
                                        <div className="mt-4 flex items-center text-sm">
                                            <span className="text-gray-400">across all portfolios</span>
                                        </div>
                                    </div>

                                    <div className="card p-6">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-sm text-gray-400">Active Portfolios</p>
                                                <p className="text-2xl font-bold text-gray-100">{dashboardData.portfolios.length}</p>
                                            </div>
                                            <div className="w-12 h-12 bg-warning-600/20 rounded-lg flex items-center justify-center">
                                                <Wallet size={24} className="text-warning-400" />
                                            </div>
                                        </div>
                                        <div className="mt-4 flex items-center text-sm">
                                            <span className="text-gray-400">managed portfolios</span>
                                        </div>
                                    </div>

                                    <div className="card p-6">
                                        <div className="flex items-center justify-between">
                                            <div>
                                                <p className="text-sm text-gray-400">Watchlists</p>
                                                <p className="text-2xl font-bold text-gray-100">{dashboardData.watchlists.length}</p>
                                            </div>
                                            <div className="w-12 h-12 bg-gray-600/20 rounded-lg flex items-center justify-center">
                                                <Bookmark size={24} className="text-gray-400" />
                                            </div>
                                        </div>
                                        <div className="mt-4 flex items-center text-sm">
                                            <span className="text-gray-400">tracking lists</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Market Overview */}
                                {dashboardData.marketStats && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                                        <div className="card p-6">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-gray-400">Market Cap</p>
                                                    <p className="text-2xl font-bold text-gray-100">
                                                        ${(dashboardData.marketStats.totalMarketCap / 1e12).toFixed(2)}T
                                                    </p>
                                                </div>
                                                <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                                    <DollarSign size={24} className="text-primary-400" />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="card p-6">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-gray-400">24h Volume</p>
                                                    <p className="text-2xl font-bold text-gray-100">
                                                        ${(dashboardData.marketStats.totalVolume / 1e9).toFixed(2)}B
                                                    </p>
                                                </div>
                                                <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                                                    <Activity size={24} className="text-success-400" />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="card p-6">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-gray-400">Gainers</p>
                                                    <p className="text-2xl font-bold text-success-400">{dashboardData.marketStats.gainers}</p>
                                                </div>
                                                <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                                                    <TrendingUp size={24} className="text-success-400" />
                                                </div>
                                            </div>
                                        </div>

                                        <div className="card p-6">
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-sm text-gray-400">Losers</p>
                                                    <p className="text-2xl font-bold text-danger-400">{dashboardData.marketStats.losers}</p>
                                                </div>
                                                <div className="w-12 h-12 bg-danger-600/20 rounded-lg flex items-center justify-center">
                                                    <TrendingDown size={24} className="text-danger-400" />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Main Content Grid */}
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                                    {/* Portfolio Overview */}
                                    <div className="card p-6">
                                        <div className="flex items-center justify-between mb-6">
                                            <h3 className="text-lg font-semibold text-gray-100">Your Portfolios</h3>
                                            <a href="/portfolio" className="btn-primary text-sm flex items-center space-x-2">
                                                <Plus size={16} />
                                                <span>New Portfolio</span>
                                            </a>
                                        </div>

                                        {dashboardData.portfolios.length === 0 ? (
                                            <div className="text-center py-8">
                                                <Wallet className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                                <h4 className="text-lg font-semibold text-gray-300 mb-2">No portfolios yet</h4>
                                                <p className="text-gray-500 mb-4">Create your first portfolio to start tracking investments</p>
                                                <a href="/portfolio" className="btn-primary">Create Portfolio</a>
                                            </div>
                                        ) : (
                                            <div className="space-y-4">
                                                {dashboardData.portfolios.slice(0, 3).map((portfolio) => (
                                                    <div key={portfolio.id} className="flex items-center justify-between p-4 bg-dark-800 rounded-lg">
                                                        <div>
                                                            <h4 className="font-medium text-gray-100">{portfolio.name}</h4>
                                                            <p className="text-sm text-gray-400">{portfolio.description || 'No description'}</p>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className="font-semibold text-gray-100">
                                                                ${(portfolio.stats?.total_value || 0).toLocaleString()}
                                                            </p>
                                                            <p className={`text-sm ${(portfolio.stats?.total_value || 0) >= (portfolio.stats?.total_cost || 0) ? 'text-success-400' : 'text-danger-400'}`}>
                                                                {portfolio.stats?.total_value && portfolio.stats?.total_cost ?
                                                                    `${((portfolio.stats.total_value - portfolio.stats.total_cost) / portfolio.stats.total_cost * 100).toFixed(2)}%` :
                                                                    '0.00%'
                                                                }
                                                            </p>
                                                        </div>
                                                    </div>
                                                ))}
                                                {dashboardData.portfolios.length > 3 && (
                                                    <div className="text-center">
                                                        <a href="/portfolio" className="text-primary-400 hover:text-primary-300 text-sm">
                                                            View all {dashboardData.portfolios.length} portfolios →
                                                        </a>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>

                                    {/* Recent Transactions */}
                                    <div className="card p-6">
                                        <div className="flex items-center justify-between mb-6">
                                            <h3 className="text-lg font-semibold text-gray-100">Recent Transactions</h3>
                                            <a href="/transactions" className="text-primary-400 hover:text-primary-300 text-sm">
                                                View all →
                                            </a>
                                        </div>

                                        {dashboardData.recentTransactions.length === 0 ? (
                                            <div className="text-center py-8">
                                                <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                                <h4 className="text-lg font-semibold text-gray-300 mb-2">No transactions yet</h4>
                                                <p className="text-gray-500 mb-4">Start trading to see your transaction history</p>
                                                <a href="/transactions" className="btn-primary">Create Transaction</a>
                                            </div>
                                        ) : (
                                            <div className="space-y-3">
                                                {dashboardData.recentTransactions.map((transaction) => (
                                                    <div key={transaction.id} className="flex items-center justify-between p-3 bg-dark-800 rounded-lg">
                                                        <div className="flex items-center space-x-3">
                                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${transaction.type === 'buy' ? 'bg-success-400/20' : 'bg-danger-400/20'
                                                                }`}>
                                                                {transaction.type === 'buy' ? (
                                                                    <TrendingUp size={16} className="text-success-400" />
                                                                ) : (
                                                                    <TrendingDown size={16} className="text-danger-400" />
                                                                )}
                                                            </div>
                                                            <div>
                                                                <p className="text-sm font-medium text-gray-100">
                                                                    {transaction.type.toUpperCase()} {transaction.symbol}
                                                                </p>
                                                                <p className="text-xs text-gray-400">
                                                                    {new Date(transaction.created_at).toLocaleDateString()}
                                                                </p>
                                                            </div>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className={`text-sm font-medium ${transaction.type === 'buy' ? 'text-success-400' : 'text-danger-400'
                                                                }`}>
                                                                {transaction.type === 'buy' ? '-' : '+'}${transaction.total_amount}
                                                            </p>
                                                            <p className="text-xs text-gray-400">
                                                                {transaction.quantity} @ ${transaction.price}
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
                                            <h3 className="text-lg font-semibold text-gray-100">Top Market Assets</h3>
                                            <a href="/assets" className="text-primary-400 hover:text-primary-300 text-sm">
                                                View all assets →
                                            </a>
                                        </div>

                                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                                            {dashboardData.topAssets.slice(0, 5).map((asset) => (
                                                <div key={asset.id} className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors cursor-pointer">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <h4 className="font-medium text-gray-100">{asset.symbol}</h4>
                                                        <span className={`text-xs px-2 py-1 rounded ${(asset.price_change_percentage_24h || 0) >= 0
                                                            ? 'bg-success-400/20 text-success-400'
                                                            : 'bg-danger-400/20 text-danger-400'
                                                            }`}>
                                                            {(asset.price_change_percentage_24h || 0).toFixed(2)}%
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-gray-400 mb-1">{asset.name}</p>
                                                    <p className="text-lg font-semibold text-gray-100">
                                                        ${asset.current_price?.toFixed(2) || 'N/A'}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Quick Actions */}
                                <div className="card p-6">
                                    <h3 className="text-lg font-semibold text-gray-100 mb-6">Quick Actions</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                        <a href="/portfolio" className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                                            <Wallet className="w-8 h-8 text-primary-400 mx-auto mb-2" />
                                            <h4 className="font-medium text-gray-100">Create Portfolio</h4>
                                            <p className="text-sm text-gray-400">Start a new investment portfolio</p>
                                        </a>
                                        <a href="/transactions" className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                                            <Plus className="w-8 h-8 text-success-400 mx-auto mb-2" />
                                            <h4 className="font-medium text-gray-100">Add Transaction</h4>
                                            <p className="text-sm text-gray-400">Record a buy or sell transaction</p>
                                        </a>
                                        <a href="/assets" className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                                            <BarChart3 className="w-8 h-8 text-warning-400 mx-auto mb-2" />
                                            <h4 className="font-medium text-gray-100">Browse Assets</h4>
                                            <p className="text-sm text-gray-400">Explore market opportunities</p>
                                        </a>
                                        <a href="/watchlist" className="p-4 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors text-center">
                                            <Bookmark className="w-8 h-8 text-danger-400 mx-auto mb-2" />
                                            <h4 className="font-medium text-gray-100">Manage Watchlists</h4>
                                            <p className="text-sm text-gray-400">Track your favorite assets</p>
                                        </a>
                                    </div>
                                </div>

                                {/* Advanced Dashboard Sections */}
                                <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                                    {/* Portfolio Performance */}
                                    {dashboardData.portfolios.length > 0 && (
                                        <PortfolioPerformance portfolios={dashboardData.portfolios} />
                                    )}

                                    {/* Market Insights */}
                                    <MarketInsights />
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
