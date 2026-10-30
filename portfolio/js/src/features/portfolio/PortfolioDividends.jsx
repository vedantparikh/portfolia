import { Coins } from "lucide-react";
import { useMemo, useState } from "react";

import { useMoney } from "../../hooks/useMoney";
import InfoTip from "../../shared/ui/InfoTip";
import LoadingSpinner from "../../shared/ui/Spinner";
import { formatDate, formatPercentage, formatQuantity, getChangeColor } from "../../utils/formatters.jsx";
import IncomeChart from "./IncomeChart";
import { useDividends } from "./queries";

const day = (d) => formatDate(`${d}T12:00:00`);
const pct = (v) => (v == null ? "—" : formatPercentage(v, { showSign: false, precision: 2 }));
const monthName = (d, options = { month: "short", year: "numeric" }) =>
  new Date(`${d}T12:00:00`).toLocaleDateString(undefined, options);

const Card = ({ title, info, subtitle, actions, children }) => (
  <div className="card p-6">
    <div className="flex items-start justify-between gap-3">
      <div>
        <h3 className="text-lg font-semibold text-gray-100 flex items-center">
          {title}
          {info && <InfoTip id={info} className="ml-2" />}
        </h3>
        {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {actions}
    </div>
    <div className="mt-4">{children}</div>
  </div>
);

const Tile = ({ label, info, value, note }) => (
  <div className="rounded-lg bg-dark-800 p-4">
    <p className="text-xs text-gray-400 flex items-center">
      {label}
      {info && <InfoTip id={info} className="ml-1.5" />}
    </p>
    <p className="text-2xl font-semibold text-gray-100">{value}</p>
    {note && <p className="text-xs text-gray-500">{note}</p>}
  </div>
);

const Income = ({ data }) => {
  const [unit, setUnit] = useState("month");
  const received = useMemo(
    () => (unit === "month" ? data.monthly : data.yearly).map((r) => ({ time: r.period, value: r.gross })),
    [data, unit],
  );
  const expected = useMemo(
    () => (unit === "month" ? data.calendar.map((m) => ({ time: m.month, value: m.amount })) : []),
    [data, unit],
  );
  const toggle = (
    <div className="flex rounded-lg bg-dark-800 p-0.5 text-xs">
      {[
        ["month", "Monthly"],
        ["year", "Yearly"],
      ].map(([value, label]) => (
        <button
          key={value}
          type="button"
          onClick={() => setUnit(value)}
          aria-pressed={unit === value}
          className={`px-3 py-1 rounded-md ${unit === value ? "bg-primary-600 text-white" : "text-gray-400"}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
  return (
    <Card
      title="Income"
      info="dividend_income"
      subtitle="Dividends received before tax, and the months ahead expected from what you hold now."
      actions={toggle}
    >
      <IncomeChart received={received} expected={expected} />
      <p className="mt-2 text-xs text-gray-500">
        <span className="inline-block w-2 h-2 rounded-sm bg-success-400 mr-1" />
        received
        {unit === "month" && (
          <>
            <span className="inline-block w-2 h-2 rounded-sm bg-sky-400/60 ml-3 mr-1" />
            expected
          </>
        )}
      </p>
    </Card>
  );
};

const Calendar = ({ data }) => {
  const money = useMoney();
  return (
    <Card
      title="Expected payments"
      info="dividend_expected"
      subtitle="Each dividend of the last 12 months, repeated a year later for the shares you hold now. Dates are estimates."
    >
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {data.calendar.map((m) => (
          <div key={m.month} className={`rounded-lg bg-dark-800 p-3 ${m.amount ? "" : "opacity-50"}`}>
            <p className="text-xs text-gray-400">{monthName(m.month)}</p>
            <p className="text-lg font-semibold text-gray-100">{money(m.amount)}</p>
            <ul className="mt-1 space-y-0.5">
              {m.payments.map((p) => (
                <li key={`${p.asset_id}-${p.day}`} className="flex justify-between text-xs text-gray-500">
                  <span className="truncate">{p.symbol}</span>
                  <span>{money(p.amount)}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Card>
  );
};

const Holdings = ({ data }) => {
  const money = useMoney();
  return (
    <Card
      title="Paying holdings"
      info="yield_on_cost"
      subtitle="Dividend per share over the last 12 months, as a yield on today's price and on what you paid."
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-dark-700">
              <th className="py-2 font-medium">Holding</th>
              <th className="text-right font-medium">Shares</th>
              <th className="text-right font-medium">Per share, 12 m</th>
              <th className="text-right font-medium">Next 12 m</th>
              <th className="text-right font-medium">Yield</th>
              <th className="text-right font-medium">On cost</th>
              <th className="text-right font-medium">
                <span className="inline-flex items-center">
                  Growth
                  <InfoTip id="dividend_growth" className="ml-1" />
                </span>
              </th>
              <th className="text-right font-medium">Received</th>
            </tr>
          </thead>
          <tbody>
            {data.holdings.map((h) => (
              <tr key={h.asset_id} className="border-b border-dark-800">
                <td className="py-2">
                  <p className="font-medium text-gray-100">{h.symbol}</p>
                  <p className="text-xs text-gray-500 truncate max-w-[14rem]">
                    {h.per_share_12m ? `last ${day(h.last_dividend)}` : `none since ${day(h.last_dividend)}`}
                    {h.source === "payments" && " · from your payments"}
                  </p>
                </td>
                <td className="text-right text-gray-300">{formatQuantity(h.quantity)}</td>
                <td className="text-right text-gray-300">{money(h.per_share_12m)}</td>
                <td className="text-right text-gray-100">{money(h.expected_12m)}</td>
                <td className="text-right text-gray-300">{pct(h.current_yield_pct)}</td>
                <td className="text-right text-gray-300">{pct(h.yield_on_cost_pct)}</td>
                <td className={`text-right ${getChangeColor(h.growth_pct)}`}>
                  {h.growth_pct == null ? "—" : formatPercentage(h.growth_pct, { precision: 1 })}
                </td>
                <td className="text-right text-gray-300">{money(h.received_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.no_dividends.length > 0 && (
        <p className="mt-3 text-xs text-gray-500">No dividends on record: {data.no_dividends.join(", ")}</p>
      )}
    </Card>
  );
};

// Dividend income: received, expected and per holding (core/domain/dividends.py)
const PortfolioDividends = ({ portfolio }) => {
  const money = useMoney();
  const { data, isPending, isError } = useDividends(portfolio?.id);
  const { received, expected } = data ?? {};

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-100 flex items-center">
          <Coins className="w-5 h-5 mr-2 text-primary-400" />
          Dividends
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          What your holdings pay you, what to expect over the next year, and whether the payouts are growing.
        </p>
      </div>
      {isPending ? (
        <LoadingSpinner centered text="Adding up dividends…" />
      ) : isError ? (
        <p className="text-sm text-warning-400">Dividends could not be loaded.</p>
      ) : !received.payments && !data.holdings.length ? (
        <div className="card p-6 text-sm text-gray-400">No dividends received yet, and none of your holdings pays one.</div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Tile
              label="Received, last 12 months"
              value={money(received.net_12m)}
              note={`${money(received.gross_12m)} before tax`}
            />
            <Tile
              label="Expected, next 12 months"
              info="dividend_expected"
              value={money(expected.gross_12m)}
              note={
                expected.tax_rate_pct
                  ? `about ${money(expected.net_12m)} after ${pct(expected.tax_rate_pct)} tax`
                  : "no tax withheld on your payments so far"
              }
            />
            <Tile
              label="Portfolio yield"
              info="yield_on_cost"
              value={pct(expected.yield_pct)}
              note={`${pct(expected.yield_on_cost_pct)} on what you paid for the payers`}
            />
            <Tile
              label="Received in total"
              value={money(received.net)}
              note={
                received.first
                  ? `${received.payments} payments since ${day(received.first)}, ${money(received.gross)} before tax`
                  : "No payments yet"
              }
            />
          </div>
          <Income data={data} />
          {data.calendar.length > 0 && <Calendar data={data} />}
          {data.holdings.length > 0 && <Holdings data={data} />}
        </>
      )}
    </div>
  );
};

export default PortfolioDividends;
