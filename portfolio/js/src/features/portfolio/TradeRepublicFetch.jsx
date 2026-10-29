import { useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";

import { apiErrorMessage } from "../../shared/api/client";
import { formatDateTime } from "../../utils/formatters";
import { portfolioAPI } from "./api";
import { portfolioKeys, usePytrSyncAvailability } from "./queries";
import { fetchSummary } from "./tradeRepublic";

const CONFIRM_POLL_MS = 2000;

export default function TradeRepublicFetch() {
  const queryClient = useQueryClient();
  const { data: tr } = usePytrSyncAvailability();
  const [step, setStep] = useState(null);
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [code, setCode] = useState("");
  const [login, setLogin] = useState(null);
  const [busy, setBusy] = useState(false);
  const previous = useRef(tr?.fetch_status);
  const running = tr?.fetch_status === "running";

  useEffect(() => {
    const now = tr?.fetch_status;
    if (previous.current === "running" && now && now !== "running") {
      if (now === "succeeded") {
        toast.success(`Trade Republic: ${fetchSummary(tr.fetch_report)}`);
        queryClient.invalidateQueries({ queryKey: portfolioKeys.all });
      } else {
        toast.error(tr.fetch_report?.error || "The fetch from Trade Republic failed");
      }
    }
    previous.current = now;
  }, [tr, queryClient]);

  const startFetch = useCallback(async () => {
    try {
      const result = await portfolioAPI.fetchFromTradeRepublic();
      previous.current = result.fetch_status;
      queryClient.setQueryData(portfolioKeys.pytrAvailability, result);
    } catch (error) {
      toast.error(apiErrorMessage(error, "Could not start the fetch"));
      queryClient.invalidateQueries({ queryKey: portfolioKeys.pytrAvailability });
    }
  }, [queryClient]);

  const confirmed = useCallback(() => {
    setStep(null);
    setLogin(null);
    setCode("");
    startFetch();
  }, [startFetch]);

  useEffect(() => {
    if (step !== "confirm" || !login || login.needs_code) return undefined;
    let stopped = false;
    let timer;
    const deadline = Date.now() + login.countdown * 1000;
    const tick = async () => {
      try {
        const result = await portfolioAPI.confirmTradeRepublicLogin(null);
        if (stopped) return;
        if (result.confirmed) {
          confirmed();
          return;
        }
      } catch (error) {
        if (!stopped) {
          toast.error(apiErrorMessage(error, "The Trade Republic login failed"));
          setStep(null);
        }
        return;
      }
      if (Date.now() > deadline) {
        toast.error("The Trade Republic login timed out");
        setStep(null);
        return;
      }
      timer = setTimeout(tick, CONFIRM_POLL_MS);
    };
    timer = setTimeout(tick, CONFIRM_POLL_MS);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [step, login, confirmed]);

  if (!tr?.available) return null;

  const onFetch = () => (tr.connected ? startFetch() : setStep("login"));

  const submitLogin = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      setLogin(await portfolioAPI.startTradeRepublicLogin(phone.replace(/\s/g, ""), pin));
      setPin("");
      setStep("confirm");
    } catch (error) {
      toast.error(apiErrorMessage(error, "The Trade Republic login failed"));
    } finally {
      setBusy(false);
    }
  };

  const submitCode = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await portfolioAPI.confirmTradeRepublicLogin(code);
      if (result.confirmed) confirmed();
    } catch (error) {
      toast.error(apiErrorMessage(error, "The code was not accepted"));
      setStep(null);
    } finally {
      setBusy(false);
    }
  };

  const last = tr.fetch_finished_at
    ? `Last fetch ${formatDateTime(tr.fetch_finished_at)}: ${fetchSummary(tr.fetch_report)}`
    : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <span className="text-sm text-gray-400">
          {running ? "Fetching from Trade Republic…" : tr.session_expired ? "Trade Republic login ended" : last}
        </span>
        <button
          type="button"
          className="btn-primary flex items-center gap-2"
          onClick={onFetch}
          disabled={running || step !== null}
        >
          <Download size={16} className={running ? "animate-pulse" : ""} />
          <span>Fetch from Trade Republic</span>
        </button>
      </div>
      {step === "login" && (
        <form onSubmit={submitLogin} className="flex flex-wrap items-end justify-end gap-2 text-sm">
          <label className="flex flex-col gap-1 text-gray-400">
            Phone
            <input
              className="input-field w-48"
              type="tel"
              autoComplete="tel"
              placeholder="+49151…"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
            />
          </label>
          <label className="flex flex-col gap-1 text-gray-400">
            PIN
            <input
              className="input-field w-24"
              type="password"
              inputMode="numeric"
              autoComplete="off"
              maxLength={4}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Log in
          </button>
          <button type="button" className="btn-secondary" onClick={() => setStep(null)}>
            Cancel
          </button>
        </form>
      )}
      {step === "confirm" && login?.needs_code && (
        <form onSubmit={submitCode} className="flex flex-wrap items-end justify-end gap-2 text-sm">
          <label className="flex flex-col gap-1 text-gray-400">
            Code from your authenticator app
            <input
              className="input-field w-36"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value.trim())}
              required
            />
          </label>
          <button type="submit" className="btn-primary" disabled={busy}>
            Confirm
          </button>
        </form>
      )}
      {step === "confirm" && login && !login.needs_code && (
        <p className="text-sm text-gray-300 text-right">
          Confirm the login in your Trade Republic app. Your PIN is not stored.
        </p>
      )}
    </div>
  );
}
