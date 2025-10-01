import { Edit, Trash2 } from "lucide-react";
import React from "react";
import {
  formatCurrency,
  formatDate,
  formatQuantity,
  getTransactionArrow,
  getTransactionColor,
  getTransactionIcon,
} from "../../utils/formatters.jsx";

const TransactionCard = ({ transaction, onEdit, onDelete }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "text-success-400 bg-success-400/20";
      case "pending":
        return "text-warning-400 bg-warning-400/20";
      case "failed":
        return "text-danger-400 bg-danger-400/20";
      case "cancelled":
        return "text-gray-400 bg-gray-400/20";
      default:
        return "text-gray-400 bg-gray-400/20";
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case "completed":
        return "Completed";
      case "pending":
        return "Pending";
      case "failed":
        return "Failed";
      case "cancelled":
        return "Cancelled";
      default:
        return "Unknown";
    }
  };

  return (
    <div className="card p-6 hover:bg-dark-800/50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center justify-center w-12 h-12 bg-dark-800 rounded-lg">
            {getTransactionIcon(
              transaction.transaction_type || transaction.type
            )}
          </div>
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <h3 className="text-lg font-semibold text-gray-100">
                {(
                  transaction.transaction_type ||
                  transaction.type ||
                  "unknown"
                ).toUpperCase()}{" "}
                {transaction.symbol}
              </h3>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
                  transaction.status
                )}`}
              >
                {getStatusText(transaction.status)}
              </span>
            </div>
            <div className="flex items-center space-x-4 text-sm text-gray-400 mb-1">
              <span>Portfolio: {transaction.portfolio.name || "unknown"}</span>
              <span>•</span>
              <span>{formatDate(transaction.transaction_date)}</span>
            </div>
            {/* Asset Information */}
            {transaction.asset.name && (
              <div className="text-sm text-gray-500">
                {transaction.asset.name}
                {transaction.asset.exchange && transaction.asset.asset_type && (
                  <span className="ml-2">
                    • {transaction.asset.exchange} •{" "}
                    {transaction.asset.asset_type}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-6">
          {/* Transaction Details */}
          <div className="text-right">
            <div className="flex items-center space-x-2 mb-1">
              {getTransactionArrow(transaction.transaction_type)}
              <span
                className={`text-lg font-semibold ${getTransactionColor(
                  transaction.transaction_type
                )}`}
              >
                {(transaction.transaction_type || transaction.type) === "buy"
                  ? "-"
                  : "+"}
                {formatCurrency(Math.abs(transaction.total_amount) || 0)}
              </span>
            </div>
            <div className="text-sm text-gray-400">
              {formatQuantity(transaction.quantity)} @{" "}
              {formatCurrency(transaction.price || 0)}
            </div>
          </div>

          {/* Fees */}
          {transaction.fees && transaction.fees > 0 && (
            <div className="text-right">
              <div className="text-sm text-gray-400">Fees</div>
              <div className="text-sm font-medium text-gray-300">
                {formatCurrency(transaction.fees)}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center space-x-2">
            <button
              onClick={onEdit}
              className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
              title="Edit transaction"
            >
              <Edit size={16} className="text-gray-400" />
            </button>
            <button
              onClick={onDelete}
              className="p-2 rounded-lg hover:bg-danger-600/20 transition-colors"
              title="Delete transaction"
            >
              <Trash2 size={16} className="text-danger-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Additional Details */}
      <div className="mt-4 pt-4 border-t border-dark-700">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Order ID:</span>
            <span className="text-gray-100 ml-2 font-mono">
              #{transaction.id}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Type:</span>
            <span
              className={`ml-2 font-medium ${getTransactionColor(
                transaction.transaction_type || transaction.type
              )}`}
            >
              {(
                transaction.transaction_type ||
                transaction.type ||
                "unknown"
              ).toUpperCase()}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Quantity:</span>
            <span className="text-gray-100 ml-2 font-medium">
              {formatQuantity(transaction.quantity)}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Price:</span>
            <span className="text-gray-100 ml-2 font-medium">
              {formatCurrency(transaction.price)}
            </span>
          </div>
        </div>

        {/* Notes */}
        {transaction.notes && (
          <div className="mt-3 pt-3 border-t border-dark-800">
            <span className="text-gray-400 text-sm">Notes:</span>
            <p className="text-gray-300 text-sm mt-1">{transaction.notes}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionCard;
