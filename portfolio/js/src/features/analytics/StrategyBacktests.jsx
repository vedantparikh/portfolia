import { ChartCandlestick, ChevronDown, ChevronRight, FlaskConical } from "lucide-react";
import { Fragment, useState } from "react";

import InfoTip from "../../shared/ui/InfoTip";
import LoadingSpinner from "../../shared/ui/Spinner";
import {
  formatDate,
  formatPercentage,
  formatPercentagePoints,
  formatQuote,
  getChangeColor,
} from "../../utils/formatters.jsx";
import { useStrategyBacktests } from "./queries";

const BACKTEST_YEARS = [1, 3, 5, 10];
const GUIDE_ID = { gfs: "gfs", macd: "macd_strategy" };

const ACTION_STYLE = { buy: "text-success-400", sell: "text-danger-400" };

const day = (iso) => formatDate(`${iso}T12:00:00`);
const plain = { showSign: false, precision: 0, defaultValue: "0%" };

const Trades = ({ trades, currency }) => (
  <table className="w-full text-xs text-gray-300">
    <thead className="text-gray-500">
      <tr>
        <th className="text-left font-normal py-1">Bought</th>
        <th className="text-right font-normal">at</th>
        <th className="text-left font-normal pl-4">Sold</th>
        <th className="text-right font-normal">at</th>
        <th className="text-right font-normal">Return</th>
      </tr>
    </thead>
    <tbody>
      {[...trades].reverse().map((trade) => (
        <tr key={trade.entry_date}>
          <td className="py-0.5">{day(trade.entry_date)}</td>
          <td className="text-right">{formatQuote(trade.entry_price, currency)}</td>
          <td className="pl-4">{trade.open ? "still held" : day(trade.exit_date)}</td>
          <td className="text-right">{formatQuote(trade.exit_price, currency)}</td>
          <td className={`text-right ${getChangeColor(trade.return_pct)}`}>{formatPercentage(trade.return_pct)}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

// Every rule in core/domain/strategies.py replayed on the same window, next to holding.
// `shown` is the rule whose trades the price chart marks.
const StrategyBacktests = ({ symbol, currency, years, onYearsChange, shown, onShow }) => {
  const [open, setOpen] = useState(null);
  const { data, isPending, isError } = useStrategyBacktests(symbol, years);
  const tested = data?.strategies.filter((row) => !row.error) ?? [];
  const beat = tested.filter((row) => row.total_return_pct > data.buy_and_hold_pct).length;

  return (
    <div className="card p-6">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-1">
        <h3 className="text-lg font-semibold text-gray-100 flex items-center">
          <FlaskConical className="w-5 h-5 mr-2 text-primary-400" />
          Strategy backtests
          <InfoTip id="backtest" className="ml-2" />
        </h3>
        <div role="group" aria-label="Backtest window" className="flex rounded-lg bg-dark-800 p-0.5 text-xs">
          {BACKTEST_YEARS.map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={years === value}
              onClick={() => onYearsChange(value)}
              className={`px-2.5 py-1 rounded-md ${years === value ? "bg-primary-600 text-white" : "text-gray-400 hover:text-gray-200"}`}
            >
              {value}y
            </button>
          ))}
        </div>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Each rule bought and sold at the close on its own signals, long only, no costs or taxes. Past results, not
        recommendations.
      </p>

      {isPending ? (
        <LoadingSpinner centered />
      ) : isError || !data ? (
        <p className="text-sm text-gray-400">No backtest: not enough price history.</p>
      ) : (
        <>
          <p className="text-sm text-gray-300 mb-3">
            Holding since {day(data.start)}:{" "}
            <span className={`font-medium ${getChangeColor(data.buy_and_hold_pct)}`}>
              {formatPercentage(data.buy_and_hold_pct)}
            </span>
            . {beat} of {tested.length} rules beat it.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="text-xs text-gray-500 border-b border-dark-700">
                <tr>
                  <th className="text-left font-normal py-2">Rule</th>
                  <th className="text-left font-normal">Last signal</th>
                  <th className="text-left font-normal">Now</th>
                  <th className="text-right font-normal">Return</th>
                  <th className="text-right font-normal">vs holding</th>
                  <th className="text-right font-normal">
                    Trades (won)
                    <InfoTip id="win_rate" className="ml-1" />
                  </th>
                  <th className="text-right font-normal">Invested</th>
                  <th className="text-right font-normal pl-3">Chart</th>
                </tr>
              </thead>
              <tbody>
                {data.strategies.map((row) => {
                  const expanded = open === row.strategy;
                  return (
                    <Fragment key={row.strategy}>
                      <tr className="border-b border-dark-800 align-top">
                        <td className="py-2 pr-3">
                          <div className="flex items-center">
                            <button
                              type="button"
                              onClick={() => setOpen(expanded ? null : row.strategy)}
                              disabled={!row.trades.length}
                              aria-expanded={expanded}
                              className="flex items-center text-left font-medium text-gray-100 disabled:cursor-default"
                            >
                              {row.trades.length ? (
                                expanded ? (
                                  <ChevronDown className="w-4 h-4 mr-1 text-gray-500" />
                                ) : (
                                  <ChevronRight className="w-4 h-4 mr-1 text-gray-500" />
                                )
                              ) : (
                                <span className="w-4 mr-1" />
                              )}
                              {row.name}
                            </button>
                            <InfoTip id={GUIDE_ID[row.strategy] ?? row.strategy} className="ml-1.5" />
                          </div>
                          <p className="text-xs text-gray-500 ml-5 max-w-sm">{row.rule}</p>
                        </td>
                        {row.error ? (
                          <td colSpan={7} className="py-2 text-xs text-gray-500">
                            {row.error}
                          </td>
                        ) : (
                          <>
                            <td className="py-2 whitespace-nowrap">
                              {row.last_signal ? (
                                <>
                                  <span className={`uppercase font-medium ${ACTION_STYLE[row.last_signal.action]}`}>
                                    {row.last_signal.action}
                                  </span>{" "}
                                  <span className="text-xs text-gray-500">{day(row.last_signal.date)}</span>
                                </>
                              ) : (
                                <span className="text-gray-500">none</span>
                              )}
                            </td>
                            <td className="py-2 text-gray-300">{row.invested ? "In" : "Out"}</td>
                            <td className={`py-2 text-right font-medium ${getChangeColor(row.total_return_pct)}`}>
                              {formatPercentage(row.total_return_pct)}
                            </td>
                            <td className={`py-2 text-right ${getChangeColor(row.vs_holding_pp)}`}>
                              {formatPercentagePoints(row.vs_holding_pp)}
                            </td>
                            <td className="py-2 text-right text-gray-300 whitespace-nowrap">
                              {row.trades.length}
                              {row.trades.length > 0 && ` (${formatPercentage(row.win_rate_pct, plain)})`}
                            </td>
                            <td className="py-2 text-right text-gray-300">
                              {formatPercentage(row.days_invested_pct, plain)}
                            </td>
                            <td className="py-2 pl-3 text-right">
                              <button
                                type="button"
                                onClick={() => onShow(shown === row.strategy ? null : row.strategy)}
                                aria-pressed={shown === row.strategy}
                                aria-label={`Show ${row.name} on the chart`}
                                title="Mark this rule's trades on the price chart"
                                className={`p-1 rounded-md ${shown === row.strategy ? "bg-primary-600 text-white" : "text-gray-500 hover:text-gray-200"}`}
                              >
                                <ChartCandlestick className="w-4 h-4" />
                              </button>
                            </td>
                          </>
                        )}
                      </tr>
                      {expanded && (
                        <tr className="border-b border-dark-800">
                          <td colSpan={8} className="pb-3 pl-5">
                            <Trades trades={row.trades} currency={currency} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};

export default StrategyBacktests;
