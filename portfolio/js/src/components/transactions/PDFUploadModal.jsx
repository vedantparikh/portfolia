import { AlertCircle, CheckCircle, FileText, Loader2, Upload, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { accountStatementsAPI } from '../../services/api';

const PDFUploadModal = ({ isOpen, onClose, onParsedData }) => {
    const [providers, setProviders] = useState([]);
    const [selectedProvider, setSelectedProvider] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isParsing, setIsParsing] = useState(false);
    const [dragActive, setDragActive] = useState(false);

    useEffect(() => {
        if (isOpen) {
            loadProviders();
        }
    }, [isOpen]);

    const loadProviders = async () => {
        try {
            setIsLoading(true);
            const response = await accountStatementsAPI.getSupportedProviders();
            setProviders(response.providers || []);
        } catch (error) {
            console.error('Failed to load providers:', error);
            toast.error('Failed to load supported providers');
        } finally {
            setIsLoading(false);
        }
    };

    const handleFileSelect = (file) => {
        if (file && file.type === 'application/pdf') {
            setSelectedFile(file);
        } else {
            toast.error('Please select a valid PDF file');
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleFileInputChange = (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
        }
    };

    const handleParse = async () => {
        if (!selectedProvider || !selectedFile) {
            toast.error('Please select a provider and upload a PDF file');
            return;
        }

        try {
            setIsParsing(true);
            const response = await accountStatementsAPI.parseStatement(
                selectedProvider,
                selectedFile,
                selectedFile.name
            );

            onParsedData(response.parsed_data);
            toast.success('PDF parsed successfully!');
        } catch (error) {
            console.error('Failed to parse PDF:', error);
            toast.error('Failed to parse PDF. Please try again.');
        } finally {
            setIsParsing(false);
        }
    };

    const handleClose = () => {
        setSelectedProvider('');
        setSelectedFile(null);
        setIsParsing(false);
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-gray-700">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                            <FileText className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold text-gray-100">Upload Account Statement</h2>
                            <p className="text-sm text-gray-400">Parse your PDF statement to import transactions</p>
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        className="text-gray-400 hover:text-gray-300 transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Provider Selection */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                            Select Account Statement Provider
                        </label>
                        {isLoading ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 animate-spin text-primary-400" />
                                <span className="ml-2 text-gray-400">Loading providers...</span>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {providers.map((provider) => (
                                    <button
                                        key={provider.id}
                                        onClick={() => setSelectedProvider(provider.id)}
                                        className={`p-4 rounded-lg border-2 transition-all ${selectedProvider === provider.id
                                            ? 'border-primary-500 bg-primary-500/10'
                                            : 'border-gray-600 hover:border-gray-500'
                                            }`}
                                    >
                                        <div className="flex items-center space-x-3">
                                            <div className="w-8 h-8 bg-gray-700 rounded-lg flex items-center justify-center">
                                                <FileText className="w-4 h-4 text-gray-300" />
                                            </div>
                                            <div className="text-left">
                                                <div className="font-medium text-gray-100">{provider.name}</div>
                                                <div className="text-xs text-gray-400">{provider.description}</div>
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* File Upload */}
                    <div>
                        <label className="block text-sm font-medium text-gray-300 mb-3">
                            Upload PDF Statement
                        </label>
                        <div
                            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive
                                ? 'border-primary-500 bg-primary-500/10'
                                : selectedFile
                                    ? 'border-success-500 bg-success-500/10'
                                    : 'border-gray-600 hover:border-gray-500'
                                }`}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            {selectedFile ? (
                                <div className="space-y-2">
                                    <CheckCircle className="w-12 h-12 text-success-400 mx-auto" />
                                    <div className="text-gray-100 font-medium">{selectedFile.name}</div>
                                    <div className="text-sm text-gray-400">
                                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                                    </div>
                                    <button
                                        onClick={() => setSelectedFile(null)}
                                        className="text-sm text-gray-400 hover:text-gray-300"
                                    >
                                        Remove file
                                    </button>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                                    <div className="text-gray-100 font-medium">Drop your PDF here</div>
                                    <div className="text-sm text-gray-400">or click to browse</div>
                                    <input
                                        type="file"
                                        accept=".pdf"
                                        onChange={handleFileInputChange}
                                        className="hidden"
                                        id="pdf-upload"
                                    />
                                    <label
                                        htmlFor="pdf-upload"
                                        className="inline-block px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 cursor-pointer transition-colors"
                                    >
                                        Choose File
                                    </label>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Warnings */}
                    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                        <div className="flex items-start space-x-3">
                            <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5" />
                            <div className="text-sm text-yellow-200">
                                <div className="font-medium mb-1">Important Notes:</div>
                                <ul className="space-y-1 text-yellow-300/80">
                                    <li>• Only PDF files are supported</li>
                                    <li>• Make sure your statement is clear and readable</li>
                                    <li>• You'll be able to review and edit parsed data before importing</li>
                                    <li>• Some transactions may need manual verification</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-700">
                    <button
                        onClick={handleClose}
                        className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleParse}
                        disabled={!selectedProvider || !selectedFile || isParsing}
                        className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isParsing ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>Parsing...</span>
                            </>
                        ) : (
                            <>
                                <FileText className="w-4 h-4" />
                                <span>Parse Statement</span>
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PDFUploadModal;
