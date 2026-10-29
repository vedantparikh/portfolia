import { Activity, BarChart3, Edit, Save, X } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import {
  formatMarketCap,
  formatPercentage,
  formatPrice,
  formatRatio,
  formatVolume,
  getChangeColor,
  getChangeIcon,
} from "../../utils/formatters.jsx";
import { SymbolSearch } from "../../components/shared";
import IndicatorChart from "../analytics/IndicatorChart";
import { Modal } from "../../shared/ui";

const AssetModal = ({ asset, mode = "view", onClose, onSave, onOpenAnalytics, existingAssets = [] }) => {
  const [activeTab, setActiveTab] = useState("overview");
  const [formData, setFormData] = useState({
    symbol: "",
    name: "",
    asset_type: "EQUITY",
    exchange: "",
    sector: "",
    industry: "",
    country: "",
    description: "",
    is_active: true,
  });
  const [isEditing, setIsEditing] = useState(false);
  const [duplicateError, setDuplicateError] = useState("");

  // Initialize form data when asset changes
  useEffect(() => {
    if (asset) {
      setFormData({
        symbol: asset.symbol || "",
        name: asset.name || "",
        asset_type: asset.asset_type || "EQUITY",
        exchange: asset.exchange || "",
        sector: asset.sector || "",
        industry: asset.industry || "",
        country: asset.country || "",
        description: asset.description || "",
        is_active: asset.is_active !== undefined ? asset.is_active : true,
      });
    } else {
      setFormData({
        symbol: "",
        name: "",
        asset_type: "EQUITY",
        exchange: "",
        sector: "",
        industry: "",
        country: "",
        description: "",
        is_active: true,
      });
    }
  }, [asset]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));

    // Clear duplicate error when user changes symbol
    if (name === 'symbol') {
      setDuplicateError("");
    }
  };

  // Check for duplicate assets
  const checkForDuplicate = (symbol) => {
    if (!symbol || mode !== 'create') return false;

    console.log('[AssetModal] Checking for duplicate:', symbol, 'in existing assets:', existingAssets);

    const duplicate = existingAssets.find(existingAsset =>
      existingAsset.symbol && existingAsset.symbol.toLowerCase() === symbol.toLowerCase()
    );

    if (duplicate) {
      console.log('[AssetModal] Duplicate found:', duplicate);
      setDuplicateError(`Asset "${symbol}" already exists in your portfolio. Please choose a different symbol.`);
      return true;
    } else {
      console.log('[AssetModal] No duplicate found');
      setDuplicateError("");
      return false;
    }
  };

  const handleSave = async () => {
    // Check for duplicates before saving
    if (mode === 'create' && checkForDuplicate(formData.symbol)) {
      return; // Don't save if duplicate found
    }

    // Validate required fields
    if (!formData.symbol || !formData.symbol.trim()) {
      toast.error('Symbol is required');
      return;
    }

    if (!formData.name || !formData.name.trim()) {
      toast.error('Asset name is required');
      return;
    }

    try {
      console.log('[AssetModal] Saving asset with data:', formData);
      const savedAsset = await onSave(formData);
      if (savedAsset) {
        toast.success(
          `Asset ${mode === "create" ? "created" : "updated"} successfully`
        );
        onClose();
      }
    } catch (error) {
      console.error("Failed to save asset:", error);
      toast.error(`Failed to ${mode === "create" ? "create" : "update"} asset`);
    }
  };

  const handleCancel = () => {
    onClose();
  };

  const isCreateMode = mode === "create";
  const isViewMode = mode === "view";

  return (
    <Modal onClose={onClose}>
      <div
        className={`bg-dark-900 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-dark-700">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-primary-600/20 rounded-lg flex items-center justify-center">
              <BarChart3 size={20} className="text-primary-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-100">
                {isCreateMode
                  ? "Create New Asset"
                  : isViewMode && !isEditing
                    ? "Asset Details"
                    : "Edit Asset"}
              </h2>
              <p className="text-sm text-gray-400">
                {isCreateMode
                  ? "Add a new asset for analysis"
                  : isViewMode && !isEditing
                    ? "View and analyze asset information"
                    : "Update asset information"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isViewMode && onOpenAnalytics && (
              <button
                type="button"
                onClick={onOpenAnalytics}
                className="btn-outline text-sm flex items-center gap-2"
              >
                <Activity size={16} />
                <span>Open analysis</span>
              </button>
            )}
            <button
              onClick={onClose}
              aria-label="Close"
              className="p-2 hover:bg-dark-800 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col overflow-hidden min-h-0">
          {isCreateMode ? (
            /* Create Mode */
            <div className="p-6 flex-1 overflow-y-auto">
              <div className="space-y-6">
                {/* Symbol Search */}
                <div className="card p-6 relative z-10">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    Search Asset
                  </h3>
                  <div className="relative">
                    <SymbolSearch
                      value={formData.symbol}
                      onChange={(value) => {
                        setFormData((prev) => ({
                          ...prev,
                          symbol: value,
                        }));
                      }}
                      onSelect={(selectedAsset) => {
                        // Check for duplicate before setting the form data
                        if (checkForDuplicate(selectedAsset.symbol)) {
                          return; // Don't update form if duplicate found
                        }

                        setFormData((prev) => ({
                          ...prev,
                          symbol: selectedAsset.symbol || "",
                          name: selectedAsset.name || selectedAsset.long_name || selectedAsset.short_name || "",
                          asset_type: selectedAsset.asset_type || "EQUITY",
                          exchange: selectedAsset.exchange || "",
                          sector: selectedAsset.sector || "",
                          industry: selectedAsset.industry || "",
                          country: selectedAsset.country || "",
                        }));
                      }}
                      placeholder="Search for a stock symbol..."
                    />
                  </div>

                  {/* Duplicate Error Display */}
                  {duplicateError && (
                    <div className="mt-3 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                      <p className="text-red-400 text-sm">{duplicateError}</p>
                    </div>
                  )}
                </div>

                {/* Asset Form */}
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-100 mb-4">
                    Asset Information
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Symbol *
                      </label>
                      <input
                        type="text"
                        name="symbol"
                        value={formData.symbol}
                        onChange={handleInputChange}
                        className="input-field"
                        placeholder="e.g., AAPL"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Name *
                      </label>
                      <input
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleInputChange}
                        className="input-field"
                        placeholder="e.g., Apple Inc."
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Asset Type
                      </label>
                      <select
                        name="asset_type"
                        value={formData.asset_type}
                        onChange={handleInputChange}
                        className="input-field"
                      >
                        <option value="EQUITY">Stock</option>
                        <option value="ETF">ETF</option>
                        <option value="CRYPTOCURRENCY">Cryptocurrency</option>
                        <option value="COMMODITY">Commodity</option>
                        <option value="BOND">Bond</option>
                        <option value="MUTUALFUND">Mutual Fund</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Exchange
                      </label>
                      <input
                        type="text"
                        name="exchange"
                        value={formData.exchange}
                        onChange={handleInputChange}
                        className="input-field"
                        placeholder="e.g., NASDAQ"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Sector
                      </label>
                      <input
                        type="text"
                        name="sector"
                        value={formData.sector}
                        onChange={handleInputChange}
                        className="input-field"
                        placeholder="e.g., Technology"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Industry
                      </label>
                      <input
                        type="text"
                        name="industry"
                        value={formData.industry}
                        onChange={handleInputChange}
                        className="input-field"
                        placeholder="e.g., Consumer Electronics"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Country
                      </label>
                      <input
                        type="text"
                        name="country"
                        value={formData.country}
                        onChange={handleInputChange}
                        className="input-field"
                        placeholder="e.g., United States"
                      />
                    </div>
                    <div className="md:col-span-2">
                      <label className="block text-sm font-medium text-gray-300 mb-2">
                        Description
                      </label>
                      <textarea
                        name="description"
                        value={formData.description}
                        onChange={handleInputChange}
                        className="input-field"
                        rows={3}
                        placeholder="Optional description..."
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* View/Edit Mode */
            <div className="p-6 flex-1 flex flex-col min-h-0">
              {/* Tabs */}
              <div className="flex space-x-1 mb-6 border-b border-dark-700">
                <button
                  onClick={() => setActiveTab("overview")}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === "overview"
                    ? "text-primary-400 border-b-2 border-primary-400"
                    : "text-gray-400 hover:text-gray-300"
                    }`}
                >
                  Overview
                </button>
                <button
                  onClick={() => setActiveTab("chart")}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${activeTab === "chart"
                    ? "text-primary-400 border-b-2 border-primary-400"
                    : "text-gray-400 hover:text-gray-300"
                    }`}
                >
                  Chart
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto min-h-0">
                {activeTab === "overview" && (
                  <div className="space-y-6">
                    {/* Asset Information */}
                    <div className="card p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold text-gray-100">
                          Asset Information
                        </h3>
                        {isViewMode && (
                          <button
                            onClick={() => setIsEditing(!isEditing)}
                            className="btn-outline text-sm flex items-center space-x-2"
                          >
                            <Edit size={16} />
                            <span>{isEditing ? "Cancel" : "Edit"}</span>
                          </button>
                        )}
                      </div>

                      {isEditing ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Symbol
                            </label>
                            <input
                              type="text"
                              name="symbol"
                              value={formData.symbol}
                              onChange={handleInputChange}
                              className="input-field"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Name
                            </label>
                            <input
                              type="text"
                              name="name"
                              value={formData.name}
                              onChange={handleInputChange}
                              className="input-field"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Asset Type
                            </label>
                            <select
                              name="asset_type"
                              value={formData.asset_type}
                              onChange={handleInputChange}
                              className="input-field"
                            >
                              <option value="EQUITY">Stock</option>
                              <option value="ETF">ETF</option>
                              <option value="CRYPTOCURRENCY">
                                Cryptocurrency
                              </option>
                              <option value="COMMODITY">Commodity</option>
                              <option value="BOND">Bond</option>
                              <option value="MUTUALFUND">Mutual Fund</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Exchange
                            </label>
                            <input
                              type="text"
                              name="exchange"
                              value={formData.exchange}
                              onChange={handleInputChange}
                              className="input-field"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Sector
                            </label>
                            <input
                              type="text"
                              name="sector"
                              value={formData.sector}
                              onChange={handleInputChange}
                              className="input-field"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Industry
                            </label>
                            <input
                              type="text"
                              name="industry"
                              value={formData.industry}
                              onChange={handleInputChange}
                              className="input-field"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Country
                            </label>
                            <input
                              type="text"
                              name="country"
                              value={formData.country}
                              onChange={handleInputChange}
                              className="input-field"
                            />
                          </div>
                          <div className="md:col-span-2">
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Description
                            </label>
                            <textarea
                              name="description"
                              value={formData.description}
                              onChange={handleInputChange}
                              className="input-field"
                              rows={3}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <span className="text-sm text-gray-400">
                              Symbol
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset?.symbol || "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">Name</span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset?.name || "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Asset Type
                            </span>
                            <p className="text-sm text-gray-300">
                              {asset?.asset_type || "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Exchange
                            </span>
                            <p className="text-sm text-gray-300">
                              {asset?.exchange || "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Sector
                            </span>
                            <p className="text-sm text-gray-300">
                              {asset?.sector || "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Industry
                            </span>
                            <p className="text-sm text-gray-300">
                              {asset?.industry || "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Country
                            </span>
                            <p className="text-sm text-gray-300">
                              {asset?.country || "N/A"}
                            </p>
                          </div>
                          {asset?.description && (
                            <div className="md:col-span-2">
                              <span className="text-sm text-gray-400">
                                Description
                              </span>
                              <p className="text-sm text-gray-300">
                                {asset.description}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Market Data */}
                    <div className="card p-6">
                      <h3 className="text-lg font-semibold text-gray-100 mb-4">
                        Market Data
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div>
                          <span className="text-sm text-gray-400">
                            Current Price
                          </span>
                          <p className="text-2xl font-bold text-gray-100">
                            {formatPrice(asset?.detail?.current_price, asset?.currency)}
                          </p>
                          {asset?.detail?.price_change_percentage_24h && (
                            <div className="flex items-center space-x-1">
                              {getChangeIcon(
                                asset.detail?.price_change_percentage_24h
                              )}
                              <span
                                className={`text-sm ${getChangeColor(
                                  asset.detail?.price_change_percentage_24h
                                )}`}
                              >
                                {formatPercentage(
                                  asset.detail?.price_change_percentage_24h
                                )}
                              </span>
                            </div>
                          )}
                        </div>
                        <div>
                          <span className="text-sm text-gray-400">
                            Market Cap
                          </span>
                          <p className="text-lg font-semibold text-gray-100">
                            {asset?.detail?.market_cap
                              ? `${formatMarketCap(asset.detail?.market_cap, asset.currency)}`
                              : "N/A"}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-400">
                            Volume (24h)
                          </span>
                          <p className="text-lg font-semibold text-gray-100">
                            {asset?.detail?.volume_24h
                              ? `${formatVolume(asset.detail?.volume_24h)}`
                              : "N/A"}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-400">
                            Day Open / High / Low
                          </span>
                          <p className="text-lg font-semibold text-gray-100">
                            {asset?.detail?.day_high
                              ? `${formatPrice(asset.detail?.open, asset.currency)} / ${formatPrice(asset.detail?.day_high, asset.currency)} / ${formatPrice(asset.detail?.day_low, asset.currency)}`
                              : "N/A"}
                          </p>
                        </div>
                        <div>
                          <span className="text-sm text-gray-400">
                            52 Week High/Low
                          </span>
                          <p className="text-lg font-semibold text-gray-100">
                            {asset?.detail?.high_52w
                              ? `${formatPrice(asset.detail?.high_52w, asset.currency)} / ${formatPrice(asset.detail?.low_52w, asset.currency)}`
                              : "N/A"}
                          </p>
                        </div>

                        <div></div>
                      </div>
                    </div>

                    {/* Business Information -- NEW SECTION */}
                    {!isEditing && asset.detail && (
                      <div className="card p-6">
                        <h3 className="text-lg font-semibold text-gray-100 mb-4">
                          Business Information
                        </h3>

                        {/* Key Metrics Grid */}
                        <h4 className="text-sm font-medium text-gray-400 mb-3">
                          Key Metrics
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                          <div>
                            <span className="text-sm text-gray-400">Beta</span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.beta
                                ? formatRatio(asset.detail.beta)
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Trailing P/E
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.trailing_PE
                                ? formatRatio(asset.detail.trailing_PE)
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Forward P/E
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.forward_PE
                                ? formatRatio(asset.detail.forward_PE)
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Book Value
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {formatPrice(asset.detail?.book_value, asset.currency)}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Price/Book
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.price_to_book
                                ? formatRatio(asset.detail.price_to_book)
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Dividend Yield
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.dividend_yield
                                ? formatPercentage(asset.detail.dividend_yield, { showSign: false })
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Payout Ratio
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.payout_ratio
                                ? formatPercentage(Number(asset.detail.payout_ratio) * 100, { showSign: false })
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Employees
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.full_time_employees
                                ? Number(
                                  asset.detail.full_time_employees
                                ).toLocaleString()
                                : "N/A"}
                            </p>
                          </div>
                        </div>

                        {/* Financials Grid */}
                        <h4 className="text-sm font-medium text-gray-400 mb-3">
                          Financials
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                          <div>
                            <span className="text-sm text-gray-400">
                              Earnings Growth
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {formatPercentage(
                                asset.detail?.earnings_growth
                              )}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Revenue Growth
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {formatPercentage(asset.detail?.revenue_growth)}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Return on Assets
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.return_on_asset
                                ? formatPercentage(Number(asset.detail.return_on_asset) * 100, { showSign: false })
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Return on Equity
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.return_on_equity
                                ? formatPercentage(Number(asset.detail.return_on_equity) * 100, { showSign: false })
                                : "N/A"}
                            </p>
                          </div>

                          <div>
                            <span className="text-sm text-gray-400">
                              Operating Cashflow
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.operating_cashflow
                                ? `${formatMarketCap(
                                  asset.detail.operating_cashflow,
                                  asset.currency
                                )}`
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Free Cashflow
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.free_cashflow
                                ? `${formatMarketCap(
                                  asset.detail.free_cashflow,
                                  asset.currency
                                )}`
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Total Cash
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.total_cash
                                ? `${formatMarketCap(
                                  asset.detail.total_cash,
                                  asset.currency
                                )}`
                                : "N/A"}
                            </p>
                          </div>
                          <div>
                            <span className="text-sm text-gray-400">
                              Total Debt
                            </span>
                            <p className="text-lg font-semibold text-gray-100">
                              {asset.detail?.total_debt
                                ? `${formatMarketCap(
                                  asset.detail.total_debt,
                                  asset.currency
                                )}`
                                : "N/A"}
                            </p>
                          </div>
                        </div>

                        {/* Summary & Website */}
                        <div className="space-y-6">
                          {asset.detail?.long_business_summary && (
                            <div>
                              <h4 className="text-sm font-medium text-gray-400 mb-2">
                                Business Summary
                              </h4>
                              <p className="text-sm text-gray-300 mt-1 whitespace-pre-wrap">
                                {asset.detail.long_business_summary}
                              </p>
                            </div>
                          )}
                          {asset.detail?.website && (
                            <div>
                              <h4 className="text-sm font-medium text-gray-400 mb-2">
                                Website
                              </h4>
                              <p className="text-sm mt-1">
                                <a
                                  href={asset.detail.website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-primary-400 hover:underline break-all"
                                >
                                  {asset.detail.website}
                                </a>
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "chart" && (
                  <div className="card p-6 relative">
                    <IndicatorChart asset={asset} height={500} enableFullscreen />
                  </div>
                )}

              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 flex items-center justify-end p-6 border-t border-dark-700">
          <div className="flex space-x-3">
            <button onClick={handleCancel} className="btn-secondary">
              Cancel
            </button>
            {(!isViewMode || isEditing) && (
              <button
                onClick={handleSave}
                className="btn-primary flex items-center space-x-2"
              >
                <Save size={16} />
                <span>{isCreateMode ? "Create Asset" : "Save Changes"}</span>
              </button>
            )}
          </div>
        </div>
      </div>

    </Modal>
  );
};

export default AssetModal;