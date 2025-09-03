import {
    Activity,
    ArrowLeft,
    BarChart3,
    DollarSign,
    Filter,
    Plus,
    RefreshCw,
    Search,
    TrendingDown,
    TrendingUp
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { portfolioAPI, transactionAPI } from '../../services/api';
import CreateTransactionModal from './CreateTransactionModal';
import EditTransactionModal from './EditTransactionModal';
import TransactionCard from './TransactionCard';
import TransactionFilters from './TransactionFilters';
import TransactionsTest from './TransactionsTest';

const Transactions = () => {
    const [transactions, setTransactions] = useState([]);
    const [filteredTransactions, setFilteredTransactions] = useState([]);
    const [portfolios, setPortfolios] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingTransaction, setEditingTransaction] = useState(null);
    const [showFilters, setShowFilters] = useState(false);
    const [selectedTransaction, setSelectedTransaction] = useState(null);
    const [filters, setFilters] = useState({
        portfolio: 'all',
        type: 'all',
        dateRange: 'all',
        sortBy: 'created_at',
        sortOrder: 'desc'
    });

    // Load data on component mount
    useEffect(() => {
        loadData();
    }, []);

    // Filter transactions when search query or filters change
    useEffect(() => {
        filterTransactions();
    }, [transactions, searchQuery, filters]);

    const loadData = async () => {
        try {
            setLoading(true);

            // Load portfolios
            const portfoliosResponse = await portfolioAPI.getPortfolios();
            setPortfolios(portfoliosResponse.portfolios || []);

            // Load transactions
            const transactionsResponse = await transactionAPI.getTransactions({
                limit: 100,
                order_by: 'created_at',
                order: 'desc'
            });
            setTransactions(transactionsResponse.transactions || []);
        } catch (error) {
            console.error('Failed to load data:', error);
            toast.error('Failed to load transaction data');
        } finally {
            setLoading(false);
        }
    };

    const filterTransactions = () => {
        let filtered = [...transactions];

        // Search filter
        if (searchQuery) {
            filtered = filtered.filter(transaction =>
                transaction.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
                transaction.portfolio_name?.toLowerCase().includes(searchQuery.toLowerCase())
            );
        }

        // Portfolio filter
        if (filters.portfolio !== 'all') {
            filtered = filtered.filter(transaction => transaction.portfolio_id === parseInt(filters.portfolio));
        }

        // Type filter
        if (filters.type !== 'all') {
            filtered = filtered.filter(transaction => transaction.type === filters.type);
        }

        // Date range filter
        if (filters.dateRange !== 'all') {
            const now = new Date();
            const filterDate = new Date();

            switch (filters.dateRange) {
                case 'today':
                    filterDate.setHours(0, 0, 0, 0);
                    break;
                case 'week':
                    filterDate.setDate(now.getDate() - 7);
                    break;
                case 'month':
                    filterDate.setMonth(now.getMonth() - 1);
                    break;
                case 'quarter':
                    filterDate.setMonth(now.getMonth() - 3);
                    break;
                case 'year':
                    filterDate.setFullYear(now.getFullYear() - 1);
                    break;
            }

            filtered = filtered.filter(transaction =>
                new Date(transaction.created_at) >= filterDate
            );
        }

        // Sort
        filtered.sort((a, b) => {
            let aValue, bValue;

            switch (filters.sortBy) {
                case 'created_at':
                    aValue = new Date(a.created_at);
                    bValue = new Date(b.created_at);
                    break;
                case 'amount':
                    aValue = a.total_amount || 0;
                    bValue = b.total_amount || 0;
                    break;
                case 'symbol':
                    aValue = a.symbol.toLowerCase();
                    bValue = b.symbol.toLowerCase();
                    break;
                default:
                    aValue = new Date(a.created_at);
                    bValue = new Date(b.created_at);
            }

            if (filters.sortOrder === 'asc') {
                return aValue > bValue ? 1 : -1;
            } else {
                return aValue < bValue ? 1 : -1;
            }
        });

        setFilteredTransactions(filtered);
    };

    const handleCreateTransaction = async (transactionData) => {
        try {
            const response = await transactionAPI.createBuyTransaction(transactionData);
            setTransactions(prev => [response, ...prev]);
            setShowCreateModal(false);
            toast.success('Transaction created successfully');
        } catch (error) {
            console.error('Failed to create transaction:', error);
            toast.error('Failed to create transaction');
        }
    };

    const handleUpdateTransaction = async (transactionId, transactionData) => {
        try {
            console.log('[Transactions] Updating transaction with data:', transactionData);
            const response = await transactionAPI.updateTransaction(transactionId, transactionData);
            console.log('[Transactions] Update response:', response);

            // Handle different response formats
            let updatedTransaction = response;
            if (response.transaction) {
                updatedTransaction = response.transaction;
            } else if (response.data) {
                updatedTransaction = response.data;
            }

            setTransactions(prev => prev.map(t => t.id === transactionId ? updatedTransaction : t));
            setShowEditModal(false);
            setEditingTransaction(null);
            toast.success('Transaction updated successfully');
        } catch (error) {
            console.error('Failed to update transaction:', error);
            toast.error('Failed to update transaction');
        }
    };

    const handleDeleteTransaction = async (transactionId) => {
        try {
            await transactionAPI.deleteTransaction(transactionId);
            setTransactions(prev => prev.filter(t => t.id !== transactionId));
            toast.success('Transaction deleted successfully');
        } catch (error) {
            console.error('Failed to delete transaction:', error);
            toast.error('Failed to delete transaction');
        }
    };

    const handleEditTransaction = (transaction) => {
        setEditingTransaction(transaction);
        setShowEditModal(true);
    };

    const handleRefresh = () => {
        loadData();
        toast.success('Transaction data refreshed');
    };

    const getTransactionStats = () => {
        const totalTransactions = filteredTransactions.length;
        const buyTransactions = filteredTransactions.filter(t => t.type === 'buy').length;
        const sellTransactions = filteredTransactions.filter(t => t.type === 'sell').length;
        const totalVolume = filteredTransactions.reduce((sum, t) => sum + (t.total_amount || 0), 0);
        const totalBuys = filteredTransactions
            .filter(t => t.type === 'buy')
            .reduce((sum, t) => sum + (t.total_amount || 0), 0);
        const totalSells = filteredTransactions
            .filter(t => t.type === 'sell')
            .reduce((sum, t) => sum + (t.total_amount || 0), 0);

        return {
            totalTransactions,
            buyTransactions,
            sellTransactions,
            totalVolume,
            totalBuys,
            totalSells
        };
    };

    const stats = getTransactionStats();

    if (loading) {
        return (
            <div className="min-h-screen gradient-bg flex items-center justify-center">
                <div className="text-center">
                    <RefreshCw className="w-8 h-8 text-primary-400 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading transactions...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen gradient-bg">
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
                                onClick={() => setShowFilters(!showFilters)}
                                className="btn-outline flex items-center space-x-2"
                            >
                                <Filter size={16} />
                                <span>Filters</span>
                            </button>
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="btn-primary flex items-center space-x-2"
                            >
                                <Plus size={16} />
                                <span>New Transaction</span>
                            </button>
                        </div>
                    </div>

                    <div className="mb-4">
                        <h1 className="text-3xl font-bold text-gray-100 mb-2">Transactions</h1>
                        <p className="text-gray-400">Track and manage your trading activity</p>
                    </div>

                    {/* Search Bar */}
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                        <input
                            type="text"
                            placeholder="Search transactions by symbol or portfolio..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="input-field w-full pl-10 pr-4 py-3"
                        />
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Total Transactions</p>
                                <p className="text-2xl font-bold text-gray-100">{stats.totalTransactions}</p>
                            </div>
                            <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                <Activity size={24} className="text-primary-400" />
                            </div>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Buy Orders</p>
                                <p className="text-2xl font-bold text-success-400">{stats.buyTransactions}</p>
                            </div>
                            <div className="w-12 h-12 bg-success-600/20 rounded-lg flex items-center justify-center">
                                <TrendingUp size={24} className="text-success-400" />
                            </div>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Sell Orders</p>
                                <p className="text-2xl font-bold text-danger-400">{stats.sellTransactions}</p>
                            </div>
                            <div className="w-12 h-12 bg-danger-600/20 rounded-lg flex items-center justify-center">
                                <TrendingDown size={24} className="text-danger-400" />
                            </div>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Total Volume</p>
                                <p className="text-2xl font-bold text-gray-100">
                                    ${stats.totalVolume.toLocaleString()}
                                </p>
                            </div>
                            <div className="w-12 h-12 bg-warning-600/20 rounded-lg flex items-center justify-center">
                                <DollarSign size={24} className="text-warning-400" />
                            </div>
                        </div>
                    </div>

                    <div className="card p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm text-gray-400">Net Flow</p>
                                <p className={`text-2xl font-bold ${(stats.totalBuys - stats.totalSells) >= 0 ? 'text-success-400' : 'text-danger-400'
                                    }`}>
                                    ${(stats.totalBuys - stats.totalSells).toLocaleString()}
                                </p>
                            </div>
                            <div className="w-12 h-12 bg-gray-600/20 rounded-lg flex items-center justify-center">
                                <BarChart3 size={24} className="text-gray-400" />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Filters */}
                {showFilters && (
                    <div className="card p-6 mb-8">
                        <TransactionFilters
                            filters={filters}
                            portfolios={portfolios}
                            onFilterChange={setFilters}
                        />
                    </div>
                )}

                {/* Transactions List */}
                {filteredTransactions.length === 0 ? (
                    <div className="space-y-6">
                        <div className="card p-12 text-center">
                            <Activity className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                            <h3 className="text-xl font-semibold text-gray-300 mb-2">No transactions found</h3>
                            <p className="text-gray-500 mb-6">
                                {searchQuery ? 'Try adjusting your search criteria' : 'Start by creating your first transaction'}
                            </p>
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="btn-primary flex items-center space-x-2 mx-auto"
                            >
                                <Plus size={16} />
                                <span>Create Transaction</span>
                            </button>
                        </div>

                        {/* Debug Test Component */}
                        <TransactionsTest />
                    </div>
                ) : (
                    <div className="space-y-4">
                        {filteredTransactions.map((transaction) => (
                            <TransactionCard
                                key={transaction.id}
                                transaction={transaction}
                                onEdit={() => handleEditTransaction(transaction)}
                                onDelete={() => handleDeleteTransaction(transaction.id)}
                            />
                        ))}
                    </div>
                )}

                {/* Create Transaction Modal */}
                {showCreateModal && (
                    <CreateTransactionModal
                        portfolios={portfolios}
                        onClose={() => setShowCreateModal(false)}
                        onCreate={handleCreateTransaction}
                    />
                )}

                {/* Edit Transaction Modal */}
                {showEditModal && editingTransaction && (
                    <EditTransactionModal
                        isOpen={showEditModal}
                        onClose={() => {
                            setShowEditModal(false);
                            setEditingTransaction(null);
                        }}
                        transaction={editingTransaction}
                        portfolios={portfolios}
                        onUpdate={handleUpdateTransaction}
                    />
                )}
            </div>
        </div>
    );
};

export default Transactions;
