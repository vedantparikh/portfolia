import {
    AlertTriangle,
    CheckCircle,
    Edit2,
    Plus,
    Save,
    Search,
    Trash2,
    X
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { ClientSideAssetSearch } from '../shared';

const ParsedDataTable = ({
    parsedData,
    onSave,
    onCancel,
    portfolios = []
}) => {
    const [transactions, setTransactions] = useState([]);
    const [editingRow, setEditingRow] = useState(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [filterType, setFilterType] = useState('all');
    const [selectedPortfolio, setSelectedPortfolio] = useState('');

    // Transaction types configuration (same as CreateTransactionModal)
    const transactionTypes = [
        { value: 'buy', label: 'Buy' },
        { value: 'sell', label: 'Sell' },
        { value: 'dividend', label: 'Dividend' },
        { value: 'split', label: 'Stock Split' },
        { value: 'merger', label: 'Merger' },
        { value: 'spin_off', label: 'Spin-off' },
        { value: 'rights_issue', label: 'Rights Issue' },
        { value: 'stock_option_exercise', label: 'Option Exercise' },
        { value: 'transfer_in', label: 'Transfer In' },
        { value: 'transfer_out', label: 'Transfer Out' },
        { value: 'fee', label: 'Fee' },
        { value: 'other', label: 'Other' }
    ];

    useEffect(() => {
        if (parsedData?.transactions) {
            setTransactions(parsedData.transactions);
        }
    }, [parsedData]);

    const handleEdit = (index) => {
        setEditingRow(index);
    };

    const handleSave = (index) => {
        setEditingRow(null);
    };

    const handleCancel = () => {
        setEditingRow(null);
    };

    const handleDelete = (index) => {
        const newTransactions = transactions.filter((_, i) => i !== index);
        setTransactions(newTransactions);
        toast.success('Transaction removed');
    };

    const handleAddNew = () => {
        const newTransaction = {
            id: `temp_${Date.now()}`,
            transaction_date: new Date().toISOString().split('T')[0],
            transaction_type: 'buy',
            name: '',
            symbol: '',
            total_amount: 0,
            quantity: 0,
            price: 0,
            fees: 0,
        };
        setTransactions([...transactions, newTransaction]);
        setEditingRow(transactions.length);
    };

    const handleFieldChange = (index, field, value) => {
        const newTransactions = [...transactions];
        newTransactions[index] = {
            ...newTransactions[index],
            [field]: value
        };

        // Auto-calculate total_amount if quantity or price changes
        if (field === 'quantity' || field === 'price' || field === 'fees') {
            const quantity = parseFloat(newTransactions[index].quantity) || 0;
            const price = parseFloat(newTransactions[index].price) || 0;
            const fees = parseFloat(newTransactions[index].fees) || 0;
            newTransactions[index].total_amount = (quantity * price) + fees;
        }

        setTransactions(newTransactions);
    };

    const handleSymbolSelect = (asset, index) => {
        handleFieldChange(index, 'symbol', asset.symbol);
        handleFieldChange(index, 'name', asset.name);
    };

    const handleSymbolChange = (value, index) => {
        handleFieldChange(index, 'symbol', value);
        // Clear name when manually typing
        if (!value) {
            handleFieldChange(index, 'name', '');
        }
    };

    const handleBulkSave = async () => {
        if (!selectedPortfolio) {
            toast.error('Please select a portfolio');
            return;
        }

        if (transactions.length === 0) {
            toast.error('No transactions to save');
            return;
        }

        try {
            const transactionData = transactions.map(txn => ({
                transaction_date: txn.transaction_date,
                transaction_type: txn.transaction_type,
                symbol: txn.symbol,
                quantity: parseFloat(txn.quantity) || 0,
                price: parseFloat(txn.price) || 0,
                fees: parseFloat(txn.fees) || 0,
                notes: `Imported from ${parsedData.provider} statement`
            }));

            await onSave(selectedPortfolio, transactionData);
        } catch (error) {
            console.error('Failed to save transactions:', error);
            toast.error('Failed to save transactions');
        }
    };

    const filteredTransactions = transactions.filter(txn => {
        const matchesSearch = !searchQuery ||
            txn.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            txn.symbol.toLowerCase().includes(searchQuery.toLowerCase());

        const matchesFilter = filterType === 'all' || txn.transaction_type === filterType;

        return matchesSearch && matchesFilter;
    });


    if (!parsedData) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-700">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                            <CheckCircle className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-gray-100">Review Parsed Transactions</h2>
                            <p className="text-sm text-gray-400">
                                {parsedData.provider} • {parsedData.metadata?.total_transactions || 0} transactions found
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onCancel}
                        className="text-gray-400 hover:text-gray-300 transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Controls */}
                <div className="p-6 border-b border-gray-700 space-y-4">
                    <div className="flex flex-wrap items-center gap-4">
                        {/* Search */}
                        <div className="relative flex-1 min-w-64">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
                            <input
                                type="text"
                                placeholder="Search transactions..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="input-field pl-10 pr-4 py-2 w-full"
                            />
                        </div>

                        {/* Filter */}
                        <select
                            value={filterType}
                            onChange={(e) => setFilterType(e.target.value)}
                            className="input-field py-2 px-3"
                        >
                            <option value="all">All Types</option>
                            {transactionTypes.map(type => (
                                <option key={type.value} value={type.value}>
                                    {type.label}
                                </option>
                            ))}
                        </select>

                        {/* Portfolio Selection */}
                        <select
                            value={selectedPortfolio}
                            onChange={(e) => setSelectedPortfolio(e.target.value)}
                            className="input-field py-2 px-3"
                        >
                            <option value="">Select Portfolio</option>
                            {portfolios.map(portfolio => (
                                <option key={portfolio.id} value={portfolio.id}>
                                    {portfolio.name}
                                </option>
                            ))}
                        </select>

                        {/* Add New */}
                        <button
                            onClick={handleAddNew}
                            className="btn-outline flex items-center space-x-2"
                        >
                            <Plus size={16} />
                            <span>Add Transaction</span>
                        </button>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center space-x-6 text-sm text-gray-400">
                        <div className="flex items-center space-x-2">
                            <span>Period:</span>
                            <span className="font-medium">
                                {parsedData.statement_period?.start_date} - {parsedData.statement_period?.end_date}
                            </span>
                        </div>
                    </div>

                    {/* Warnings */}
                    {parsedData.metadata?.warnings && parsedData.metadata.warnings.length > 0 && (
                        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                            <div className="flex items-start space-x-2">
                                <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />
                                <div className="text-sm text-yellow-200">
                                    <div className="font-medium mb-1">Parsing Warnings:</div>
                                    <ul className="space-y-1">
                                        {parsedData.metadata.warnings.map((warning, index) => (
                                            <li key={index} className="text-yellow-300/80">• {warning}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Table */}
                <div className="overflow-x-auto max-h-96">
                    <table className="w-full">
                        <thead className="bg-gray-700 sticky top-0">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Date
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Type
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Name
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Symbol
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Quantity
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Price
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Fees
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Total
                                </th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {filteredTransactions.map((transaction, index) => (
                                <tr key={transaction.id} className="hover:bg-gray-700/50">
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        {editingRow === index ? (
                                            <input
                                                type="date"
                                                value={transaction.transaction_date}
                                                onChange={(e) => handleFieldChange(index, 'transaction_date', e.target.value)}
                                                className="input-field py-1 px-2 text-sm w-full"
                                            />
                                        ) : (
                                            transaction.transaction_date
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        {editingRow === index ? (
                                            <select
                                                value={transaction.transaction_type}
                                                onChange={(e) => handleFieldChange(index, 'transaction_type', e.target.value)}
                                                className="input-field py-1 px-2 text-sm w-full"
                                            >
                                                {transactionTypes.map(type => (
                                                    <option key={type.value} value={type.value}>
                                                        {type.label}
                                                    </option>
                                                ))}
                                            </select>
                                        ) : (
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${transaction.transaction_type === 'buy'
                                                ? 'bg-success-500/20 text-success-400'
                                                : transaction.transaction_type === 'sell'
                                                    ? 'bg-danger-500/20 text-danger-400'
                                                    : 'bg-primary-500/20 text-primary-400'
                                                }`}>
                                                {transactionTypes.find(t => t.value === transaction.transaction_type)?.label || transaction.transaction_type}
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        {editingRow === index ? (
                                            <input
                                                type="text"
                                                value={transaction.name}
                                                onChange={(e) => handleFieldChange(index, 'name', e.target.value)}
                                                className="input-field py-1 px-2 text-sm w-full"
                                                placeholder="Company name"
                                            />
                                        ) : (
                                            transaction.name
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        {editingRow === index ? (
                                            <ClientSideAssetSearch
                                                value={transaction.symbol}
                                                onChange={(value) => handleSymbolChange(value, index)}
                                                onSelect={(asset) => handleSymbolSelect(asset, index)}
                                                placeholder="Search symbol..."
                                                showSuggestions={true}
                                                preloadAssets={true}
                                            />
                                        ) : (
                                            transaction.symbol || '-'
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        {editingRow === index ? (
                                            <input
                                                type="number"
                                                step="0.0001"
                                                value={transaction.quantity}
                                                onChange={(e) => handleFieldChange(index, 'quantity', e.target.value)}
                                                className="input-field py-1 px-2 text-sm w-full"
                                            />
                                        ) : (
                                            transaction.quantity
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        {editingRow === index ? (
                                            <input
                                                type="number"
                                                step="0.01"
                                                value={transaction.price}
                                                onChange={(e) => handleFieldChange(index, 'price', e.target.value)}
                                                className="input-field py-1 px-2 text-sm w-full"
                                            />
                                        ) : (
                                            `$${transaction.price || '0.00'}`
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        {editingRow === index ? (
                                            <input
                                                type="number"
                                                step="0.01"
                                                value={transaction.fees}
                                                onChange={(e) => handleFieldChange(index, 'fees', e.target.value)}
                                                className="input-field py-1 px-2 text-sm w-full"
                                            />
                                        ) : (
                                            `$${transaction.fees || '0.00'}`
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-sm text-gray-300">
                                        ${transaction.total_amount || '0.00'}
                                    </td>
                                    <td className="px-4 py-3 text-sm">
                                        <div className="flex items-center space-x-2">
                                            {editingRow === index ? (
                                                <>
                                                    <button
                                                        onClick={() => handleSave(index)}
                                                        className="text-success-400 hover:text-success-300"
                                                    >
                                                        <Save size={16} />
                                                    </button>
                                                    <button
                                                        onClick={handleCancel}
                                                        className="text-gray-400 hover:text-gray-300"
                                                    >
                                                        <X size={16} />
                                                    </button>
                                                </>
                                            ) : (
                                                <>
                                                    <button
                                                        onClick={() => handleEdit(index)}
                                                        className="text-primary-400 hover:text-primary-300"
                                                    >
                                                        <Edit2 size={16} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(index)}
                                                        className="text-danger-400 hover:text-danger-300"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-6 border-t border-gray-700">
                    <div className="text-sm text-gray-400">
                        {filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? 's' : ''} ready to import
                    </div>
                    <div className="flex items-center space-x-3">
                        <button
                            onClick={onCancel}
                            className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleBulkSave}
                            disabled={!selectedPortfolio || transactions.length === 0}
                            className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Save size={16} />
                            <span>Import {transactions.length} Transactions</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ParsedDataTable;
