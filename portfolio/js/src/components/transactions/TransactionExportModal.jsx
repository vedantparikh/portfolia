import { Download, Eye, X } from "lucide-react";
import PropTypes from "prop-types";
import { useState } from "react";
import toast from "react-hot-toast";
import { transactionPDFExportAPI } from "../../services/api";

const TransactionExportModal = ({ isOpen, onClose, portfolios = [] }) => {
  const [selectedPortfolios, setSelectedPortfolios] = useState([]);
  const [dateRange, setDateRange] = useState({
    startDate: "",
    endDate: "",
  });
  const [transactionTypes, setTransactionTypes] = useState([]);
  const [assetSymbols, setAssetSymbols] = useState([]);
  const [amountRange, setAmountRange] = useState({
    minAmount: "",
    maxAmount: "",
  });
  const [exportOptions, setExportOptions] = useState({
    include_summary: true,
    include_charts: false,
    include_portfolio_details: true,
    include_asset_details: true,
    group_by_portfolio: false,
    group_by_asset: false,
    sort_by: "transaction_date",
    sort_order: "desc",
  });
  const [customFilename, setCustomFilename] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  const transactionTypeOptions = [
    { value: "buy", label: "Buy" },
    { value: "sell", label: "Sell" },
    { value: "dividend", label: "Dividend" },
    { value: "split", label: "Stock Split" },
    { value: "merger", label: "Merger" },
    { value: "spin_off", label: "Spin-off" },
    { value: "rights_issue", label: "Rights Issue" },
    { value: "stock_option_exercise", label: "Option Exercise" },
    { value: "transfer_in", label: "Transfer In" },
    { value: "transfer_out", label: "Transfer Out" },
    { value: "fee", label: "Fee" },
    { value: "other", label: "Other" },
  ];

  const sortByOptions = [
    { value: "transaction_date", label: "Transaction Date" },
    { value: "amount", label: "Amount" },
    { value: "symbol", label: "Symbol" },
    { value: "type", label: "Type" },
  ];

  // Build filters object for API
  const buildFilters = () => {
    const filters = {};

    if (selectedPortfolios.length > 0) {
      filters.portfolio_ids = selectedPortfolios.map((id) => parseInt(id));
    }

    if (dateRange.startDate) {
      filters.start_date = new Date(dateRange.startDate).toISOString();
    }

    if (dateRange.endDate) {
      filters.end_date = new Date(dateRange.endDate).toISOString();
    }

    if (transactionTypes.length > 0) {
      filters.transaction_types = transactionTypes;
    }

    if (assetSymbols.length > 0) {
      filters.asset_symbols = assetSymbols;
    }

    if (amountRange.minAmount) {
      filters.min_amount = parseFloat(amountRange.minAmount);
    }

    if (amountRange.maxAmount) {
      filters.max_amount = parseFloat(amountRange.maxAmount);
    }

    return filters;
  };

  // Preview export
  const handlePreview = async () => {
    const filters = buildFilters();

    if (Object.keys(filters).length === 0) {
      toast.error("Please select at least one filter criteria");
      return;
    }

    setIsPreviewing(true);
    try {
      const preview = await transactionPDFExportAPI.previewExport(
        filters,
        exportOptions
      );
      setPreviewData(preview);
      toast.success(
        `Preview ready: ${preview.transaction_count} transactions will be exported`
      );
    } catch (error) {
      console.error("Preview failed:", error);
      toast.error("Failed to preview export");
    } finally {
      setIsPreviewing(false);
    }
  };

  // Export PDF
  const handleExport = async () => {
    const filters = buildFilters();

    if (Object.keys(filters).length === 0) {
      toast.error("Please select at least one filter criteria");
      return;
    }

    setIsExporting(true);
    try {
      const response = await transactionPDFExportAPI.downloadPDF(
        filters,
        exportOptions,
        customFilename
      );

      // Create download link
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;

      // Get filename from response headers or use default
      const contentDisposition = response.headers["content-disposition"];
      let filename = "transactions_report.pdf";
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      toast.success(`PDF exported successfully: ${filename}`);
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("Failed to export PDF");
    } finally {
      setIsExporting(false);
    }
  };

  const handlePortfolioChange = (portfolioId) => {
    setSelectedPortfolios((prev) =>
      prev.includes(portfolioId)
        ? prev.filter((id) => id !== portfolioId)
        : [...prev, portfolioId]
    );
  };

  const handleTransactionTypeChange = (type) => {
    setTransactionTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleAssetSymbolChange = (e) => {
    const symbols = e.target.value
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s);
    setAssetSymbols(symbols);
  };

  const handleClose = () => {
    setSelectedPortfolios([]);
    setDateRange({ startDate: "", endDate: "" });
    setTransactionTypes([]);
    setAssetSymbols([]);
    setAmountRange({ minAmount: "", maxAmount: "" });
    setExportOptions({
      include_summary: true,
      include_charts: false,
      include_portfolio_details: true,
      include_asset_details: true,
      group_by_portfolio: false,
      group_by_asset: false,
      sort_by: "transaction_date",
      sort_order: "desc",
    });
    setCustomFilename("");
    setPreviewData(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
              <Download className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-100">
                Export Transaction PDF
              </h2>
              <p className="text-sm text-gray-400">
                Generate professional PDF reports with advanced filtering
              </p>
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
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Filters */}
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-100">Filters</h3>

              {/* Portfolio Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Portfolios
                </label>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {portfolios.map((portfolio) => (
                    <label
                      key={portfolio.id}
                      className="flex items-center space-x-2"
                    >
                      <input
                        type="checkbox"
                        checked={selectedPortfolios.includes(
                          portfolio.id.toString()
                        )}
                        onChange={() =>
                          handlePortfolioChange(portfolio.id.toString())
                        }
                        className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-300">
                        {portfolio.name}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Leave unchecked to include all portfolios
                </p>
              </div>

              {/* Date Range */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Date Range
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={dateRange.startDate}
                      onChange={(e) =>
                        setDateRange((prev) => ({
                          ...prev,
                          startDate: e.target.value,
                        }))
                      }
                      className="input-field w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={dateRange.endDate}
                      onChange={(e) =>
                        setDateRange((prev) => ({
                          ...prev,
                          endDate: e.target.value,
                        }))
                      }
                      className="input-field w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Transaction Types */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Transaction Types
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-32 overflow-y-auto">
                  {transactionTypeOptions.map((type) => (
                    <label
                      key={type.value}
                      className="flex items-center space-x-2"
                    >
                      <input
                        type="checkbox"
                        checked={transactionTypes.includes(type.value)}
                        onChange={() => handleTransactionTypeChange(type.value)}
                        className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-300">
                        {type.label}
                      </span>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Leave unchecked to include all types
                </p>
              </div>

              {/* Asset Symbols */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Asset Symbols
                </label>
                <input
                  type="text"
                  placeholder="AAPL, GOOGL, MSFT (comma-separated)"
                  value={assetSymbols.join(", ")}
                  onChange={handleAssetSymbolChange}
                  className="input-field w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty to include all assets
                </p>
              </div>

              {/* Amount Range */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Amount Range
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Min Amount ($)
                    </label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={amountRange.minAmount}
                      onChange={(e) =>
                        setAmountRange((prev) => ({
                          ...prev,
                          minAmount: e.target.value,
                        }))
                      }
                      className="input-field w-full"
                      step="0.01"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">
                      Max Amount ($)
                    </label>
                    <input
                      type="number"
                      placeholder="0.00"
                      value={amountRange.maxAmount}
                      onChange={(e) =>
                        setAmountRange((prev) => ({
                          ...prev,
                          maxAmount: e.target.value,
                        }))
                      }
                      className="input-field w-full"
                      step="0.01"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column - Options & Preview */}
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-gray-100">
                Export Options
              </h3>

              {/* Export Options */}
              <div className="space-y-3">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={exportOptions.include_summary}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        include_summary: e.target.checked,
                      }))
                    }
                    className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">
                    Include Summary Statistics
                  </span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={exportOptions.include_portfolio_details}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        include_portfolio_details: e.target.checked,
                      }))
                    }
                    className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">
                    Include Portfolio Details
                  </span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={exportOptions.include_asset_details}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        include_asset_details: e.target.checked,
                      }))
                    }
                    className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">
                    Include Asset Details
                  </span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={exportOptions.group_by_portfolio}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        group_by_portfolio: e.target.checked,
                      }))
                    }
                    className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">
                    Group by Portfolio
                  </span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={exportOptions.group_by_asset}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        group_by_asset: e.target.checked,
                      }))
                    }
                    className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">Group by Asset</span>
                </label>
              </div>

              {/* Sort Options */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Sort By
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <select
                    value={exportOptions.sort_by}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        sort_by: e.target.value,
                      }))
                    }
                    className="input-field w-full"
                  >
                    {sortByOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={exportOptions.sort_order}
                    onChange={(e) =>
                      setExportOptions((prev) => ({
                        ...prev,
                        sort_order: e.target.value,
                      }))
                    }
                    className="input-field w-full"
                  >
                    <option value="asc">Ascending</option>
                    <option value="desc">Descending</option>
                  </select>
                </div>
              </div>

              {/* Custom Filename */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Custom Filename (Optional)
                </label>
                <input
                  type="text"
                  placeholder="my_transactions_report"
                  value={customFilename}
                  onChange={(e) => setCustomFilename(e.target.value)}
                  className="input-field w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty for auto-generated filename
                </p>
              </div>

              {/* Preview Section */}
              {previewData && (
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-gray-300 mb-3">
                    Export Preview
                  </h4>
                  <div className="text-sm text-gray-400 space-y-1">
                    <div>Transactions: {previewData.transaction_count}</div>
                    <div>Estimated Pages: {previewData.estimated_pages}</div>
                    <div>
                      Date Range:{" "}
                      {previewData.summary_stats?.date_range || "All"}
                    </div>
                    <div>
                      Portfolios:{" "}
                      {previewData.summary_stats?.portfolios_included?.join(
                        ", "
                      ) || "All"}
                    </div>
                    <div>
                      Total Buy Volume: $
                      {previewData.summary_stats?.total_buy_volume?.toFixed(
                        2
                      ) || "0.00"}
                    </div>
                    <div>
                      Total Sell Volume: $
                      {previewData.summary_stats?.total_sell_volume?.toFixed(
                        2
                      ) || "0.00"}
                    </div>
                    <div>
                      Net Flow: $
                      {previewData.summary_stats?.net_flow?.toFixed(2) ||
                        "0.00"}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-700">
          <button
            onClick={handlePreview}
            disabled={isPreviewing || isExporting}
            className="btn-outline flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPreviewing ? (
              <>
                <div className="w-4 h-4 border-2 border-primary-400 border-t-transparent rounded-full animate-spin" />
                <span>Previewing...</span>
              </>
            ) : (
              <>
                <Eye size={16} />
                <span>Preview Export</span>
              </>
            )}
          </button>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-gray-400 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting || isPreviewing}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isExporting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Exporting...</span>
                </>
              ) : (
                <>
                  <Download size={16} />
                  <span>Export PDF</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

TransactionExportModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  portfolios: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      name: PropTypes.string.isRequired,
    })
  ).isRequired,
};

export default TransactionExportModal;
