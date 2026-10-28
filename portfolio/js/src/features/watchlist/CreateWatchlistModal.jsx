import { Globe, Lock, Star, X } from 'lucide-react';
import { useState } from 'react';
import { Modal } from '../../shared/ui';

const CreateWatchlistModal = ({ isOpen, onClose, onCreate }) => {
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        is_default: false,
        is_public: false,
        color: '#3B82F6'
    });
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.name.trim()) {
            alert('Please enter a watchlist name');
            return;
        }

        setLoading(true);
        try {
            await onCreate(formData);
            handleClose();
        } catch (error) {
            console.error('Failed to create watchlist:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setFormData({
            name: '',
            description: '',
            is_default: false,
            is_public: false,
            color: '#3B82F6'
        });
        setLoading(false);
        onClose();
    };

    const colorOptions = [
        '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
        '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
    ];

    if (!isOpen) return null;

    return (
        <Modal onClose={handleClose} overlayClassName="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-dark-900 border border-dark-700 rounded-lg w-full max-w-md mx-4">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <h2 className="text-lg font-semibold text-gray-100">Create New Watchlist</h2>
                    <button
                        onClick={handleClose}
                        className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
                    >
                        <X size={20} className="text-gray-400" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Name */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Watchlist Name *
                        </label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                            className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            placeholder="Enter watchlist name"
                            required
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                            Description
                        </label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                            className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-100 placeholder-gray-400 focus:outline-hidden focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                            placeholder="Enter description (optional)"
                            rows={3}
                        />
                    </div>

                    {/* Color */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                            Color
                        </label>
                        <div className="flex items-center space-x-3">
                            <div
                                className="w-8 h-8 rounded-lg border-2 border-dark-600"
                                style={{ backgroundColor: formData.color }}
                            />
                            <div className="flex-1 grid grid-cols-5 gap-2">
                                {colorOptions.map((color) => (
                                    <button
                                        key={color}
                                        type="button"
                                        onClick={() => setFormData(prev => ({ ...prev, color }))}
                                        className={`w-6 h-6 rounded border-2 transition-all ${
                                            formData.color === color 
                                                ? 'border-white scale-110' 
                                                : 'border-dark-600 hover:border-gray-400'
                                        }`}
                                        style={{ backgroundColor: color }}
                                    />
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Settings */}
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                <Star size={16} className="text-yellow-400" />
                                <div>
                                    <label className="text-sm font-medium text-gray-300">
                                        Set as Default
                                    </label>
                                    <p className="text-xs text-gray-400">
                                        Make this your primary watchlist
                                    </p>
                                </div>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.is_default}
                                    onChange={(e) => setFormData(prev => ({ ...prev, is_default: e.target.checked }))}
                                    className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-dark-700 peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-primary-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                            </label>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                {formData.is_public ? (
                                    <Globe size={16} className="text-blue-400" />
                                ) : (
                                    <Lock size={16} className="text-gray-400" />
                                )}
                                <div>
                                    <label className="text-sm font-medium text-gray-300">
                                        Public Watchlist
                                    </label>
                                    <p className="text-xs text-gray-400">
                                        {formData.is_public 
                                            ? 'Others can view this watchlist' 
                                            : 'Only you can view this watchlist'
                                        }
                                    </p>
                                </div>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={formData.is_public}
                                    onChange={(e) => setFormData(prev => ({ ...prev, is_public: e.target.checked }))}
                                    className="sr-only peer"
                                />
                                <div className="w-11 h-6 bg-dark-700 peer-focus:outline-hidden peer-focus:ring-4 peer-focus:ring-primary-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                            </label>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center space-x-3 pt-4">
                        <button
                            type="button"
                            onClick={handleClose}
                            className="flex-1 px-4 py-2 border border-dark-600 text-gray-300 rounded-lg hover:bg-dark-800 transition-colors"
                        >
                            Back
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !formData.name.trim()}
                            className="flex-1 px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-600/50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                        >
                            {loading ? 'Creating...' : 'Create Watchlist'}
                        </button>
                    </div>
                </form>
            </div>
        </Modal>
    );
};

export default CreateWatchlistModal;
