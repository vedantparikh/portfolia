import {
    Activity,
    BarChart3,
    MoreVertical,
    Plus,
    Trash2
} from 'lucide-react';
import React, { useState } from 'react';
import {
    formatMarketCap,
    formatPercentage,
    formatPrice,
    formatVolume,
    getChangeArrow,
    getChangeColor,
    getChangeIcon
} from '../../utils/formatters.jsx';

const AssetCard = ({ asset, viewMode = 'grid', onClick, onDelete, onAnalytics, onTransaction }) => {
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

    const handleAnalytics = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onAnalytics && onAnalytics();
    };

    const handleTransaction = (e) => {
        e.stopPropagation();
        setShowMenu(false);
        onTransaction && onTransaction();
    };

    if (viewMode === 'list') {
        return (
            <div
                // Use template literal and add conditional z-index
                className={`card p-4 hover:bg-dark-800/50 transition-colors cursor-pointer relative ${showMenu ? 'z-10' : 'z-0'}`} // <-- FIX
                onClick={onClick}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center">
                            <BarChart3 size={24} className="text-primary-400" />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-100 truncate max-w-48">{asset.name}</h3>
                            <p className="text-sm text-gray-400">{asset.symbol}</p>
                            {asset.asset_type && (
                                <p className="text-xs text-primary-400 capitalize">
                                    {asset.asset_type.toLowerCase().replace('_', ' ')}
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center space-x-8">
                        <div className="text-right">
                            <p className="text-lg font-semibold text-gray-100">
                                {formatPrice(asset.detail?.current_price)}
                            </p>
                            <div className="flex items-center space-x-1">
                                {getChangeIcon(asset.detail?.price_change_percentage_24h)}
                                <span className={`text-sm ${getChangeColor(asset.detail?.price_change_percentage_24h)}`}>
                                    {asset.detail?.price_change_percentage_24h ? `${formatPercentage(asset.detail?.price_change_percentage_24h)}` : 'N/A'}
                                </span>
                            </div>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Market Cap</p>
                            <p className="text-sm font-medium text-gray-100">
                                {formatMarketCap(asset.detail?.market_cap)}
                            </p>
                        </div>

                        <div className="text-right">
                            <p className="text-sm text-gray-400">Volume (24h)</p>
                            <p className="text-sm font-medium text-gray-100">
                                {formatVolume(asset.detail?.volume_24h)}
                            </p>
                        </div>

                        <div className="flex items-center space-x-2">
                            {getChangeArrow(asset.detail?.price_change_percentage_24h)}
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
            // Use template literal and add conditional z-index
            className={`card p-6 hover:bg-dark-800/50 transition-all duration-200 cursor-pointer group relative ${showMenu ? 'z-10' : 'z-0'}`} // <-- FIX
            onClick={onClick}
        >
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 bg-primary-600/20 rounded-lg flex items-center justify-center group-hover:bg-primary-600/30 transition-colors">
                        <BarChart3 size={24} className="text-primary-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-gray-100 truncate max-w-32">{asset.name}</h3>
                        <p className="text-sm text-gray-400">{asset.symbol}</p>
                        {asset.asset_type && (
                            <p className="text-xs text-primary-400 capitalize">
                                {asset.asset_type.toLowerCase().replace('_', ' ')}
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center space-x-2">
                    {getChangeArrow(asset.detail?.price_change_percentage_24h)}
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
                    <span className="text-sm text-gray-400">Current Price</span>
                    <div className="text-right">
                        <span className="text-xl font-bold text-gray-100">
                            {formatPrice(asset.detail?.current_price)}
                        </span>
                        {asset.detail?.price_change_percentage_24h && (
                            <div className="flex items-center space-x-1">
                                {getChangeIcon(asset.detail?.price_change_percentage_24h)}
                                <span className={`text-xs ${getChangeColor(asset.detail?.price_change_percentage_24h)}`}>
                                    {formatPercentage(asset.detail?.price_change_percentage_24h)}
                                </span>
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Market Cap</span>
                    <span className="text-sm font-medium text-gray-100">
                        {formatMarketCap(asset.detail?.market_cap)}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Volume (24h)</span>
                    <span className="text-sm font-medium text-gray-100">
                        {formatVolume(asset.detail?.volume_24h)}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">52W High</span>
                    <span className="text-sm font-medium text-gray-100">
                        {formatPrice(asset.detail?.high_52w)}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">52W Low</span>
                    <span className="text-sm font-medium text-gray-100">
                        {formatPrice(asset.detail?.low_52w)}
                    </span>
                </div>

                {/* Technical Analysis Metrics */}
                {(asset.rsi || asset.macd || asset.bollinger_bands || asset.volatility_20d) && (
                    <div className="pt-3 border-t border-dark-700 space-y-2">
                        {asset.rsi && (
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-500">RSI (14)</span>
                                <span className={`text-xs font-medium ${asset.rsi > 70 ? 'text-danger-400' : asset.rsi < 30 ? 'text-success-400' : 'text-gray-300'}`}>
                                    {asset.rsi.toFixed(1)}
                                    {asset.rsi > 70 && <span className="text-xs text-danger-400 ml-1">(Overbought)</span>}
                                    {asset.rsi < 30 && <span className="text-xs text-success-400 ml-1">(Oversold)</span>}
                                </span>
                            </div>
                        )}
                        {asset.macd && (
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-500">MACD</span>
                                <span className={`text-xs font-medium ${asset.macd > 0 ? 'text-success-400' : 'text-danger-400'}`}>
                                    {asset.macd.toFixed(4)}
                                </span>
                            </div>
                        )}
                        {asset.bollinger_bands && (
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-500">BB Position</span>
                                <span className={`text-xs font-medium ${asset.bollinger_bands > 0.8 ? 'text-danger-400' :
                                    asset.bollinger_bands < 0.2 ? 'text-success-400' : 'text-gray-300'
                                    }`}>
                                    {asset.bollinger_bands > 0.8 ? 'Upper Band' :
                                        asset.bollinger_bands < 0.2 ? 'Lower Band' : 'Middle'}
                                </span>
                            </div>
                        )}
                        {asset.volatility_20d && (
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-500">Volatility (20d)</span>
                                <span className={`text-xs font-medium ${asset.volatility_20d > 0.3 ? 'text-warning-400' : 'text-gray-300'}`}>
                                    {(asset.volatility_20d * 100).toFixed(1)}%
                                </span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Price change indicator bar */}
            <div className="mt-4 pt-4 border-t border-dark-700">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>24h Performance</span>
                    <span>{asset.detail?.price_change_percentage_24h ? `${formatPercentage(asset.detail?.price_change_percentage_24h)}` : 'N/A'}</span>
                </div>
                <div className="w-full bg-dark-700 rounded-full h-1.5">
                    <div
                        className={`h-1.5 rounded-full transition-all duration-300 ${asset.detail?.price_change_percentage_24h > 0
                            ? 'bg-success-400'
                            : asset.detail?.price_change_percentage_24h < 0
                                ? 'bg-danger-400'
                                : 'bg-gray-500'
                            }`}
                        style={{
                            width: `${Math.min(Math.abs(asset.detail?.price_change_percentage_24h || 0) * 2, 100)}%`
                        }}
                    />
                </div>
            </div>
        </div>
    );
};

export default AssetCard;