import { DollarSign, Edit, Target, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';

const EditPortfolioModal = ({ isOpen, onClose, portfolio, onUpdate }) => {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        initial_cash: '',
        target_return: '',
        risk_tolerance: 'moderate',
        is_public: false
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (portfolio) {
            setFormData({
                name: portfolio.name || '',
                description: portfolio.description || '',
                initial_cash: portfolio.initial_cash || '',
                target_return: portfolio.target_return || '',
                risk_tolerance: portfolio.risk_tolerance || 'moderate',
                is_public: portfolio.is_public || false
            });
        }
    }, [portfolio]);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Validation
        if (!formData.name.trim()) {
            toast.error('Portfolio name is required');
            return;
        }

        if (formData.name.trim().length < 2) {
            toast.error('Portfolio name must be at least 2 characters long');
            return;
        }

        if (formData.initial_cash && parseFloat(formData.initial_cash) < 0) {
            toast.error('Initial cash cannot be negative');
            return;
        }

        if (formData.target_return && (parseFloat(formData.target_return) < 0 || parseFloat(formData.target_return) > 100)) {
            toast.error('Target return must be between 0% and 100%');
            return;
        }

        try {
            setLoading(true);

            const portfolioData = {
                name: formData.name.trim(),
                description: formData.description.trim() || '',
                initial_cash: formData.initial_cash ? parseFloat(formData.initial_cash) : 0,
                target_return: formData.target_return ? parseFloat(formData.target_return) : null,
                risk_tolerance: formData.risk_tolerance || 'moderate',
                is_public: formData.is_public || false
            };

            console.log('[EditPortfolioModal] Submitting portfolio data:', portfolioData);
            await onUpdate(portfolio.id, portfolioData);
        } catch (error) {
            console.error('Error updating portfolio:', error);
            toast.error('Failed to update portfolio. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const riskToleranceOptions = [
        { value: 'conservative', label: 'Conservative', description: 'Low risk, stable returns' },
        { value: 'moderate', label: 'Moderate', description: 'Balanced risk and return' },
        { value: 'aggressive', label: 'Aggressive', description: 'High risk, high potential returns' }
    ];

    if (!isOpen || !portfolio) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-dark-900 rounded-xl border border-dark-700 w-full max-w-2xl max-h-[95vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700 shrink-0">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
                            <Edit size={20} className="text-primary-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-100">Edit Portfolio</h2>
                            <p className="text-sm text-gray-400">Update your portfolio settings</p>
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
                <form onSubmit={handleSubmit} className="p-6 space-y-6 flex-1 overflow-y-auto">
                    {/* Portfolio Name */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Portfolio Name *
                        </label>
                        <input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleInputChange}
                            placeholder="e.g., My Growth Portfolio"
                            className="input-field w-full"
                            required
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Description
                        </label>
                        <textarea
                            name="description"
                            value={formData.description}
                            onChange={handleInputChange}
                            placeholder="Describe your investment strategy and goals..."
                            rows={3}
                            className="input-field w-full resize-none"
                        />
                    </div>

                    {/* Initial Cash */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            <div className="flex items-center space-x-2">
                                <DollarSign size={16} />
                                <span>Initial Cash</span>
                            </div>
                        </label>
                        <input
                            type="number"
                            name="initial_cash"
                            value={formData.initial_cash}
                            onChange={handleInputChange}
                            placeholder="0.00"
                            min="0"
                            step="0.01"
                            className="input-field w-full"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Starting cash balance for this portfolio
                        </p>
                    </div>

                    {/* Target Return */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            <div className="flex items-center space-x-2">
                                <Target size={16} />
                                <span>Target Annual Return (%)</span>
                            </div>
                        </label>
                        <input
                            type="number"
                            name="target_return"
                            value={formData.target_return}
                            onChange={handleInputChange}
                            placeholder="10.0"
                            min="0"
                            max="100"
                            step="0.1"
                            className="input-field w-full"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                            Your target annual return percentage (optional)
                        </p>
                    </div>

                    {/* Risk Tolerance */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                            Risk Tolerance
                        </label>
                        <div className="space-y-3">
                            {riskToleranceOptions.map((option) => (
                                <label key={option.value} className="flex items-start space-x-3 cursor-pointer">
                                    <input
                                        type="radio"
                                        name="risk_tolerance"
                                        value={option.value}
                                        checked={formData.risk_tolerance === option.value}
                                        onChange={handleInputChange}
                                        className="mt-1 text-primary-600 focus:ring-primary-500"
                                    />
                                    <div className="flex-1">
                                        <div className="text-sm font-medium text-gray-100">
                                            {option.label}
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            {option.description}
                                        </div>
                                    </div>
                                </label>
                            ))}
                        </div>
                    </div>

                    {/* Public Portfolio */}
                    <div className="flex items-center space-x-3">
                        <input
                            type="checkbox"
                            name="is_public"
                            checked={formData.is_public}
                            onChange={handleInputChange}
                            className="text-primary-600 focus:ring-primary-500"
                        />
                        <div>
                            <label className="text-sm font-medium text-gray-300 cursor-pointer">
                                Make this portfolio public
                            </label>
                            <p className="text-xs text-gray-500">
                                Allow others to view this portfolio (read-only)
                            </p>
                        </div>
                    </div>
                </form>

                {/* Footer */}
                <div className="flex items-center justify-end space-x-3 p-6 border-t border-dark-700 shrink-0">
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
                        disabled={loading || !formData.name.trim()}
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
                                <span>Update Portfolio</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EditPortfolioModal;
