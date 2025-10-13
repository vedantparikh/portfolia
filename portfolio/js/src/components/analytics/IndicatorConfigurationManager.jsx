import {
    Activity,
    CheckCircle,
    Copy,
    Edit3,
    Plus,
    Search,
    Trash2,
    X
} from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { toast } from 'react-hot-toast';
import { statisticalIndicatorsAPI } from '../../services/api';
import LoadingSpinner from '../shared/LoadingSpinner';

const IndicatorConfigurationManager = ({
    onConfigurationSelect,
    selectedConfigurationId,
    showCreateButton = true,
    showSearch = true,
    showFilters = true,
    className = ''
}) => {
    const [configurations, setConfigurations] = useState([]);
    const [availableIndicators, setAvailableIndicators] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [editingConfig, setEditingConfig] = useState(null);
    const [newConfig, setNewConfig] = useState({
        name: '',
        description: '',
        indicators: [],
        chart_settings: {},
        is_public: false,
        tags: []
    });

    // Load configurations and available indicators
    useEffect(() => {
        loadConfigurations();
        loadAvailableIndicators();
    }, []);

    const loadConfigurations = async () => {
        try {
            setLoading(true);
            const response = await statisticalIndicatorsAPI.getConfigurations(0, 100, true);
            setConfigurations(response.configurations || []);
        } catch (error) {
            console.error('Failed to load configurations:', error);
            toast.error('Failed to load configurations');
        } finally {
            setLoading(false);
        }
    };

    const loadAvailableIndicators = async () => {
        try {
            const response = await statisticalIndicatorsAPI.getAvailableIndicators();
            setAvailableIndicators(response.indicators || []);
        } catch (error) {
            console.error('Failed to load indicators:', error);
        }
    };

    const handleCreateConfiguration = async () => {
        try {
            if (!newConfig.name.trim()) {
                toast.error('Configuration name is required');
                return;
            }

            if (newConfig.indicators.length === 0) {
                toast.error('Please select at least one indicator');
                return;
            }

            const response = await statisticalIndicatorsAPI.createConfiguration(newConfig);
            setConfigurations(prev => [response, ...prev]);
            setShowCreateModal(false);
            setNewConfig({
                name: '',
                description: '',
                indicators: [],
                chart_settings: {},
                is_public: false,
                tags: []
            });
            toast.success('Configuration created successfully');
        } catch (error) {
            console.error('Failed to create configuration:', error);
            toast.error('Failed to create configuration');
        }
    };

    const handleUpdateConfiguration = async () => {
        try {
            if (!editingConfig.name.trim()) {
                toast.error('Configuration name is required');
                return;
            }

            if (editingConfig.indicators.length === 0) {
                toast.error('Please select at least one indicator');
                return;
            }

            const response = await statisticalIndicatorsAPI.updateConfiguration(editingConfig.id, editingConfig);
            setConfigurations(prev => prev.map(config =>
                config.id === editingConfig.id ? response : config
            ));
            setShowEditModal(false);
            setEditingConfig(null);
            toast.success('Configuration updated successfully');
        } catch (error) {
            console.error('Failed to update configuration:', error);
            toast.error('Failed to update configuration');
        }
    };

    const handleDeleteConfiguration = async (configId) => {
        if (!window.confirm('Are you sure you want to delete this configuration?')) {
            return;
        }

        try {
            await statisticalIndicatorsAPI.deleteConfiguration(configId);
            setConfigurations(prev => prev.filter(config => config.id !== configId));
            toast.success('Configuration deleted successfully');
        } catch (error) {
            console.error('Failed to delete configuration:', error);
            toast.error('Failed to delete configuration');
        }
    };

    const handleDuplicateConfiguration = async (config) => {
        try {
            const newName = `${config.name} (Copy)`;
            const response = await statisticalIndicatorsAPI.duplicateConfiguration(config.id, newName);
            setConfigurations(prev => [response, ...prev]);
            toast.success('Configuration duplicated successfully');
        } catch (error) {
            console.error('Failed to duplicate configuration:', error);
            toast.error('Failed to duplicate configuration');
        }
    };

    const handleEditConfiguration = (config) => {
        setEditingConfig({ ...config });
        setShowEditModal(true);
    };

    const addIndicatorToConfig = (config, indicator) => {
        const indicatorConfig = {
            id: `${indicator.name}_${Date.now()}`,
            indicator_name: indicator.name,
            parameters: {},
            enabled: true,
            display_name: indicator.name,
            color: getDefaultColor(config.indicators.length),
            line_style: 'solid',
            line_width: 1,
            y_axis: 'secondary',
            show_in_legend: true
        };

        // Set default parameters based on indicator definition
        if (indicator.parameters) {
            indicator.parameters.forEach(param => {
                if (param.default_value !== undefined) {
                    indicatorConfig.parameters[param.name] = param.default_value;
                }
            });
        }

        return {
            ...config,
            indicators: [...config.indicators, indicatorConfig]
        };
    };

    const removeIndicatorFromConfig = (config, indicatorId) => {
        return {
            ...config,
            indicators: config.indicators.filter(ind => ind.id !== indicatorId)
        };
    };

    const updateIndicatorConfig = (config, indicatorId, updates) => {
        return {
            ...config,
            indicators: config.indicators.map(ind =>
                ind.id === indicatorId ? { ...ind, ...updates } : ind
            )
        };
    };

    const getDefaultColor = (index) => {
        const colors = [
            '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ];
        return colors[index % colors.length];
    };

    const filteredConfigurations = configurations.filter(config => {
        const matchesSearch = !searchQuery ||
            config.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            config.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            config.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));

        const matchesCategory = !selectedCategory ||
            config.indicators?.some(ind =>
                availableIndicators.find(avail => avail.name === ind.indicator_name)?.category === selectedCategory
            );

        return matchesSearch && matchesCategory;
    });

    const categories = [...new Set(availableIndicators.map(ind => ind.category))];

    return (
        <div className={`space-y-4 ${className}`}>
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                    <Activity className="w-5 h-5 text-primary-400" />
                    <h3 className="text-lg font-semibold text-gray-100">Analysis Configurations</h3>
                </div>
                {showCreateButton && (
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="btn-primary flex items-center space-x-2"
                    >
                        <Plus size={16} />
                        <span>New Configuration</span>
                    </button>
                )}
            </div>

            {/* Search and Filters */}
            {(showSearch || showFilters) && (
                <div className="flex flex-col sm:flex-row gap-4">
                    {showSearch && (
                        <div className="flex-1">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                                <input
                                    type="text"
                                    placeholder="Search configurations..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="input pl-10"
                                />
                            </div>
                        </div>
                    )}
                    {showFilters && (
                        <div className="sm:w-48">
                            <select
                                value={selectedCategory}
                                onChange={(e) => setSelectedCategory(e.target.value)}
                                className="input"
                            >
                                <option value="">All Categories</option>
                                {categories.map(category => (
                                    <option key={category} value={category}>
                                        {category.charAt(0).toUpperCase() + category.slice(1)}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                </div>
            )}

            {/* Configurations List */}
            <div className="space-y-3">
                {loading ? (
                    <div className="flex items-center justify-center py-8">
                        <LoadingSpinner type="analyst" size="md" />
                    </div>
                ) : filteredConfigurations.length === 0 ? (
                    <div className="text-center py-8 text-gray-400">
                        <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                        <p>No configurations found</p>
                        {showCreateButton && (
                            <button
                                onClick={() => setShowCreateModal(true)}
                                className="btn-outline mt-4"
                            >
                                Create your first configuration
                            </button>
                        )}
                    </div>
                ) : (
                    filteredConfigurations.map(config => (
                        <div
                            key={config.id}
                            className={`card p-4 cursor-pointer transition-all duration-200 hover:bg-dark-700 ${selectedConfigurationId === config.id ? 'ring-2 ring-primary-400 bg-dark-700' : ''
                                }`}
                            onClick={() => onConfigurationSelect && onConfigurationSelect(config)}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center space-x-2 mb-2">
                                        <h4 className="font-semibold text-gray-100">{config.name}</h4>
                                        {config.is_public && (
                                            <span className="px-2 py-1 text-xs bg-green-900 text-green-300 rounded">
                                                Public
                                            </span>
                                        )}
                                        {selectedConfigurationId === config.id && (
                                            <CheckCircle className="w-4 h-4 text-primary-400" />
                                        )}
                                    </div>
                                    {config.description && (
                                        <p className="text-sm text-gray-400 mb-3">{config.description}</p>
                                    )}
                                    <div className="flex flex-wrap gap-2 mb-3">
                                        {config.indicators?.slice(0, 5).map(indicator => (
                                            <span
                                                key={indicator.id}
                                                className="px-2 py-1 text-xs bg-dark-600 text-gray-300 rounded"
                                            >
                                                {indicator.display_name || indicator.indicator_name}
                                            </span>
                                        ))}
                                        {config.indicators?.length > 5 && (
                                            <span className="px-2 py-1 text-xs bg-dark-600 text-gray-400 rounded">
                                                +{config.indicators.length - 5} more
                                            </span>
                                        )}
                                    </div>
                                    {config.tags && config.tags.length > 0 && (
                                        <div className="flex flex-wrap gap-1">
                                            {config.tags.map(tag => (
                                                <span
                                                    key={tag}
                                                    className="px-2 py-1 text-xs bg-primary-900 text-primary-300 rounded"
                                                >
                                                    #{tag}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div className="flex items-center space-x-2 ml-4">
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleEditConfiguration(config);
                                        }}
                                        className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-600 rounded transition-colors"
                                        title="Edit configuration"
                                    >
                                        <Edit3 size={16} />
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDuplicateConfiguration(config);
                                        }}
                                        className="p-2 text-gray-400 hover:text-gray-100 hover:bg-dark-600 rounded transition-colors"
                                        title="Duplicate configuration"
                                    >
                                        <Copy size={16} />
                                    </button>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteConfiguration(config.id);
                                        }}
                                        className="p-2 text-gray-400 hover:text-red-400 hover:bg-dark-600 rounded transition-colors"
                                        title="Delete configuration"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Create Configuration Modal */}
            {showCreateModal && (
                <ConfigurationModal
                    config={newConfig}
                    setConfig={setNewConfig}
                    availableIndicators={availableIndicators}
                    onSave={handleCreateConfiguration}
                    onClose={() => setShowCreateModal(false)}
                    title="Create New Configuration"
                />
            )}

            {/* Edit Configuration Modal */}
            {showEditModal && editingConfig && (
                <ConfigurationModal
                    config={editingConfig}
                    setConfig={setEditingConfig}
                    availableIndicators={availableIndicators}
                    onSave={handleUpdateConfiguration}
                    onClose={() => {
                        setShowEditModal(false);
                        setEditingConfig(null);
                    }}
                    title="Edit Configuration"
                />
            )}
        </div>
    );
};

// Configuration Modal Component
const ConfigurationModal = ({
    config,
    setConfig,
    availableIndicators,
    onSave,
    onClose,
    title
}) => {
    const [selectedIndicator, setSelectedIndicator] = useState('');

    const addIndicator = () => {
        if (!selectedIndicator) return;

        const indicator = availableIndicators.find(ind => ind.name === selectedIndicator);
        if (!indicator) return;

        const indicatorConfig = {
            id: `${indicator.name}_${Date.now()}`,
            indicator_name: indicator.name,
            parameters: {},
            enabled: true,
            display_name: indicator.name,
            color: getDefaultColor(config.indicators.length),
            line_style: 'solid',
            line_width: 1,
            y_axis: 'secondary',
            show_in_legend: true
        };

        // Set default parameters
        if (indicator.parameters) {
            indicator.parameters.forEach(param => {
                if (param.default_value !== undefined) {
                    indicatorConfig.parameters[param.name] = param.default_value;
                }
            });
        }

        setConfig({
            ...config,
            indicators: [...config.indicators, indicatorConfig]
        });
        setSelectedIndicator('');
    };

    const removeIndicator = (indicatorId) => {
        setConfig({
            ...config,
            indicators: config.indicators.filter(ind => ind.id !== indicatorId)
        });
    };

    const updateIndicator = (indicatorId, updates) => {
        setConfig({
            ...config,
            indicators: config.indicators.map(ind =>
                ind.id === indicatorId ? { ...ind, ...updates } : ind
            )
        });
    };

    const getDefaultColor = (index) => {
        const colors = [
            '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
            '#06B6D4', '#84CC16', '#F97316', '#EC4899', '#6366F1'
        ];
        return colors[index % colors.length];
    };

    const categories = [...new Set(availableIndicators.map(ind => ind.category))];

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-dark-800 rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden">
                <div className="flex items-center justify-between p-6 border-b border-dark-700">
                    <h3 className="text-xl font-semibold text-gray-100">{title}</h3>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-100"
                    >
                        <X size={24} />
                    </button>
                </div>

                <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                    <div className="space-y-6">
                        {/* Basic Information */}
                        <div className="space-y-4">
                            <h4 className="text-lg font-medium text-gray-100">Basic Information</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Name *
                                    </label>
                                    <input
                                        type="text"
                                        value={config.name}
                                        onChange={(e) => setConfig({ ...config, name: e.target.value })}
                                        className="input"
                                        placeholder="Configuration name"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        Public
                                    </label>
                                    <label className="flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={config.is_public}
                                            onChange={(e) => setConfig({ ...config, is_public: e.target.checked })}
                                            className="mr-2"
                                        />
                                        <span className="text-sm text-gray-300">Make this configuration public</span>
                                    </label>
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Description
                                </label>
                                <textarea
                                    value={config.description}
                                    onChange={(e) => setConfig({ ...config, description: e.target.value })}
                                    className="input"
                                    rows={3}
                                    placeholder="Configuration description"
                                />
                            </div>
                        </div>

                        {/* Add Indicators */}
                        <div className="space-y-4">
                            <h4 className="text-lg font-medium text-gray-100">Indicators</h4>
                            <div className="flex gap-2">
                                <select
                                    value={selectedIndicator}
                                    onChange={(e) => setSelectedIndicator(e.target.value)}
                                    className="input flex-1"
                                >
                                    <option value="">Select an indicator...</option>
                                    {categories.map(category => (
                                        <optgroup key={category} label={category.charAt(0).toUpperCase() + category.slice(1)}>
                                            {availableIndicators
                                                .filter(ind => ind.category === category)
                                                .map(indicator => (
                                                    <option key={indicator.name} value={indicator.name}>
                                                        {indicator.name} - {indicator.description}
                                                    </option>
                                                ))}
                                        </optgroup>
                                    ))}
                                </select>
                                <button
                                    onClick={addIndicator}
                                    disabled={!selectedIndicator}
                                    className="btn-primary"
                                >
                                    Add
                                </button>
                            </div>
                        </div>

                        {/* Configured Indicators */}
                        {config.indicators.length > 0 && (
                            <div className="space-y-3">
                                <h5 className="text-md font-medium text-gray-100">Configured Indicators</h5>
                                {config.indicators.map(indicator => (
                                    <IndicatorConfigCard
                                        key={indicator.id}
                                        indicator={indicator}
                                        availableIndicators={availableIndicators}
                                        onUpdate={(updates) => updateIndicator(indicator.id, updates)}
                                        onRemove={() => removeIndicator(indicator.id)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="flex items-center justify-end space-x-3 p-6 border-t border-dark-700">
                    <button
                        onClick={onClose}
                        className="btn-outline"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onSave}
                        className="btn-primary"
                    >
                        Save Configuration
                    </button>
                </div>
            </div>
        </div>
    );
};

// Indicator Configuration Card Component
const IndicatorConfigCard = ({
    indicator,
    availableIndicators,
    onUpdate,
    onRemove
}) => {
    const indicatorDef = availableIndicators.find(ind => ind.name === indicator.indicator_name);

    return (
        <div className="card p-4">
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-2">
                    <div
                        className="w-4 h-4 rounded"
                        style={{ backgroundColor: indicator.color }}
                    />
                    <h6 className="font-medium text-gray-100">
                        {indicator.display_name || indicator.indicator_name}
                    </h6>
                </div>
                <button
                    onClick={onRemove}
                    className="text-gray-400 hover:text-red-400"
                >
                    <X size={16} />
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                        Display Name
                    </label>
                    <input
                        type="text"
                        value={indicator.display_name}
                        onChange={(e) => onUpdate({ display_name: e.target.value })}
                        className="input text-sm"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                        Color
                    </label>
                    <input
                        type="color"
                        value={indicator.color}
                        onChange={(e) => onUpdate({ color: e.target.value })}
                        className="input text-sm h-8"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                        Y-Axis
                    </label>
                    <select
                        value={indicator.y_axis}
                        onChange={(e) => onUpdate({ y_axis: e.target.value })}
                        className="input text-sm"
                    >
                        <option value="primary">Primary</option>
                        <option value="secondary">Secondary</option>
                    </select>
                </div>
            </div>

            {/* Parameters */}
            {indicatorDef?.parameters && indicatorDef.parameters.length > 0 && (
                <div className="mt-4">
                    <h6 className="text-sm font-medium text-gray-300 mb-2">Parameters</h6>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {indicatorDef.parameters.map(param => (
                            <div key={param.name}>
                                <label className="block text-xs font-medium text-gray-400 mb-1">
                                    {param.name}
                                </label>
                                <input
                                    type={param.type === 'integer' ? 'number' : param.type === 'float' ? 'number' : 'text'}
                                    value={indicator.parameters[param.name] || ''}
                                    onChange={(e) => onUpdate({
                                        parameters: {
                                            ...indicator.parameters,
                                            [param.name]: param.type === 'boolean' ? e.target.checked : e.target.value
                                        }
                                    })}
                                    className="input text-sm"
                                    placeholder={param.description}
                                />
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default IndicatorConfigurationManager;
