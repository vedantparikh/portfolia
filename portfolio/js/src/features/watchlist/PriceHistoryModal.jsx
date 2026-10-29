import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";

import Sparkline from "../../components/shared/Sparkline";
import { Modal } from "../../shared/ui";
import LoadingSpinner from "../../shared/ui/Spinner";
import { formatDate, formatQuote } from "../../utils/formatters.jsx";
import { watchlistAPI } from "./api";
import { watchlistKeys } from "./queries";

const PriceHistoryModal = ({ watchlistId, item, onClose }) => {
  const { data: history = [], isPending } = useQuery({
    queryKey: watchlistKeys.history(item?.id ?? "none"),
    queryFn: () => watchlistAPI.getItemHistory(watchlistId, item.id),
    enabled: Boolean(item && watchlistId),
  });
  if (!item) return null;

  const prices = history.map((point) => Number(point.price));
  const low = prices.length ? Math.min(...prices) : null;
  const high = prices.length ? Math.max(...prices) : null;
  const first = history[0];
  const last = history[history.length - 1];

  return (
    <Modal onClose={onClose}>
      <div className="bg-dark-900 border border-dark-700 rounded-lg w-full max-w-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">
            {item.symbol} price history
          </h2>
          <button type="button" onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-200">
            <X size={20} />
          </button>
        </div>
        {isPending ? (
          <LoadingSpinner centered />
        ) : history.length < 2 ? (
          <p className="text-sm text-gray-400">
            The worker records one price a day; there is not enough history yet.
          </p>
        ) : (
          <>
            <Sparkline
              values={prices}
              width={520}
              height={160}
              className="text-primary-400 w-full h-auto"
              title={`${item.symbol} daily prices`}
            />
            <dl className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div>
                <dt className="text-gray-400">{formatDate(first.date)}</dt>
                <dd className="text-gray-100">{formatQuote(first.price, item.currency)}</dd>
              </div>
              <div>
                <dt className="text-gray-400">{formatDate(last.date)}</dt>
                <dd className="text-gray-100">{formatQuote(last.price, item.currency)}</dd>
              </div>
              <div>
                <dt className="text-gray-400">Low</dt>
                <dd className="text-gray-100">{formatQuote(low, item.currency)}</dd>
              </div>
              <div>
                <dt className="text-gray-400">High</dt>
                <dd className="text-gray-100">{formatQuote(high, item.currency)}</dd>
              </div>
            </dl>
          </>
        )}
      </div>
    </Modal>
  );
};

export default PriceHistoryModal;
