import { Edit, Trash2 } from "lucide-react";
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

  const type = transaction.transaction_type || transaction.type || "unknown";
  const subtitle = [
    transaction.asset?.name,
    transaction.portfolio?.name,
    formatDate(transaction.transaction_date),
    `#${transaction.id}`,
  ].filter(Boolean);

  return (
    <div className="card px-4 py-3 hover:bg-dark-800/50 transition-colors">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-10 h-10 bg-dark-800 rounded-lg shrink-0">
            {getTransactionIcon(type)}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-gray-100">
                <span className={getTransactionColor(type)}>
                  {type.toUpperCase()}
                </span>{" "}
                {transaction.asset?.symbol || transaction.symbol}
              </h3>
              <span
                className={`hidden sm:inline-block px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
                  transaction.status
                )}`}
              >
                {getStatusText(transaction.status)}
              </span>
            </div>
            <div className="text-sm text-gray-400 truncate">
              {subtitle.join(" · ")}
            </div>
            {transaction.notes && (
              <div
                className="text-xs text-gray-500 truncate"
                title={transaction.notes}
              >
                {transaction.notes}
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-6 shrink-0">
          <div className="text-right">
            <div className="flex items-center justify-end gap-2">
              {getTransactionArrow(type)}
              <span className="text-base font-semibold text-gray-100">
                {type === "buy" ? "-" : "+"}
                {formatCurrency(Math.abs(transaction.total_amount) || 0, { currency: transaction.currency })}
              </span>
            </div>
            <div className="text-sm text-gray-400">
              {formatQuantity(transaction.quantity)} @{" "}
              {formatCurrency(transaction.price || 0, { currency: transaction.currency })}
            </div>
          </div>

          {Number(transaction.fees) > 0 && (
            <div className="text-right hidden md:block">
              <div className="text-sm text-gray-400">Fees</div>
              <div className="text-sm font-medium text-gray-300">
                {formatCurrency(transaction.fees, { currency: transaction.currency })}
              </div>
            </div>
          )}

          <div className="flex items-center gap-1">
            <button
              onClick={onEdit}
              className="p-2 rounded-lg hover:bg-dark-800 transition-colors"
              title="Edit transaction"
              aria-label="Edit transaction"
            >
              <Edit size={16} className="text-gray-400" />
            </button>
            <button
              onClick={onDelete}
              className="p-2 rounded-lg hover:bg-danger-600/20 transition-colors"
              title="Delete transaction"
              aria-label="Delete transaction"
            >
              <Trash2 size={16} className="text-danger-400" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransactionCard;
