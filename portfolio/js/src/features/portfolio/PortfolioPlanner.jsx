import { PiggyBank } from "lucide-react";
import { useState } from "react";

import { useMoney } from "../../hooks/useMoney";
import InfoTip from "../../shared/ui/InfoTip";
import LoadingSpinner from "../../shared/ui/Spinner";
import {
  formatDate,
  formatPercentage,
  formatQuantity,
  getChangeColor,
} from "../../utils/formatters.jsx";
import GoalChart from "./GoalChart";
import { useGoalProjection, useInvestPlan, useSavingsPlans } from "./queries";

const day = (d) => formatDate(`${d}T12:00:00`);
const pct = (v) => formatPercentage(v, { showSign: false, precision: 1, defaultValue: "0.0%" });
const inTenYears = () => {
  const d = new Date();
  d.setFullYear(d.getFullYear() + 10);
  return d.toISOString().slice(0, 10);
};
const RHYTHM = {
  weekly: "weekly · 4× a month",
  "every two weeks": "every two weeks · 2× a month",
  monthly: "monthly",
  quarterly: "quarterly",
};
const RETURNS = [
  ["5", "Cautious, 5% a year"],
  ["7", "Long-run, 7% a year"],
  ["history", "Benchmark history"],
];

const Card = ({ title, info, subtitle, children }) => (
  <div className="card p-6">
    <h3 className="text-lg font-semibold text-gray-100 flex items-center">
      {title}
      {info && <InfoTip id={info} className="ml-2" />}
    </h3>
    {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    <div className="mt-4">{children}</div>
  </div>
);

const Field = ({ label, children }) => (
  <label className="flex flex-col gap-1 text-xs text-gray-400">
    {label}
    {children}
  </label>
);

const inputClass =
  "w-full rounded-lg border border-gray-600 bg-dark-800 px-3 py-2 text-sm text-gray-100 focus:outline-hidden focus:ring-2 focus:ring-primary-500";

const InvestNewMoney = ({ portfolio }) => {
  const money = useMoney();
  const [draft, setDraft] = useState({ amount: "500", min: "1" });
  const [applied, setApplied] = useState({ amount: 500, min: 1 });
  const { data, isPending, isError, isFetching } = useInvestPlan(portfolio.id, applied.amount, applied.min);
  const buys = data?.buys.filter((b) => b.amount > 0) ?? [];
  const submit = (event) => {
    event.preventDefault();
    const amount = Number(draft.amount);
    if (amount > 0) setApplied({ amount, min: Math.max(0, Number(draft.min) || 0) });
  };

  return (
    <Card
      title="Invest new money"
      info="buy_only_rebalancing"
      subtitle="Where new money should go to move back toward your targets, without selling anything (selling realises gains and tax)."
    >
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3 mb-4">
        <Field label={`Amount (${money.currency})`}>
          <input
            type="number"
            min="1"
            step="any"
            value={draft.amount}
            onChange={(e) => setDraft({ ...draft, amount: e.target.value })}
            className={`${inputClass} w-36`}
          />
        </Field>
        <Field label="Smallest order">
          <input
            type="number"
            min="0"
            step="any"
            value={draft.min}
            onChange={(e) => setDraft({ ...draft, min: e.target.value })}
            className={`${inputClass} w-28`}
          />
        </Field>
        <button type="submit" className="btn-primary px-4 py-2 text-sm">
          Plan
        </button>
      </form>
      {isPending ? (
        <LoadingSpinner centered />
      ) : isError ? (
        <p className="text-sm text-gray-400">The plan could not be calculated.</p>
      ) : (
        <div className={isFetching ? "opacity-60" : ""}>
          {data.mode === "current_weights" && (
            <p className="mb-3 rounded-lg bg-dark-800 px-3 py-2 text-xs text-warning-400">
              This portfolio has no targets, so the money is split in proportion to what you hold now. Set targets in
              Holdings Detail → Allocations to steer it toward the mix you want.
            </p>
          )}
          {data.untargeted_value > 0 && (
            <p className="mb-3 text-xs text-gray-500">
              {money(data.untargeted_value)} in holdings without a target is left out of the weights.
            </p>
          )}
          {data.unpriced.length > 0 && (
            <p className="mb-3 text-xs text-gray-500">No price today, skipped: {data.unpriced.join(", ")}.</p>
          )}
          {buys.length === 0 ? (
            <p className="text-sm text-gray-400">Nothing to buy: no holding is below its target share.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[620px] text-sm">
                <thead className="text-xs text-gray-500 border-b border-dark-700">
                  <tr>
                    <th className="text-left font-normal py-2">Holding</th>
                    <th className="text-right font-normal">Buy</th>
                    <th className="text-right font-normal">≈ Shares</th>
                    <th className="text-right font-normal">Weight now</th>
                    <th className="text-right font-normal">After</th>
                    <th className="text-right font-normal">Target</th>
                  </tr>
                </thead>
                <tbody>
                  {buys.map((b) => (
                    <tr key={b.asset_id} className="border-b border-dark-800">
                      <td className="py-2">
                        <p className="font-medium text-gray-100">{b.symbol}</p>
                        <p className="text-xs text-gray-500">{b.name}</p>
                      </td>
                      <td className="text-right font-medium text-gray-100">{money(b.amount)}</td>
                      <td className="text-right text-gray-300">
                        {b.shares == null ? "—" : formatQuantity(b.shares)}
                      </td>
                      <td className="text-right text-gray-300">{pct(b.weight_before_pct)}</td>
                      <td className="text-right text-gray-100">{pct(b.weight_after_pct)}</td>
                      <td className="text-right text-gray-400">{pct(b.target_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

const SavingsPlans = ({ portfolio, plans }) => {
  const money = useMoney();
  const { data, isPending, isError } = plans;

  return (
    <Card
      title="Savings plans"
      info="savings_plans"
      subtitle="Found from your purchases: the same holding bought on a steady rhythm. Worth today = the plan's shares at today's price."
    >
      {isPending ? (
        <LoadingSpinner centered />
      ) : isError ? (
        <p className="text-sm text-gray-400">Savings plans could not be loaded.</p>
      ) : data.plans.length === 0 ? (
        <p className="text-sm text-gray-400">
          No recurring purchases found in {portfolio.name}. A plan shows up after three purchases of the same amount of
          the same holding on a weekly, two-weekly, monthly or quarterly rhythm.
        </p>
      ) : (
        <>
          <p className="mb-3 text-sm text-gray-300">
            Active plans invest <span className="font-semibold text-gray-100">{money(data.monthly_total)}</span> a month.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="text-xs text-gray-500 border-b border-dark-700">
                <tr>
                  <th className="text-left font-normal py-2">Holding</th>
                  <th className="text-left font-normal">Rhythm</th>
                  <th className="text-right font-normal">Amount now</th>
                  <th className="text-right font-normal">Per month</th>
                  <th className="text-left font-normal pl-4">Since</th>
                  <th className="text-right font-normal">Invested</th>
                  <th className="text-right font-normal">Worth today</th>
                  <th className="text-left font-normal pl-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.plans.map((plan) => {
                  const gain = plan.value_now == null ? null : (plan.value_now / plan.invested - 1) * 100;
                  return (
                    <tr
                      key={`${plan.asset_id}-${plan.first}`}
                      className={`border-b border-dark-800 ${plan.active ? "" : "opacity-60"}`}
                    >
                      <td className="py-2">
                        <p className="font-medium text-gray-100">{plan.symbol}</p>
                        <p className="text-xs text-gray-500 truncate max-w-[14rem]">{plan.name}</p>
                      </td>
                      <td className="text-gray-300">{RHYTHM[plan.rhythm] ?? plan.rhythm}</td>
                      <td className="text-right text-gray-100">
                        {money(plan.amount)}
                        {plan.previous_amount != null && (
                          <p className="text-xs text-gray-500">from {money(plan.previous_amount)}</p>
                        )}
                      </td>
                      <td className="text-right text-gray-300">{money(plan.monthly_amount)}</td>
                      <td className="pl-4 text-gray-300">
                        {day(plan.first)}
                        <span className="text-xs text-gray-500"> · {plan.executions}×</span>
                      </td>
                      <td className="text-right text-gray-300">{money(plan.invested)}</td>
                      <td className="text-right">
                        {plan.value_now == null ? (
                          <span className="text-gray-500">sold</span>
                        ) : (
                          <>
                            <span className="text-gray-100">{money(plan.value_now)}</span>
                            <span className={`ml-1.5 text-xs ${getChangeColor(gain)}`}>
                              {formatPercentage(gain, { precision: 1 })}
                            </span>
                          </>
                        )}
                      </td>
                      <td className="pl-4">
                        {plan.active ? (
                          <span className="text-success-400">active</span>
                        ) : (
                          <span className="text-gray-400">stopped {day(plan.last)}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Card>
  );
};

const Goal = ({ portfolio, plans }) => {
  const money = useMoney();
  const planned = plans.data?.monthly_total;
  const [draft, setDraft] = useState({ target: "100000", date: inTenYears(), monthly: "", returns: "7" });
  const [applied, setApplied] = useState(null);
  const goal = applied ?? {
    target: 100000,
    targetDate: draft.date,
    monthly: null,
    annualReturn: 7,
  };
  const { data, isPending, isError, error, isFetching } = useGoalProjection(portfolio.id, goal);
  const submit = (event) => {
    event.preventDefault();
    setApplied({
      target: Number(draft.target),
      targetDate: draft.date,
      monthly: draft.monthly === "" ? null : Number(draft.monthly),
      annualReturn: draft.returns === "history" ? null : Number(draft.returns),
    });
  };
  const reached = data?.probability_pct;
  const need = (v) => (v === 0 ? "none" : money(v));

  return (
    <Card
      title="Goal"
      info="goal_projection"
      subtitle="Where today's value and your monthly saving could lead, simulated from the benchmark's real ups and downs."
    >
      <form onSubmit={submit} className="grid grid-cols-2 lg:grid-cols-5 items-end gap-3 mb-5">
        <Field label={`Goal (${money.currency})`}>
          <input
            type="number"
            min="1"
            step="any"
            value={draft.target}
            onChange={(e) => setDraft({ ...draft, target: e.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="By">
          <input
            type="date"
            value={draft.date}
            onChange={(e) => setDraft({ ...draft, date: e.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="Monthly saving">
          <input
            type="number"
            min="0"
            step="any"
            placeholder={planned != null ? `${Math.round(planned)} (your plans)` : ""}
            value={draft.monthly}
            onChange={(e) => setDraft({ ...draft, monthly: e.target.value })}
            className={inputClass}
          />
        </Field>
        <Field label="Return assumption">
          <select
            value={draft.returns}
            onChange={(e) => setDraft({ ...draft, returns: e.target.value })}
            className={inputClass}
          >
            {RETURNS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <button type="submit" className="btn-primary px-4 py-2 text-sm">
          Project
        </button>
      </form>

      {isPending ? (
        <LoadingSpinner centered text="Simulating…" />
      ) : isError ? (
        <p className="text-sm text-warning-400">
          {error?.response?.data?.error?.message ?? "The projection could not be calculated."}
        </p>
      ) : (
        <div className={isFetching ? "opacity-60" : ""}>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="rounded-lg bg-dark-800 p-4">
              <p className="text-xs text-gray-400">Chance of reaching {money(data.target, { notation: "compact" })}</p>
              <p className={`text-2xl font-semibold ${reached >= 75 ? "text-success-400" : reached >= 50 ? "text-warning-400" : "text-danger-400"}`}>
                {formatPercentage(reached, { showSign: false, precision: 0, defaultValue: "0%" })}
              </p>
            </div>
            <div className="rounded-lg bg-dark-800 p-4">
              <p className="text-xs text-gray-400">Typical outcome ({day(data.target_date)})</p>
              <p className="text-2xl font-semibold text-gray-100">{money(data.final["50"], { notation: "compact" })}</p>
              <p className="text-xs text-gray-500">
                1 in 10 below {money(data.final["10"], { notation: "compact" })}, 1 in 10 above{" "}
                {money(data.final["90"], { notation: "compact" })}
              </p>
            </div>
            <div className="rounded-lg bg-dark-800 p-4">
              <p className="text-xs text-gray-400">You put in</p>
              <p className="text-2xl font-semibold text-gray-100">{money(data.deposits, { notation: "compact" })}</p>
              <p className="text-xs text-gray-500">
                {money(data.start_value, { notation: "compact" })} today + {money(data.monthly)} × {data.months} months
              </p>
            </div>
            <div className="rounded-lg bg-dark-800 p-4">
              <p className="text-xs text-gray-400">Monthly saving needed</p>
              {data.required_monthly["90"] === 0 ? (
                <>
                  <p className="text-2xl font-semibold text-success-400">None</p>
                  <p className="text-xs text-gray-500">Today&apos;s value reaches the goal on 9 in 10 paths without more saving</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-semibold text-gray-100">
                    {data.required_monthly["50"] === 0 ? "None" : money(data.required_monthly["50"])}
                  </p>
                  <p className="text-xs text-gray-500">
                    for an even chance; {need(data.required_monthly["75"])} for 3 in 4,{" "}
                    {need(data.required_monthly["90"])} for 9 in 10
                  </p>
                </>
              )}
            </div>
          </div>
          <GoalChart points={data.points} goal={data.target} />
          <p className="mt-3 text-xs text-gray-500">
            {formatQuantity(data.basis.paths, { precision: 0 })} simulated paths built from 12-month stretches of {data.basis.name}&apos;s
            monthly returns since {day(data.basis.first_month)} ({data.basis.months_of_history} months), whose average
            was {pct(data.basis.history_annual_pct)} a year
            {data.basis.assumed_annual_pct != null &&
              `; shifted to average ${pct(data.basis.assumed_annual_pct)} a year, keeping the same swings`}
            . Before inflation, costs and tax. The solid line is the middle outcome; the dotted lines are the 10th, 25th,
            75th and 90th percentiles.
          </p>
        </div>
      )}
    </Card>
  );
};

// Planning new money: the buy-only split, detected savings plans and the goal (core/domain/planner.py)
const PortfolioPlanner = ({ portfolio }) => {
  const plans = useSavingsPlans(portfolio?.id);
  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-100 flex items-center">
          <PiggyBank className="w-5 h-5 mr-2 text-primary-400" />
          Planner
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          Decide where new money goes, see your savings plans, and check whether your saving reaches your goal. These are
          calculations, not advice.
        </p>
      </div>
      <InvestNewMoney portfolio={portfolio} />
      <SavingsPlans portfolio={portfolio} plans={plans} />
      <Goal portfolio={portfolio} plans={plans} />
    </div>
  );
};

export default PortfolioPlanner;
