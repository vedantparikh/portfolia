import { AlertTriangle, Bell, X } from 'lucide-react';
import { useEffect, useState } from 'react';

const asAlertInput = (value) => {
    if (value == null || value === '') return '';
    const n = Number(value);
    return Number.isFinite(n) ? String(n) : '';
};

const EditSymbolModal = ({ isOpen, onClose, symbol, onUpdate }) => {
    const [formData, setFormData] = useState({
        notes: '',
        alert_price_high: '',
        alert_price_low: '',
        alert_price_change_percent: '',
        alerts_enabled: true,
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (symbol) {
            setFormData({
                notes: symbol.notes || '',
                alert_price_high: asAlertInput(symbol.alert_price_high),
                alert_price_low: asAlertInput(symbol.alert_price_low),
                alert_price_change_percent: asAlertInput(symbol.alert_price_change_percent),
                alerts_enabled: symbol.alerts_enabled ?? true,
            });
        }
    }, [symbol]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        setLoading(true);
        try {
            const updateData = {};
            if (formData.notes !== (symbol?.notes || '')) updateData.notes = formData.notes;
            for (const field of ['alert_price_high', 'alert_price_low', 'alert_price_change_percent']) {
                const value = asAlertInput(formData[field]);
                if (value !== asAlertInput(symbol?.[field])) {
                    updateData[field] = value === '' ? null : value;
                }
            }
            if (formData.alerts_enabled !== (symbol?.alerts_enabled ?? true)) {
                updateData.alerts_enabled = formData.alerts_enabled;
            }
            
            await onUpdate(symbol.id, updateData);
            handleClose();
        } catch (error) {
            console.error('Failed to update symbol:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setLoading(false);
        onClose();
    };

    const validatePrice = (value) => {
        if (!value) return true;
        const num = parseFloat(value);
        return !isNaN(num) && num >= 0;
    };

    if (!isOpen || !symbol) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-dark-900 border border-dark-700 rounded-lg w-full max-w-md mx-4">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <h2 className="text-lg font-semibold text-gray-100">Edit {symbol.symbol}</h2>
                    <button
                        onClick={handleClose}
                        className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
                    >
                        <X size={20} className="text-gray-400" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Symbol Info */}
                    <div className="bg-dark-800/50 border border-dark-600 rounded-lg p-4">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                                <span className="text-primary-400 font-mono font-bold text-lg">
                                    {symbol.symbol}
                                </span>
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-gray-100">
                                    {symbol.symbol}
                                </h3>
                                <p className="text-xs text-gray-400">
                                    {symbol.company_name || 'Unknown Company'}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Notes */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Notes
                        </label>
                        <textarea
                            value={formData.notes}
                            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                            className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                            placeholder="Add notes about this symbol..."
                            rows={3}
                        />
                    </div>

                    {/* Price Alerts */}
                    <div className="space-y-4">
                        <div className="flex items-center space-x-2">
                            <Bell size={16} className="text-yellow-400" />
                            <h3 className="text-sm font-medium text-gray-300">Price Alerts</h3>
                        </div>

                        <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={formData.alerts_enabled}
                                onChange={(e) => setFormData(prev => ({ ...prev, alerts_enabled: e.target.checked }))}
                            />
                            Alerts on
                        </label>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    High price
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    value={formData.alert_price_high}
                                    onChange={(e) => setFormData(prev => ({ ...prev, alert_price_high: e.target.value }))}
                                    className="input-field w-full"
                                    placeholder="Off"
                                />
                                <p className="text-xs text-gray-400 mt-1">At or above this price</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Low price
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    value={formData.alert_price_low}
                                    onChange={(e) => setFormData(prev => ({ ...prev, alert_price_low: e.target.value }))}
                                    className="input-field w-full"
                                    placeholder="Off"
                                />
                                <p className="text-xs text-gray-400 mt-1">At or below this price</p>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Move since added (%)
                                </label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    value={formData.alert_price_change_percent}
                                    onChange={(e) => setFormData(prev => ({ ...prev, alert_price_change_percent: e.target.value }))}
                                    className="input-field w-full"
                                    placeholder="Off"
                                />
                                <p className="text-xs text-gray-400 mt-1">Up or down by this much</p>
                            </div>
                        </div>

                        {/* Alert Info */}
                        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
                            <div className="flex items-start space-x-2">
                                <AlertTriangle size={14} className="text-yellow-400 mt-0.5" />
                                <div className="text-xs text-yellow-300">
                                    <p className="font-medium mb-1">Price Alerts:</p>
                                    <ul className="space-y-1">
                                        <li>• Checked in the background about every 15 minutes</li>
                                        <li>• Shown in the app: the Watchlist alerts panel and the dashboard</li>
                                        <li>• Each alert fires once, and again only after the price has moved back</li>
                                        <li>• Leave a field empty to switch that alert off</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="flex-1 px-4 py-2 border border-dark-600 text-gray-300 rounded-lg hover:bg-dark-800 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || 
                                (!validatePrice(formData.alert_price_high) || 
                                 !validatePrice(formData.alert_price_low))
                            }
                            className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-600/50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                        >
                            {loading ? 'Updating...' : 'Update Symbol'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default EditSymbolModal;
