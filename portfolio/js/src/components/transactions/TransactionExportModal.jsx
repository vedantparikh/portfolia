import jsPDF from "jspdf";
import "jspdf-autotable";
import { Download, X } from "lucide-react";
import React, { useState } from "react";
import toast from "react-hot-toast";

const TransactionExportModal = ({
  isOpen,
  onClose,
  portfolios = [],
  transactions = [],
}) => {
  const [selectedPortfolio, setSelectedPortfolio] = useState("");
  const [dateRange, setDateRange] = useState({
    startDate: "",
    endDate: "",
  });
  const [transactionTypes, setTransactionTypes] = useState([]);
  const [exportFormat, setExportFormat] = useState("pdf");
  const [includeCharts, setIncludeCharts] = useState(false);
  const [includeSummary, setIncludeSummary] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

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

  const filterTransactions = () => {
    let filtered = [...transactions];

    // Filter by portfolio
    if (selectedPortfolio) {
      filtered = filtered.filter(
        (txn) => txn.portfolio_id === parseInt(selectedPortfolio)
      );
    }

    // Filter by date range
    if (dateRange.startDate) {
      filtered = filtered.filter(
        (txn) => new Date(txn.transaction_date) >= new Date(dateRange.startDate)
      );
    }
    if (dateRange.endDate) {
      filtered = filtered.filter(
        (txn) => new Date(txn.transaction_date) <= new Date(dateRange.endDate)
      );
    }

    // Filter by transaction types
    if (transactionTypes.length > 0) {
      filtered = filtered.filter((txn) =>
        transactionTypes.includes(txn.transaction_type)
      );
    }

    return filtered;
  };

  const generatePDF = async () => {
    const filteredTransactions = filterTransactions();

    if (filteredTransactions.length === 0) {
      toast.error("No transactions found with the selected filters");
      return;
    }

    setIsExporting(true);

    try {
      const doc = new jsPDF();
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();

      // Header
      doc.setFontSize(20);
      doc.setFont("helvetica", "bold");
      doc.text("Transaction Report", pageWidth / 2, 30, { align: "center" });

      // Portfolio info
      if (selectedPortfolio) {
        const portfolio = portfolios.find(
          (p) => p.id === parseInt(selectedPortfolio)
        );
        if (portfolio) {
          doc.setFontSize(14);
          doc.setFont("helvetica", "normal");
          doc.text(`Portfolio: ${portfolio.name}`, 20, 50);
        }
      }

      // Date range info
      if (dateRange.startDate || dateRange.endDate) {
        doc.setFontSize(12);
        doc.text(
          `Date Range: ${dateRange.startDate || "Start"} - ${
            dateRange.endDate || "End"
          }`,
          20,
          60
        );
      }

      // Summary section
      if (includeSummary) {
        const summary = calculateSummary(filteredTransactions);

        doc.setFontSize(14);
        doc.setFont("helvetica", "bold");
        doc.text("Summary", 20, 80);

        doc.setFontSize(10);
        doc.setFont("helvetica", "normal");
        doc.text(`Total Transactions: ${summary.totalTransactions}`, 20, 90);
        doc.text(
          `Total Buy Volume: $${summary.totalBuyVolume.toFixed(2)}`,
          20,
          100
        );
        doc.text(
          `Total Sell Volume: $${summary.totalSellVolume.toFixed(2)}`,
          20,
          110
        );
        doc.text(`Net Flow: $${summary.netFlow.toFixed(2)}`, 20, 120);
      }

      // Transactions table
      const tableData = filteredTransactions.map((txn) => [
        txn.transaction_date,
        txn.transaction_type.toUpperCase(),
        txn.asset?.symbol || txn.symbol || "-",
        txn.asset?.name || txn.name || "-",
        txn.quantity?.toFixed(4) || "0",
        `$${txn.price?.toFixed(2) || "0.00"}`,
        `$${txn.fees?.toFixed(2) || "0.00"}`,
        `$${txn.total_amount?.toFixed(2) || "0.00"}`,
        txn.notes || "-",
      ]);

      const startY = includeSummary ? 140 : 80;

      doc.autoTable({
        head: [
          [
            "Date",
            "Type",
            "Symbol",
            "Name",
            "Quantity",
            "Price",
            "Fees",
            "Total",
            "Notes",
          ],
        ],
        body: tableData,
        startY: startY,
        styles: {
          fontSize: 8,
          cellPadding: 2,
        },
        headStyles: {
          fillColor: [66, 139, 202],
          textColor: 255,
          fontStyle: "bold",
        },
        alternateRowStyles: {
          fillColor: [245, 245, 245],
        },
        margin: { left: 20, right: 20 },
      });

      // Footer
      const finalY = doc.lastAutoTable.finalY + 20;
      doc.setFontSize(8);
      doc.setFont("helvetica", "normal");
      doc.text(
        `Generated on ${new Date().toLocaleDateString()} at ${new Date().toLocaleTimeString()}`,
        pageWidth / 2,
        finalY,
        { align: "center" }
      );

      // Save the PDF
      const fileName = `transactions_${
        selectedPortfolio
          ? portfolios
              .find((p) => p.id === parseInt(selectedPortfolio))
              ?.name.replace(/\s+/g, "_")
          : "all"
      }_${new Date().toISOString().split("T")[0]}.pdf`;
      doc.save(fileName);

      toast.success(`PDF exported successfully: ${fileName}`);
    } catch (error) {
      console.error("Failed to generate PDF:", error);
      toast.error("Failed to generate PDF");
    } finally {
      setIsExporting(false);
    }
  };

  const calculateSummary = (transactions) => {
    const totalTransactions = transactions.length;
    const totalBuyVolume = transactions
      .filter((txn) => txn.transaction_type === "buy")
      .reduce((sum, txn) => sum + (parseFloat(txn.total_amount) || 0), 0);
    const totalSellVolume = transactions
      .filter((txn) => txn.transaction_type === "sell")
      .reduce((sum, txn) => sum + (parseFloat(txn.total_amount) || 0), 0);
    const netFlow = totalSellVolume - totalBuyVolume;

    return {
      totalTransactions,
      totalBuyVolume,
      totalSellVolume,
      netFlow,
    };
  };

  const handleTransactionTypeChange = (type) => {
    setTransactionTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  const handleClose = () => {
    setSelectedPortfolio("");
    setDateRange({ startDate: "", endDate: "" });
    setTransactionTypes([]);
    setExportFormat("pdf");
    setIncludeCharts(false);
    setIncludeSummary(true);
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
              <Download className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-100">
                Export Transactions
              </h2>
              <p className="text-sm text-gray-400">
                Generate PDF report of your transactions
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
        <div className="p-6 space-y-6">
          {/* Portfolio Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Portfolio
            </label>
            <select
              value={selectedPortfolio}
              onChange={(e) => setSelectedPortfolio(e.target.value)}
              className="input-field w-full"
            >
              <option value="">All Portfolios</option>
              {portfolios.map((portfolio) => (
                <option key={portfolio.id} value={portfolio.id}>
                  {portfolio.name}
                </option>
              ))}
            </select>
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
            <div className="grid grid-cols-2 gap-2">
              {transactionTypeOptions.map((type) => (
                <label key={type.value} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={transactionTypes.includes(type.value)}
                    onChange={() => handleTransactionTypeChange(type.value)}
                    className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-300">{type.label}</span>
                </label>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Leave unchecked to include all types
            </p>
          </div>

          {/* Export Options */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">
              Export Options
            </label>
            <div className="space-y-3">
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={includeSummary}
                  onChange={(e) => setIncludeSummary(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-300">
                  Include Summary Statistics
                </span>
              </label>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={includeCharts}
                  onChange={(e) => setIncludeCharts(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-700 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-300">
                  Include Charts (Coming Soon)
                </span>
              </label>
            </div>
          </div>

          {/* Preview */}
          <div className="bg-gray-700/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-2">
              Export Preview
            </h3>
            <div className="text-sm text-gray-400 space-y-1">
              <div>
                Portfolio:{" "}
                {selectedPortfolio
                  ? portfolios.find((p) => p.id === parseInt(selectedPortfolio))
                      ?.name || "All"
                  : "All Portfolios"}
              </div>
              <div>
                Date Range: {dateRange.startDate || "Start"} -{" "}
                {dateRange.endDate || "End"}
              </div>
              <div>
                Transaction Types:{" "}
                {transactionTypes.length > 0
                  ? transactionTypes.join(", ")
                  : "All"}
              </div>
              <div>Estimated Transactions: {filterTransactions().length}</div>
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
            onClick={generatePDF}
            disabled={isExporting || filterTransactions().length === 0}
            className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Generating...</span>
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
  );
};

export default TransactionExportModal;
