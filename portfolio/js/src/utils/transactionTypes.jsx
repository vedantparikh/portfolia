import {
    ArrowDownLeft,
    ArrowUpRight,
    Calculator,
    CircleDollarSign,
    Copy,
    Gift,
    GitBranch,
    Merge,
    Repeat,
    TrendingDown,
    TrendingUp,
    Zap
} from 'lucide-react';

const transactionTypes = [
    { value: 'buy', label: 'Buy', description: 'Purchase assets', icon: TrendingUp, color: 'success', category: 'trading' },
    { value: 'sell', label: 'Sell', description: 'Sell assets', icon: TrendingDown, color: 'danger', category: 'trading' },
    { value: 'dividend', label: 'Dividend', description: 'Dividend payment', icon: CircleDollarSign, color: 'primary', category: 'income' },
    { value: 'split', label: 'Stock Split', description: 'Stock split event', icon: Copy, color: 'info', category: 'corporate' },
    { value: 'merger', label: 'Merger', description: 'Company merger', icon: Merge, color: 'warning', category: 'corporate' },
    { value: 'spin_off', label: 'Spin-off', description: 'Corporate spin-off', icon: GitBranch, color: 'info', category: 'corporate' },
    { value: 'rights_issue', label: 'Rights Issue', description: 'Rights offering', icon: Gift, color: 'primary', category: 'corporate' },
    { value: 'stock_option_exercise', label: 'Option Exercise', description: 'Stock option exercise', icon: Zap, color: 'warning', category: 'options' },
    { value: 'transfer_in', label: 'Transfer In', description: 'Asset transfer in', icon: ArrowDownLeft, color: 'success', category: 'transfer' },
    { value: 'transfer_out', label: 'Transfer Out', description: 'Asset transfer out', icon: ArrowUpRight, color: 'danger', category: 'transfer' },
    { value: 'fee', label: 'Fee', description: 'Management fee', icon: Calculator, color: 'gray', category: 'other' },
    { value: 'other', label: 'Other', description: 'Other transaction', icon: Repeat, color: 'gray', category: 'other' }
];

export default transactionTypes;


export const colorSchemes = {
    success: { border: 'border-success-400', bg: 'bg-success-400/10', text: 'text-success-400', hover: 'hover:border-success-300' },
    danger: { border: 'border-danger-400', bg: 'bg-danger-400/10', text: 'text-danger-400', hover: 'hover:border-danger-300' },
    primary: { border: 'border-primary-400', bg: 'bg-primary-400/10', text: 'text-primary-400', hover: 'hover:border-primary-300' },
    warning: { border: 'border-warning-400', bg: 'bg-warning-400/10', text: 'text-warning-400', hover: 'hover:border-warning-300' },
    info: { border: 'border-info-400', bg: 'bg-info-400/10', text: 'text-info-400', hover: 'hover:border-info-300' },
    gray: { border: 'border-gray-400', bg: 'bg-gray-400/10', text: 'text-gray-400', hover: 'hover:border-gray-300' }
};
