import { Landmark } from "lucide-react";
import { useEffect, useState } from "react";

import { useMoney } from "../../hooks/useMoney";
import InfoTip from "../../shared/ui/InfoTip";
import LoadingSpinner from "../../shared/ui/Spinner";
import { formatDate, formatPercentage, formatQuantity, getChangeColor } from "../../utils/formatters.jsx";
import { useAllowanceSplit, useGermanTax } from "./queries";

const day = (d) => formatDate(`${d}T12:00:00`);
const pct = (v, precision = 2) => (v == null ? "—" : formatPercentage(v, { showSign: false, precision }));
const KIND = { share: "share", fund: "fund (70% taxed)", other: "other" };
const storageKey = (id) => `portfolia.tax.${id}`;
const loadSettings = (id) => {
  try {
    return { allowance: "", joint: false, church: "0", ...JSON.parse(localStorage.getItem(storageKey(id)) || "{}") };
  } catch {
    return { allowance: "", joint: false, church: "0" };
  }
};

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

const Tile = ({ label, info, value, note, tone = "text-gray-100" }) => (
  <div className="rounded-lg bg-dark-800 p-4">
    <p className="text-xs text-gray-400 flex items-center">
      {label}
      {info && <InfoTip id={info} className="ml-1.5" />}
    </p>
    <p className={`text-2xl font-semibold ${tone}`}>{value}</p>
    {note && <p className="text-xs text-gray-500">{note}</p>}
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

const Signed = ({ value }) => {
  const money = useMoney();
  if (!value) return <span className="text-gray-500">—</span>;
  return <span className={getChangeColor(value)}>{money(value)}</span>;
};

const Year = ({ data }) => {
  const money = useMoney();
  const s = data.settlement;
  const carried = s.share_loss_carried + s.other_loss_carried;
  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile
          label="Capital income"
          info="loss_pots"
          value={money(s.income)}
          note={`shares ${money(s.share_net)}, everything else ${money(s.other_net)}`}
        />
        <Tile
          label="Allowance used"
          info="sparerpauschbetrag"
          value={money(s.allowance_used)}
          note={`of ${money(s.allowance)}; ${money(s.allowance_left)} left`}
          tone={s.allowance_left > 0 ? "text-success-400" : "text-gray-100"}
        />
        <Tile
          label="Estimated tax"
          value={money(s.tax)}
          note={`your broker withheld ${money(s.withheld)} (net of refunds)`}
        />
        <Tile
          label="Losses carried forward"
          info="loss_pots"
          value={money(carried)}
          note={`shares ${money(s.share_loss_carried)}, other ${money(s.other_loss_carried)}`}
          tone={carried < 0 ? "text-warning-400" : "text-gray-100"}
        />
      </div>
      {data.items.length > 0 && (
        <Card
          title={`What counts in ${data.year}`}
          info="teilfreistellung"
          subtitle="Per holding, before tax. Funds are taxed on 70% (Teilfreistellung). A fund sale is reduced by the Vorabpauschalen already taxed on it."
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-dark-700">
                  <th className="py-2 font-medium">Holding</th>
                  <th className="text-right font-medium">Sales</th>
                  <th className="text-right font-medium">Vorabpauschale credit</th>
                  <th className="text-right font-medium">Dividends</th>
                  <th className="text-right font-medium">Vorabpauschale</th>
                  <th className="text-right font-medium">Taxable</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.asset_id} className="border-b border-dark-800">
                    <td className="py-2">
                      <p className="font-medium text-gray-100">{r.symbol}</p>
                      <p className="text-xs text-gray-500">{KIND[r.kind]}</p>
                    </td>
                    <td className="text-right"><Signed value={r.sale_gain} /></td>
                    <td className="text-right text-gray-300">{r.vorabpauschale_credit ? money(-r.vorabpauschale_credit) : "—"}</td>
                    <td className="text-right text-gray-300">{r.dividends ? money(r.dividends) : "—"}</td>
                    <td className="text-right text-gray-300">{r.vorabpauschale ? money(r.vorabpauschale) : "—"}</td>
                    <td className="text-right"><Signed value={r.taxable} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(s.share_loss_in < 0 || s.other_loss_in < 0) && (
            <p className="mt-3 text-xs text-gray-500">
              Carried in from last year: shares {money(s.share_loss_in)}, other {money(s.other_loss_in)}.
            </p>
          )}
        </Card>
      )}
    </>
  );
};

const VorabpauschaleCard = ({ vp }) => {
  const money = useMoney();
  if (!vp.funds.length) return null;
  return (
    <Card
      title={`Vorabpauschale ${vp.year}`}
      info="vorabpauschale"
      subtitle={`${vp.estimate ? "Estimate with today's prices; " : ""}charged around ${day(vp.due)} on your funds, at a Basiszins of ${pct(vp.basiszins_pct)}.`}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-dark-700">
              <th className="py-2 font-medium">Fund</th>
              <th className="text-right font-medium">Shares</th>
              <th className="text-right font-medium">Start of year</th>
              <th className="text-right font-medium">{vp.estimate ? "Now" : "End of year"}</th>
              <th className="text-right font-medium">Distributed</th>
              <th className="text-right font-medium">Per share</th>
              <th className="text-right font-medium">Vorabpauschale</th>
            </tr>
          </thead>
          <tbody>
            {vp.funds.map((f) => (
              <tr key={f.asset_id} className="border-b border-dark-800">
                <td className="py-2 font-medium text-gray-100">{f.symbol}</td>
                <td className="text-right text-gray-300">{formatQuantity(f.shares)}</td>
                <td className="text-right text-gray-300">{money(f.start_price)}</td>
                <td className="text-right text-gray-300">{money(f.end_price)}</td>
                <td className="text-right text-gray-300">{money(f.distributions)}</td>
                <td className="text-right text-gray-300">{money(f.per_share)}</td>
                <td className="text-right text-gray-100">{money(f.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm text-gray-300">
        {money(vp.amount)} in total, {money(vp.taxable)} taxable: about {money(vp.tax)} tax if no allowance is left
        in January. Keep that much cash in the account.
      </p>
    </Card>
  );
};

const Harvest = ({ data }) => {
  const money = useMoney();
  const s = data.settlement;
  return (
    <Card
      title="Before the year ends"
      info="tax_loss_harvesting"
      subtitle="Selling realises a gain or loss in this year's pots. Share losses only offset share gains; other losses offset everything."
    >
      {data.harvest.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-dark-700">
                <th className="py-2 font-medium">Holding with a loss</th>
                <th className="text-right font-medium">Unrealised</th>
                <th className="text-right font-medium">Counts as</th>
                <th className="text-right font-medium">Tax saved this year</th>
              </tr>
            </thead>
            <tbody>
              {data.harvest.map((h) => (
                <tr key={h.asset_id} className="border-b border-dark-800">
                  <td className="py-2">
                    <p className="font-medium text-gray-100">{h.symbol}</p>
                    <p className="text-xs text-gray-500">{KIND[h.kind]}</p>
                  </td>
                  <td className="text-right"><Signed value={h.unrealized} /></td>
                  <td className="text-right text-gray-300">{money(h.taxable)}</td>
                  <td className="text-right text-gray-100">{h.tax_saved > 0.005 ? money(h.tax_saved) : "none"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-gray-400">No holding is below what you paid.</p>
      )}
      {s.allowance_left > 0 && data.tax_free_gains.length > 0 && (
        <p className="mt-3 text-sm text-gray-300">
          {money(s.allowance_left)} of your allowance is unused this year. Selling and buying back holdings with a
          gain ({data.tax_free_gains.slice(0, 3).map((g) => g.symbol).join(", ")}) realises up to that much tax-free
          and raises their cost basis.
        </p>
      )}
    </Card>
  );
};

const History = ({ data }) => {
  const money = useMoney();
  return (
    <Card title="Year by year" subtitle="Each year as your broker settles it, carrying losses forward. Compare the estimate with what was withheld.">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-dark-700">
              <th className="py-2 font-medium">Year</th>
              <th className="text-right font-medium">Capital income</th>
              <th className="text-right font-medium">Allowance used</th>
              <th className="text-right font-medium">Estimated tax</th>
              <th className="text-right font-medium">Withheld</th>
              <th className="text-right font-medium">Losses carried</th>
            </tr>
          </thead>
          <tbody>
            {data.history.map((h) => (
              <tr key={h.year} className="border-b border-dark-800">
                <td className="py-2 text-gray-100">{h.year}</td>
                <td className="text-right text-gray-300">{money(h.income)}</td>
                <td className="text-right text-gray-300">{money(h.allowance_used)}</td>
                <td className="text-right text-gray-100">{money(h.tax)}</td>
                <td className="text-right text-gray-300">{money(h.withheld)}</td>
                <td className="text-right text-gray-300">{money(h.share_loss_carried + h.other_loss_carried)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

const AllowanceSplit = ({ year, joint }) => {
  const money = useMoney();
  const { data } = useAllowanceSplit(year, joint);
  if (!data || data.portfolios.length < 2) return null;
  return (
    <Card
      title="Freistellungsauftrag across your portfolios"
      info="sparerpauschbetrag"
      subtitle={`Capital income per euro portfolio in ${data.year}, and a split of the ${money(data.allowance)} allowance that covers the largest first. Portfolios at the same broker share one order.`}
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-dark-700">
            <th className="py-2 font-medium">Portfolio</th>
            <th className="text-right font-medium">Capital income</th>
            <th className="text-right font-medium">Suggested order</th>
          </tr>
        </thead>
        <tbody>
          {data.portfolios.map((p) => (
            <tr key={p.portfolio_id} className="border-b border-dark-800">
              <td className="py-2 text-gray-100">{p.name}</td>
              <td className="text-right text-gray-300">{money(p.income)}</td>
              <td className="text-right text-gray-100">{money(p.suggested)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
};

// German tax view: the year as the bank settles it (core/domain/german_tax.py)
const PortfolioTax = ({ portfolio }) => {
  const [settings, setSettings] = useState(() => loadSettings(portfolio.id));
  const [year, setYear] = useState(null);
  useEffect(() => {
    setSettings(loadSettings(portfolio.id));
    setYear(null);
  }, [portfolio.id]);
  useEffect(() => {
    localStorage.setItem(storageKey(portfolio.id), JSON.stringify(settings));
  }, [portfolio.id, settings]);
  const query = {
    year,
    allowance: settings.allowance === "" ? null : Number(settings.allowance),
    joint: settings.joint,
    churchPct: Number(settings.church),
  };
  const { data, isPending, isError, error, isFetching } = useGermanTax(portfolio.id, query);
  const shownYear = data?.year;

  return (
    <div className="space-y-6">
      <div className="card p-6">
        <h2 className="text-xl font-semibold text-gray-100 flex items-center">
          <Landmark className="w-5 h-5 mr-2 text-primary-400" />
          German tax
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          Your capital income as a German bank settles it: allowance, loss pots, Vorabpauschale and what you could still
          do this year. An estimate for information, not tax advice.
        </p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
          <Field label="Year">
            <select
              value={shownYear ?? ""}
              onChange={(e) => setYear(Number(e.target.value))}
              className={inputClass}
            >
              {(data?.years ?? []).map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Freistellungsauftrag here (EUR)">
            <input
              type="number"
              min="0"
              step="any"
              placeholder={data ? `${Math.round(data.assumptions.allowance)} (full allowance)` : ""}
              value={settings.allowance}
              onChange={(e) => setSettings({ ...settings, allowance: e.target.value })}
              className={inputClass}
            />
          </Field>
          <Field label="Church tax">
            <select
              value={settings.church}
              onChange={(e) => setSettings({ ...settings, church: e.target.value })}
              className={inputClass}
            >
              <option value="0">None</option>
              <option value="8">8% (Bavaria, Baden-Württemberg)</option>
              <option value="9">9%</option>
            </select>
          </Field>
          <label className="flex items-center gap-2 text-sm text-gray-300 mt-5">
            <input
              type="checkbox"
              checked={settings.joint}
              onChange={(e) => setSettings({ ...settings, joint: e.target.checked })}
            />
            Jointly assessed (double allowance)
          </label>
        </div>
      </div>

      {isPending ? (
        <LoadingSpinner centered text="Settling the year…" />
      ) : isError ? (
        <p className="text-sm text-warning-400">
          {error?.response?.data?.error?.message ?? "The tax view could not be calculated."}
        </p>
      ) : (
        <div className={`space-y-6 ${isFetching ? "opacity-60" : ""}`}>
          <Year data={data} />
          <VorabpauschaleCard vp={data.vorabpauschale} />
          {data.year === data.years.at(-1) && <Harvest data={data} />}
          <History data={data} />
          <AllowanceSplit year={data.year} joint={settings.joint} />
          <p className="text-xs text-gray-500">
            Rate {pct(data.assumptions.rate_pct, 3)} (25% Abgeltungsteuer, 5.5% Soli
            {data.assumptions.church_pct ? `, ${data.assumptions.church_pct}% church tax` : ""}). Funds are treated as
            equity funds (30% Teilfreistellung). Not covered: foreign withholding tax credits, losses carried in from
            another bank, and interest.
            {data.excluded.length > 0 &&
              ` Crypto (${data.excluded.join(", ")}) is left out: it is taxed as a private sale, tax-free after a year.`}
          </p>
        </div>
      )}
    </div>
  );
};

export default PortfolioTax;
