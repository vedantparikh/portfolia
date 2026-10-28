import { AlertTriangle, CheckCircle, HelpCircle, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { accountStatementsAPI } from "./api";

const BATCH = 10;

const majorCurrency = (code) => {
  if (!code) return "";
  if (code === "GBp" || code.toUpperCase() === "GBX") return "GBP";
  if (code.toUpperCase() === "ILA") return "ILS";
  return code.toUpperCase();
};

const STATUS = {
  existing: { label: "Your asset", icon: CheckCircle, tone: "text-success-400" },
  matched: { label: "Matched", icon: CheckCircle, tone: "text-success-400" },
  uncertain: { label: "Check", icon: AlertTriangle, tone: "text-warning-400" },
  unmatched: { label: "No match", icon: HelpCircle, tone: "text-gray-400" },
};

const InstrumentMappingPanel = ({ instruments, mapping, onChange, portfolioCurrency }) => {
  const [results, setResults] = useState({});
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const resolveAll = async () => {
      for (let i = 0; i < instruments.length && !cancelled; i += BATCH) {
        try {
          const { results: batch } = await accountStatementsAPI.resolveInstruments(
            instruments.slice(i, i + BATCH)
          );
          if (cancelled) return;
          setResults((prev) => ({
            ...prev,
            ...Object.fromEntries(batch.map((r) => [r.isin, r])),
          }));
          batch.forEach((r) => onChange(r.isin, null, r));
        } catch (error) {
          console.error("Instrument resolution failed:", error);
          setFailed(true);
        }
      }
    };
    resolveAll();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- resolve once per parsed file; onChange identity changes every render
  }, [instruments]);

  const resolved = Object.keys(results).length;
  const included = instruments.filter((i) => mapping[i.isin] && !mapping[i.isin].excluded);
  const rowsIncluded = included.reduce((n, i) => n + i.transaction_count, 0);
  const rowsTotal = instruments.reduce((n, i) => n + i.transaction_count, 0);

  return (
    <details open className="bg-gray-700/40 border border-gray-600 rounded-lg p-3 mb-4 text-sm">
      <summary className="cursor-pointer text-gray-200 font-medium">
        Map securities to listings · {included.length}/{instruments.length} included ({rowsIncluded}/
        {rowsTotal} rows)
        {resolved < instruments.length && !failed && (
          <span className="ml-2 text-gray-400">
            <Loader2 className="inline w-4 h-4 animate-spin mr-1" />
            matching {resolved}/{instruments.length}…
          </span>
        )}
      </summary>
      <p className="mt-2 text-gray-400">
        Each ISIN is matched to the Yahoo listing whose daily price range contains your actual
        trade prices. Pick another listing or type any Yahoo ticker; securities left out are not
        imported.
      </p>
      {failed && (
        <p className="mt-2 text-danger-400">Matching failed for some securities; enter a ticker or try again later.</p>
      )}
      <div className="mt-3 max-h-80 overflow-auto">
        <table className="w-full">
          <thead className="text-xs text-gray-400 text-left">
            <tr>
              <th className="py-1 pr-2">Security</th>
              <th className="py-1 pr-2">Rows</th>
              <th className="py-1 pr-2">Match</th>
              <th className="py-1 pr-2">Listing</th>
              <th className="py-1">Import</th>
            </tr>
          </thead>
          <tbody>
            {instruments.map((instrument) => {
              const result = results[instrument.isin];
              const choice = mapping[instrument.isin];
              const status = result ? STATUS[result.status] : null;
              const Icon = status?.icon;
              const chosen = result?.candidates.find((c) => c.symbol === choice?.symbol);
              return (
                <tr key={instrument.isin} className="border-t border-gray-700/60 align-top">
                  <td className="py-1.5 pr-2">
                    <div className="text-gray-200">{instrument.name}</div>
                    <div className="text-xs text-gray-500">{instrument.isin}</div>
                  </td>
                  <td className="py-1.5 pr-2 text-gray-300">{instrument.transaction_count}</td>
                  <td className="py-1.5 pr-2">
                    {status ? (
                      <span className={`inline-flex items-center gap-1 ${status.tone}`}>
                        <Icon className="w-4 h-4" />
                        {status.label}
                        {chosen?.match_percent != null && ` · ${chosen.match_percent}%`}
                      </span>
                    ) : (
                      <Loader2 className="w-4 h-4 animate-spin text-gray-500" />
                    )}
                  </td>
                  <td className="py-1.5 pr-2">
                    {result && (
                      <div className="flex flex-col gap-1">
                        {result.candidates.length > 0 && (
                          <select
                            className="input-field py-1 text-sm"
                            value={chosen ? choice.symbol : ""}
                            onChange={(e) =>
                              onChange(instrument.isin, {
                                symbol: e.target.value,
                                asset_id: null,
                                currency: result.candidates.find((c) => c.symbol === e.target.value)
                                  ?.currency,
                                excluded: !e.target.value,
                              })
                            }
                          >
                            <option value="">Choose a listing…</option>
                            {result.candidates.map((c) => (
                              <option key={c.symbol} value={c.symbol}>
                                {c.symbol} · {c.exchange || "?"} · {c.currency || "?"}
                                {c.match_percent != null && ` · ${c.match_percent}% of ${c.fills_checked}`}
                              </option>
                            ))}
                          </select>
                        )}
                        {portfolioCurrency &&
                          choice?.currency &&
                          !choice.excluded &&
                          majorCurrency(choice.currency) !== majorCurrency(portfolioCurrency) && (
                            <p className="text-xs text-warning-400">
                              {choice.symbol} is quoted in {choice.currency}. Values are converted
                              into {portfolioCurrency}.
                            </p>
                          )}
                        <input
                          className="input-field py-1 text-sm"
                          placeholder="or type a Yahoo ticker"
                          value={choice?.symbol || ""}
                          onChange={(e) =>
                            onChange(instrument.isin, {
                              symbol: e.target.value.trim().toUpperCase(),
                              asset_id: null,
                              excluded: !e.target.value.trim(),
                            })
                          }
                        />
                      </div>
                    )}
                  </td>
                  <td className="py-1.5">
                    <input
                      type="checkbox"
                      className="w-4 h-4"
                      checked={Boolean(choice && !choice.excluded)}
                      disabled={!choice?.symbol}
                      onChange={(e) => onChange(instrument.isin, { ...choice, excluded: !e.target.checked })}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
};

export default InstrumentMappingPanel;
