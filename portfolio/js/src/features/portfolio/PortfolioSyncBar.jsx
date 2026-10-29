import { useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";

import { apiErrorMessage } from "../../shared/api/client";
import { formatDateTime } from "../../utils/formatters";
import { portfolioAPI } from "./api";
import { portfolioKeys, usePortfolioSync } from "./queries";
import TradeRepublicFetch from "./TradeRepublicFetch";

function summarize(report) {
  if (!report) return "Not synced yet";
  const parts = [`${report.created} new`];
  if (report.failed) parts.push(`${report.failed} failed`);
  if (report.trade_priced?.length) parts.push(`${report.trade_priced.length} without market prices`);
  return parts.join(" · ");
}

export default function PortfolioSyncBar({ portfolio }) {
  const queryClient = useQueryClient();
  const { data: status } = usePortfolioSync(portfolio.id, !!portfolio.sync_source);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [tickers, setTickers] = useState({});
  const report = status?.report;

  const run = async (action, success) => {
    setBusy(true);
    try {
      const result = await action();
      queryClient.setQueryData(portfolioKeys.sync(portfolio.id), result);
      await queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
      toast.success(success(result.report));
    } catch (error) {
      toast.error(apiErrorMessage(error, "Sync failed"));
    } finally {
      setBusy(false);
    }
  };

  const syncNow = () =>
    run(
      () => portfolioAPI.runSync(portfolio.id),
      (r) => `Trade Republic: ${summarize(r)}`,
    );

  const map = (isin) =>
    run(
      () => portfolioAPI.mapSyncInstrument(portfolio.id, isin, tickers[isin] || ""),
      (r) => `Mapped ${isin}: ${summarize(r)}`,
    );

  return (
    <div className="card p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm">
          <p className="text-gray-100 font-medium">Synced with Trade Republic</p>
          <p className="text-gray-400">
            {status?.synced_at ? `Last import ${formatDateTime(status.synced_at)}` : "Not synced yet"}
            {status?.file_updated_at && ` · export from ${formatDateTime(status.file_updated_at)}`}
            {report && ` · ${summarize(report)}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {(report?.trade_priced?.length > 0 || report?.errors?.length > 0) && (
            <button type="button" className="btn-secondary flex items-center gap-1" onClick={() => setOpen(!open)}>
              Details {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
          <button type="button" className="btn-secondary flex items-center gap-2" onClick={syncNow} disabled={busy}>
            <RefreshCw size={16} className={busy ? "animate-spin" : ""} />
            <span>Import file</span>
          </button>
        </div>
      </div>
      <TradeRepublicFetch />
      {open && report && (
        <div className="space-y-3 text-sm">
          {report.trade_priced?.length > 0 && (
            <div>
              <p className="text-gray-400 mb-2">
                Yahoo has no prices for these securities (knock-outs, warrants), so they are valued at their own last trade. A redeemed knock-out is booked as sold at its redemption amount. Enter a Yahoo ticker to use market prices instead.
              </p>
              <ul className="space-y-2">
                {report.trade_priced.map((item) => (
                  <li key={item.isin} className="flex flex-wrap items-center gap-2">
                    <span className="text-gray-200 min-w-[14rem]">{item.name}</span>
                    <span className="text-gray-500">{item.isin}</span>
                    <input
                      aria-label={`Ticker for ${item.isin}`}
                      className="input-field w-36"
                      placeholder={item.suggested_symbol || "Ticker"}
                      value={tickers[item.isin] || ""}
                      onChange={(e) => setTickers({ ...tickers, [item.isin]: e.target.value.trim() })}
                    />
                    <button type="button" className="btn-secondary" disabled={busy || !tickers[item.isin]} onClick={() => map(item.isin)}>
                      Use ticker
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.errors?.length > 0 && (
            <ul className="text-danger-400 list-disc pl-5">
              {report.errors.map((e) => <li key={e}>{e}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
