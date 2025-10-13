import {
    Calculator,
    Edit,
    X,
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { formatQuantity } from '../../utils/formatters';
import transactionTypes, { colorSchemes } from '../../utils/transactionTypes';

const EditTransactionModal = ({ isOpen, onClose, transaction, portfolios, onUpdate }) => {
    const [formData, setFormData] = useState({
        transaction_type: 'buy',
        asset_id: '',
        quantity: '',
        price: '',
        amount: '', // Optional amount field for UI calculation
        fees: '',
        notes: '',
        date: ''
    });
    const [loading, setLoading] = useState(false);
    const [showAllTransactionTypes, setShowAllTransactionTypes] = useState(false);

    // Helper function to get the selected transaction type details
    const getSelectedTransactionType = () => {
        return transactionTypes.find(type => type.value === formData.transaction_type) || transactionTypes[0];
    };

    // Get transaction types to display (common ones first, then all if expanded)
    const getDisplayedTransactionTypes = () => {
        const commonTypes = ['buy', 'sell', 'dividend'];

        if (!showAllTransactionTypes) {
            return transactionTypes.filter(type => commonTypes.includes(type.value));
        }

        return transactionTypes;
    };

    useEffect(() => {
        if (transaction) {
            setFormData({
                transaction_type: transaction.transaction_type || transaction.type || 'buy',
                asset_id: transaction.asset_id || '',
                quantity: transaction.quantity || '',
                price: transaction.price || '',
                fees: transaction.fees || '',
                notes: transaction.notes || '',
                date: transaction.transaction_date ? transaction.transaction_date.split('T')[0] : new Date().toISOString().split('T')[0]
            });
        }
    }, [transaction]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;

        // Handle amount/quantity/price calculations
        if (name === 'amount' || name === 'price') {
            const newFormData = { ...formData, [name]: value };

            // Auto-calculate quantity if both amount and price are present
            if (name === 'amount' && newFormData.price && parseFloat(newFormData.price) > 0) {
                const calculatedQuantity = parseFloat(value || 0) / parseFloat(newFormData.price);
                newFormData.quantity = calculatedQuantity > 0 ? calculatedQuantity.toFixed(6) : '';
            } else if (name === 'price' && newFormData.amount && parseFloat(value) > 0) {
                const calculatedQuantity = parseFloat(newFormData.amount) / parseFloat(value);
                newFormData.quantity = calculatedQuantity > 0 ? calculatedQuantity.toFixed(6) : '';
            }

            setFormData(newFormData);
        } else if (name === 'quantity') {
            // Clear amount when quantity is manually changed
            setFormData(prev => ({
                ...prev,
                [name]: value,
                amount: ''
            }));
        } else {
            setFormData(prev => ({
                ...prev,
                [name]: value
            }));
        }
    };


    const calculateTotal = () => {
        const quantity = parseFloat(formData.quantity) || 0;
        const price = parseFloat(formData.price) || 0;
        const fees = parseFloat(formData.fees) || 0;

        // Some transaction types don't involve monetary exchange
        const selectedType = getSelectedTransactionType();
        const monetaryTypes = ['buy', 'sell', 'dividend', 'fee', 'transfer_in', 'transfer_out'];

        if (!monetaryTypes.includes(selectedType.value)) {
            return fees; // Only fees for non-monetary transactions
        }

        return (quantity * price) + fees;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!formData.asset_id) {
            toast.error('Please select an asset from the search results. If the asset doesn\'t exist, add it first in the Assets section.');
            return;
        }

        // Validation based on transaction type
        const selectedType = getSelectedTransactionType();
        const requiresQuantity = !['fee'].includes(selectedType.value);
        const requiresPrice = ['buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'].includes(selectedType.value);

        if (requiresQuantity && (!formData.quantity || parseFloat(formData.quantity) <= 0)) {
            toast.error('Valid quantity is required');
            return;
        }

        if (requiresPrice && (!formData.price || parseFloat(formData.price) <= 0)) {
            toast.error('Valid price is required');
            return;
        }

        try {
            setLoading(true);

            const transactionData = {
                portfolio_id: transaction.portfolio_id,
                transaction_type: formData.transaction_type,
                asset_id: parseInt(formData.asset_id),
                quantity: parseFloat(formData.quantity) || 0,
                price: parseFloat(formData.price) || 0,
                fees: parseFloat(formData.fees) || 0,
                notes: formData.notes.trim(),
                transaction_date: formData.date,
                total_amount: calculateTotal()
            };

            await onUpdate(transaction.id, transactionData);
            onClose();
        } catch (error) {
            console.error('Error updating transaction:', error);
        } finally {
            setLoading(false);
        }
    };

    const totalAmount = calculateTotal();

    if (!isOpen || !transaction) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-dark-900 rounded-xl border border-dark-700 w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700 flex-shrink-0">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                            {(() => {
                                const selectedType = getSelectedTransactionType();
                                const IconComponent = selectedType.icon;
                                const colorScheme = colorSchemes[selectedType.color];
                                return <IconComponent size={20} className={colorScheme.text} />;
                            })()}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-100">Edit Transaction</h2>
                            <p className="text-sm text-gray-400">
                                Update {getSelectedTransactionType().label.toLowerCase()} transaction
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
                    >
                        <X size={20} className="text-gray-400" />
                    </button>
                </div>

                {/* Form */}
                <div className="flex-1 overflow-y-auto">
                    <form onSubmit={handleSubmit} className="p-6 space-y-6">
                        {/* Transaction Type */}
                        <div>
                            <div className="flex items-center justify-between mb-3">
                                <label className="block text-sm font-medium text-gray-300">
                                    Transaction Type
                                </label>
                                <button
                                    type="button"
                                    onClick={() => setShowAllTransactionTypes(!showAllTransactionTypes)}
                                    className="text-xs text-primary-400 hover:text-primary-300 transition-colors"
                                >
                                    {showAllTransactionTypes ? 'Show Less' : 'Show All Types'}
                                </button>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {getDisplayedTransactionTypes().map((type) => {
                                    const IconComponent = type.icon;
                                    const colorScheme = colorSchemes[type.color];
                                    const isSelected = formData.transaction_type === type.value;

                                    return (
                                        <button
                                            key={type.value}
                                            type="button"
                                            onClick={() => setFormData(prev => ({ ...prev, transaction_type: type.value }))}
                                            className={`p-3 rounded-lg border-2 transition-colors ${isSelected
                                                ? `${colorScheme.border} ${colorScheme.bg} ${colorScheme.text}`
                                                : `border-dark-600 bg-dark-800 text-gray-300 hover:border-dark-500 ${colorScheme.hover}`
                                                }`}
                                        >
                                            <div className="flex items-center space-x-3">
                                                <IconComponent size={18} className={isSelected ? colorScheme.text : 'text-gray-400'} />
                                                <div className="text-left flex-1">
                                                    <div className="font-medium text-sm">{type.label}</div>
                                                    <div className="text-xs opacity-75">{type.description}</div>
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Category indicator for selected type */}
                            {(() => {
                                const selectedType = getSelectedTransactionType();
                                return (
                                    <div className="mt-3 flex items-center space-x-2">
                                        <span className="text-xs text-gray-500">Category:</span>
                                        <span className={`text-xs px-2 py-1 rounded-full ${colorSchemes[selectedType.color].bg} ${colorSchemes[selectedType.color].text}`}>
                                            {selectedType.category.charAt(0).toUpperCase() + selectedType.category.slice(1)}
                                        </span>
                                    </div>
                                );
                            })()}
                        </div>

                        {/* Amount, Quantity and Price */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {(() => {
                                const selectedType = getSelectedTransactionType();
                                const requiresQuantity = !['fee'].includes(selectedType.value);
                                const requiresPrice = ['buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'].includes(selectedType.value);

                                return (
                                    <>
                                        {/* Amount field - optional helper for calculation */}
                                        {requiresQuantity && requiresPrice && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                                    Total Amount
                                                    <span className="text-xs text-gray-500 ml-1">(optional)</span>
                                                </label>
                                                <input
                                                    type="number"
                                                    name="amount"
                                                    value={formData.amount}
                                                    onChange={handleInputChange}
                                                    placeholder="0.00"
                                                    min="0"
                                                    step="0.01"
                                                    className="input-field w-full"
                                                />
                                                <div className="text-xs text-gray-500 mt-1">
                                                    Auto-calculates quantity when price is set
                                                </div>
                                            </div>
                                        )}
                                        {requiresQuantity && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                                    {selectedType.value === 'split' ? 'Split Ratio' : 'Quantity'} *
                                                </label>
                                                <input
                                                    type="number"
                                                    name="quantity"
                                                    value={formatQuantity(formData.quantity)}
                                                    onChange={handleInputChange}
                                                    placeholder={selectedType.value === 'split' ? "2" : "0.0000"}
                                                    min="0"
                                                    step={selectedType.value === 'split' ? "1" : "0.000001"}
                                                    className="input-field w-full"
                                                    required
                                                />
                                                {formData.quantity && (
                                                    <div className="text-xs text-gray-500 mt-1">
                                                        Exact: {parseFloat(formData.quantity || 0).toFixed(6)}
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        {requiresPrice && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                                    {(() => {
                                                        switch (selectedType.value) {
                                                            case 'dividend': return 'Dividend per Share';
                                                            case 'transfer_in':
                                                            case 'transfer_out': return 'Transfer Price';
                                                            default: return 'Price per Share';
                                                        }
                                                    })()} *
                                                </label>
                                                <input
                                                    type="number"
                                                    name="price"
                                                    value={formData.price}
                                                    onChange={handleInputChange}
                                                    placeholder="0.00"
                                                    min="0"
                                                    step="0.01"
                                                    className="input-field w-full"
                                                    required
                                                />
                                            </div>
                                        )}
                                        {/* Fee field always visible for all transaction types */}
                                        {!requiresPrice && !requiresQuantity && (
                                            <div className="md:col-span-3">
                                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                                    Fee Amount *
                                                </label>
                                                <input
                                                    type="number"
                                                    name="fees"
                                                    value={formData.fees}
                                                    onChange={handleInputChange}
                                                    placeholder="0.00"
                                                    min="0"
                                                    step="0.01"
                                                    className="input-field w-full"
                                                    required
                                                />
                                            </div>
                                        )}
                                    </>
                                );
                            })()}
                        </div>

                        {/* Fees and Date */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {(() => {
                                const selectedType = getSelectedTransactionType();
                                const showFeesField = selectedType.value !== 'fee'; // Don't show separate fees field for fee transactions

                                return (
                                    <>
                                        {showFeesField && (
                                            <div>
                                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                                    Additional Fees
                                                </label>
                                                <input
                                                    type="number"
                                                    name="fees"
                                                    value={formData.fees}
                                                    onChange={handleInputChange}
                                                    placeholder="0.00"
                                                    min="0"
                                                    step="0.01"
                                                    className="input-field w-full"
                                                />
                                            </div>
                                        )}
                                        <div className={showFeesField ? '' : 'md:col-span-2'}>
                                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                                Transaction Date
                                            </label>
                                            <input
                                                type="date"
                                                name="date"
                                                value={formData.date}
                                                onChange={handleInputChange}
                                                className="input-field w-full"
                                            />
                                        </div>
                                    </>
                                );
                            })()}
                        </div>

                        {/* Total Amount Display */}
                        <div className="bg-dark-800 rounded-lg p-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-2">
                                    <Calculator size={16} className="text-gray-400" />
                                    <span className="text-sm font-medium text-gray-300">
                                        {(() => {
                                            const selectedType = getSelectedTransactionType();
                                            switch (selectedType.value) {
                                                case 'buy': return 'Total Cost';
                                                case 'sell': return 'Total Proceeds';
                                                case 'dividend': return 'Dividend Amount';
                                                case 'fee': return 'Fee Amount';
                                                case 'transfer_in':
                                                case 'transfer_out': return 'Transfer Value';
                                                default: return 'Total Amount';
                                            }
                                        })()}
                                    </span>
                                </div>
                                <span className={`text-xl font-bold ${(() => {
                                    const selectedType = getSelectedTransactionType();
                                    const colorScheme = colorSchemes[selectedType.color];
                                    return colorScheme.text;
                                })()}`}>
                                    {(() => {
                                        const selectedType = getSelectedTransactionType();
                                        const sign = ['buy', 'fee', 'transfer_out'].includes(selectedType.value) ? '-' : '+';
                                        return `${sign}$${totalAmount.toFixed(2)}`;
                                    })()}
                                </span>
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                                {(() => {
                                    const selectedType = getSelectedTransactionType();
                                    const monetaryTypes = ['buy', 'sell', 'dividend', 'transfer_in', 'transfer_out'];

                                    if (monetaryTypes.includes(selectedType.value)) {
                                        return `${formatQuantity(formData.quantity) || 0} × $${formData.price || 0} + $${formData.fees || 0} fees`;
                                    } else {
                                        return `$${formData.fees || 0} fees only`;
                                    }
                                })()}
                            </div>
                        </div>

                        {/* Notes */}
                        <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                                Notes
                            </label>
                            <textarea
                                name="notes"
                                value={formData.notes}
                                onChange={handleInputChange}
                                placeholder="Optional notes about this transaction..."
                                rows={3}
                                className="input-field w-full resize-none"
                            />
                        </div>
                    </form>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end space-x-3 p-6 border-t border-dark-700 flex-shrink-0">
                    <button
                        type="button"
                        onClick={onClose}
                        className="btn-secondary"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        onClick={handleSubmit}
                        disabled={loading || !formData.asset_id}
                        className="btn-primary flex items-center space-x-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                <span>Updating...</span>
                            </>
                        ) : (
                            <>
                                <Edit size={16} />
                                <span>Update Transaction</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EditTransactionModal;
