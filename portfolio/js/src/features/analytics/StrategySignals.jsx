import { Signal } from "lucide-react";

import LoadingSpinner from "../../shared/ui/Spinner";
import { formatDate, formatQuote, formatRatio } from "../../utils/formatters.jsx";
import { useStrategySignals } from "./queries";

const ACTION_STYLE = {
  buy: "text-success-400",
  sell: "text-danger-400",
  hold: "text-gray-300",
};

const day = (iso) => formatDate(`${iso}T12:00:00`);

// What two rule sets say about the symbol (core/domain/strategies.py); not advice
const StrategySignals = ({ symbol, currency }) => {
  const { data, isPending } = useStrategySignals(symbol);

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-gray-100 mb-1 flex items-center">
        <Signal className="w-5 h-5 mr-2 text-primary-400" />
        Strategy signals
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        What two fixed rule sets say about the price history. They are not recommendations.
      </p>
      {isPending ? (
        <LoadingSpinner centered />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section>
            <h4 className="font-medium text-gray-100">Grandfather-father-son RSI</h4>
            <p className="text-xs text-gray-500 mb-2">
              RSI(14) of monthly, weekly and daily closes: all below 30 = buy, all above 70 = sell.
            </p>
            {data?.gfs ? (
              <>
                <p className={`text-xl font-semibold uppercase ${ACTION_STYLE[data.gfs.action]}`}>
                  {data.gfs.action}
                </p>
                <ul className="mt-2 text-sm text-gray-300 space-y-1">
                  {data.gfs.readings.map((reading) => (
                    <li key={reading.timeframe} className="flex justify-between">
                      <span className="capitalize">{reading.timeframe}</span>
                      <span>
                        {formatRatio(reading.rsi, 1)}{" "}
                        <span className="text-xs text-gray-500">({day(reading.as_of)})</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="text-sm text-gray-400">Not enough price history.</p>
            )}
          </section>
          <section>
            <h4 className="font-medium text-gray-100">MACD with 200-day trend</h4>
            <p className="text-xs text-gray-500 mb-2">
              MACD crossing its signal below zero above the 200-day EMA = buy; above zero below it = sell. Last 12 months.
            </p>
            {!data?.macd ? (
              <p className="text-sm text-gray-400">Not enough price history.</p>
            ) : data.macd.signals.length === 0 ? (
              <p className="text-sm text-gray-400">No signal in the last 12 months.</p>
            ) : (
              <ul className="text-sm text-gray-300 space-y-1">
                {[...data.macd.signals].reverse().map((signal) => (
                  <li key={`${signal.date}-${signal.action}`} className="flex justify-between">
                    <span>{day(signal.date)}</span>
                    <span className={`uppercase font-medium ${ACTION_STYLE[signal.action]}`}>
                      {signal.action}
                    </span>
                    <span>{formatQuote(signal.close, currency)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
};

export default StrategySignals;
