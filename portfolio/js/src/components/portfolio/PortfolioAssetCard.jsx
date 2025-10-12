import React, { useState } from 'react';
import {
    Activity,
    MoreVertical,
    Plus,
    Trash2
} from 'lucide-react';

const AllocationDonut = ({ percentage = 0 }) => {
    const sqSize = 48; // Corresponds to w-12 h-12
    const strokeWidth = 5;
    const radius = (sqSize - strokeWidth) / 2;
    const viewBox = `0 0 ${sqSize} ${sqSize}`;
    const circumference = radius * 2 * Math.PI;
    const dashOffset = circumference - (percentage / 100) * circumference;

    return (
        <div className="relative w-12 h-12">
            <svg width={sqSize} height={sqSize} viewBox={viewBox}>
                <circle
                    className="text-dark-700"
                    cx={sqSize / 2}
                    cy={sqSize / 2}
                    r={radius}
                    strokeWidth={`${strokeWidth}px`}
                    fill="none"
                    stroke="currentColor"
                />
                <circle
                    className="text-primary-400"
                    cx={sqSize / 2}
                    cy={sqSize / 2}
                    r={radius}
                    strokeWidth={`${strokeWidth}px`}
                    fill="none"
                    stroke="currentColor"
                    strokeDasharray={circumference}
                    strokeDashoffset={dashOffset}
                    strokeLinecap="round"
                    transform={`rotate(-90 ${sqSize / 2} ${sqSize / 2})`}
                />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-semibold text-gray-300">
                    {`${percentage.toFixed(0)}%`}
                </span>
            </div>
        </div>
    );
};

// Custom portfolio asset display component
const PortfolioAssetCard = ({ asset, portfolioTotalValue = 0, viewMode = 'grid', onClick, onTransaction, onAnalytics, onDelete }) => {
    const [showMenu, setShowMenu] = useState(false);

    const handleMenuClick = (e) => {
        e.stopPropagation();
        setShowMenu(!showMenu);
    };

    const handleDelete = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onDelete && onDelete();
    };

    const handleTransaction = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onTransaction && onTransaction();
    };

    const handleAnalytics = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onAnalytics && onAnalytics();
    };

    const allocation = portfolioTotalValue > 0 && asset.total_value ? (asset.total_value / portfolioTotalValue) * 100 : 0;

    if (viewMode === 'list') {
        return (
            <div
                className={`card p-4 hover:bg-dark-800/50 transition-colors cursor-pointer relative ${showMenu ? 'z-10' : 'z-0'}`}
                onClick={onClick}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <AllocationDonut percentage={allocation} />
                        <div>
                            <h3 className="text-lg font-semibold text-gray-100">{asset.symbol}</h3>
                            <p className="text-sm text-gray-400 truncate max-w-48">{asset.name}</p>
                            {asset.asset_type && (
                                <p className="text-xs text-primary-400 capitalize">
                                    {asset.asset_type.toLowerCase().replace('_', ' ')}
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center space-x-8">
                        <div className="text-right">
                            <p className="text-sm text-gray-400">Quantity</p>
                            <p className="text-lg font-semibold text-gray-100">
                                {asset.quantity?.toFixed(4) || '0'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Purchase Price</p>
                            <p className="text-sm font-medium text-gray-100">
                                ${asset.purchase_price?.toFixed(2) || '0.00'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Current Price</p>
                            <p className="text-sm font-medium text-gray-100">
                                ${asset.current_price?.toFixed(2) || '0.00'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Total Value</p>
                            <p className="text-lg font-semibold text-gray-100">
                                ${asset.total_value?.toFixed(2) || '0.00'}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">P&L</p>
                            <p className={`text-sm font-medium ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.pnl?.toFixed(2) || '0.00'}
                            </p>
                            <p className={`text-xs ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {asset.pnl_percentage?.toFixed(2) || '0.00'}%
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-gray-400">Realized P&L</p>
                            <p className={`text-sm font-medium ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.realized_pnl?.toFixed(2) || '0.00'}
                            </p>
                            <p className={`text-xs ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {asset.realized_pnl_percentage?.toFixed(2) || '0.00'}%
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="text-sm text-gray-400">Today's P&L</p>
                            <p className={`text-sm font-medium ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.today_pnl?.toFixed(2) || '0.00'}
                            </p>
                            <p className={`text-xs ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                {asset.today_pnl_percentage?.toFixed(2) || '0.00'}%
                            </p>
                        </div>

                        <div className="flex items-center space-x-2">
                            <div className="relative">
                                <button
                                    onClick={handleMenuClick}
                                    className="p-1 rounded-lg hover:bg-dark-700 transition-colors"
                                >
                                    <MoreVertical size={16} className="text-gray-400" />
                                </button>
                                {showMenu && (
                                    <div className="absolute right-0 top-8 bg-dark-800 border border-dark-700 rounded-lg shadow-lg z-10 min-w-40">
                                        <button
                                            onClick={handleTransaction}
                                            className="w-full px-3 py-2 text-left text-sm text-success-400 hover:bg-dark-700 flex items-center space-x-2"
                                        >
                                            <Plus size={14} />
                                            <span>Add Transaction</span>
                                        </button>
                                        <button
                                            onClick={handleAnalytics}
                                            className="w-full px-3 py-2 text-left text-sm text-primary-400 hover:bg-dark-700 flex items-center space-x-2"
                                        >
                                            <Activity size={14} />
                                            <span>Analytics</span>
                                        </button>
                                        <button
                                            onClick={handleDelete}
                                            className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-700 flex items-center space-x-2"
                                        >
                                            <Trash2 size={14} />
                                            <span>Delete</span>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div
            className={`card p-6 hover:bg-dark-800/50 transition-all duration-200 cursor-pointer group relative ${showMenu ? 'z-10' : 'z-0'}`}
            onClick={onClick}
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                    <AllocationDonut percentage={allocation} />
                    <div>
                        <h3 className="text-lg font-semibold text-gray-100">{asset.symbol}</h3>
                        <p className="text-sm text-gray-400 truncate max-w-32">{asset.name}</p>
                        {asset.asset_type && (
                            <p className="text-xs text-primary-400 capitalize">
                                {asset.asset_type.toLowerCase().replace('_', ' ')}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center space-x-2">
                    <div className="relative">
                        <button
                            onClick={handleMenuClick}
                            className="p-1 rounded-lg hover:bg-dark-700 transition-colors opacity-0 group-hover:opacity-100"
                        >
                            <MoreVertical size={16} className="text-gray-400" />
                        </button>
                        {showMenu && (
                            <div className="absolute right-0 top-8 bg-dark-800 border border-dark-700 rounded-lg shadow-lg z-10 min-w-40">
                                <button
                                    onClick={handleTransaction}
                                    className="w-full px-3 py-2 text-left text-sm text-success-400 hover:bg-dark-700 flex items-center space-x-2"
                                >
                                    <Plus size={14} />
                                    <span>Add Transaction</span>
                                </button>
                                <button
                                    onClick={handleAnalytics}
                                    className="w-full px-3 py-2 text-left text-sm text-primary-400 hover:bg-dark-700 flex items-center space-x-2"
                                >
                                    <Activity size={14} />
                                    <span>Analytics</span>
                                </button>
                                <button
                                    onClick={handleDelete}
                                    className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-dark-700 flex items-center space-x-2"
                                >
                                    <Trash2 size={14} />
                                    <span>Delete</span>
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Quantity</span>
                    <span className="text-lg font-bold text-gray-100">
                        {asset.quantity?.toFixed(4) || '0'}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Purchase Price</span>
                    <span className="text-sm font-medium text-gray-100">
                        ${asset.purchase_price?.toFixed(2) || '0.00'}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Current Price</span>
                    <span className="text-sm font-medium text-gray-100">
                        ${asset.current_price?.toFixed(2) || '0.00'}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Total Value</span>
                    <span className="text-lg font-bold text-gray-100">
                        ${asset.total_value?.toFixed(2) || '0.00'}
                    </span>
                </div>

                {/* P&L Section */}
                <div className="pt-3 border-t border-dark-700 space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">Unrealized P&L</span>
                        <div className="text-right">
                            <span className={`text-sm font-bold ${(asset.pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ${asset.pnl?.toFixed(2) || '0.00'}
                            </span>
                            <span className={`text-xs ml-2 ${(asset.pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                ({asset.pnl_percentage?.toFixed(2) || '0.00'}%)
                            </span>
                        </div>
                    </div>

                    {asset.realized_pnl !== undefined && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Realized P&L</span>
                            <div className="text-right">
                                <span className={`text-sm font-medium ${(asset.realized_pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ${asset.realized_pnl?.toFixed(2) || '0.00'}
                                </span>
                                <span className={`text-xs ml-2 ${(asset.realized_pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ({asset.realized_pnl_percentage?.toFixed(2) || '0.00'}%)
                                </span>
                            </div>
                        </div>
                    )}
                    {asset.today_pnl !== undefined && (
                        <div className="flex items-center justify-between">
                            <span className="text-sm text-gray-400">Today's P&L</span>
                            <div className="text-right">
                                <span className={`text-sm font-medium ${(asset.today_pnl || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ${asset.today_pnl?.toFixed(2) || '0.00'}
                                </span>
                                <span className={`text-xs ml-2 ${(asset.today_pnl_percentage || 0) >= 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    ({asset.today_pnl_percentage?.toFixed(2) || '0.00'}%)
                                </span>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* P&L indicator bar */}
            <div className="mt-4 pt-4 border-t border-dark-700">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Position Performance</span>
                    <span>{asset.pnl_percentage ? `${asset.pnl_percentage.toFixed(2)}%` : '0.00%'}</span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full transition-all duration-300 ${(asset.pnl_percentage || 0) > 0
                            ? 'bg-success-400'
                            : (asset.pnl_percentage || 0) < 0
                                ? 'bg-danger-400'
                                : 'bg-gray-500'
                            }`}
                        style={{
                            width: `${Math.min(Math.abs(asset.pnl_percentage || 0) * 2, 100)}%`
                        }}
                    />
                </div>
            </div>
        </div>
    );
};

export default PortfolioAssetCard;