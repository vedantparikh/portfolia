import { AlertTriangle } from "lucide-react";

export const EmptyState = ({
  icon: Icon,
  title,
  message,
  action,
  className = "text-center py-12",
}) => (
  <div className={className}>
    {Icon && <Icon className="w-16 h-16 text-gray-600 mx-auto mb-4" />}
    <h3 className="text-lg font-semibold text-gray-300 mb-2">{title}</h3>
    {message && (
      <p className={action ? "text-gray-500 mb-4" : "text-gray-500"}>
        {message}
      </p>
    )}
    {action}
  </div>
);

export const ErrorState = ({
  icon: Icon = AlertTriangle,
  title,
  message,
  onRetry,
  retryLabel = "Try Again",
  className = "text-center py-12",
}) => (
  <div className={className}>
    <Icon className="w-16 h-16 text-danger-400 mx-auto mb-4" />
    <h3 className="text-lg font-semibold text-gray-300 mb-2">{title}</h3>
    {message && <p className="text-gray-500 mb-4">{message}</p>}
    {onRetry && (
      <button onClick={onRetry} className="btn-primary">
        {retryLabel}
      </button>
    )}
  </div>
);
