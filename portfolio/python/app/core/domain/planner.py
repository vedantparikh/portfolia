"""
Planning new money: where to put it, which purchases recur, and where the
savings lead. Money in the portfolio currency; percent units (15.0).

- Buy-only split ("water-filling"): with targets t_i (normalised over the
  targeted holdings) and current values c_i, find the level L with
  Σ max(0, t_i·L − c_i) = amount and buy max(0, t_i·L − c_i) of each. The
  most underweight holdings are topped up first and all bought holdings end
  at the same fraction of their target; nothing is sold. Buys below
  `min_amount` are dropped and the amount split again over the rest.
- Savings plans: a holding's purchases on a steady rhythm (weekly, every two
  weeks, monthly, quarterly). Fee-free purchases are used when there are
  enough of them (broker savings plans are free); the plan is the latest run
  of purchases whose gaps fit the rhythm, allowing one skipped execution.
- Goal projection: monthly paths built from 12-month blocks of historical
  monthly returns (a block bootstrap keeps good and bad years together),
  contributions at the start of each month. A path ends at V0·G + C·A
  (G = growth, A = growth of one euro a month), so the monthly amount that
  reaches the goal on that path is (goal − V0·G) ÷ A. `with_annual_mean`
  moves the history's average to an assumed annual return and keeps its
  swings, so one strong stretch of history does not set the expectation.
"""

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class Buy:
    asset_id: int
    amount: float
    value_before: float
    value_after: float
    weight_before_pct: float
    weight_after_pct: float
    target_pct: float


def _water_fill(
    values: Mapping[int, float], targets: Mapping[int, float], amount: float
) -> Dict[int, float]:
    order = sorted(targets, key=lambda a: values.get(a, 0.0) / targets[a])
    weight = held = 0.0
    level = 0.0
    for k, asset_id in enumerate(order):
        weight += targets[asset_id]
        held += values.get(asset_id, 0.0)
        level = (amount + held) / weight
        following = order[k + 1] if k + 1 < len(order) else None
        if (
            following is None
            or level <= values.get(following, 0.0) / targets[following]
        ):
            break
    return {
        asset_id: max(0.0, targets[asset_id] * level - values.get(asset_id, 0.0))
        for asset_id in order
    }


def buy_only_split(
    values: Mapping[int, float],
    targets_pct: Mapping[int, float],
    amount: float,
    min_amount: float = 0.0,
) -> List[Buy]:
    """
    `values`: current value per holding; `targets_pct`: target percent per
    holding (any total, normalised here). Holdings without a target get
    nothing and are left out of the weights. Largest buy first.
    """
    targets = {a: t for a, t in targets_pct.items() if t > 0}
    total_target = sum(targets.values())
    if amount <= 0 or not targets:
        return []
    weights = {a: t / total_target for a, t in targets.items()}
    eligible = dict(weights)
    while True:
        norm = sum(eligible.values())
        split = _water_fill(values, {a: w / norm for a, w in eligible.items()}, amount)
        small = [a for a, x in split.items() if 0 < x < min_amount]
        if not small or len(eligible) == 1:
            break
        del eligible[min(small, key=lambda a: split[a])]

    before = sum(values.get(a, 0.0) for a in weights)
    after = before + sum(split.values())
    buys = [
        Buy(
            asset_id=a,
            amount=split.get(a, 0.0),
            value_before=values.get(a, 0.0),
            value_after=values.get(a, 0.0) + split.get(a, 0.0),
            weight_before_pct=values.get(a, 0.0) / before * 100 if before else 0.0,
            weight_after_pct=(values.get(a, 0.0) + split.get(a, 0.0)) / after * 100,
            target_pct=weights[a] * 100,
        )
        for a in weights
    ]
    return sorted(buys, key=lambda b: (-b.amount, b.asset_id))


@dataclass(frozen=True)
class Purchase:
    asset_id: int
    day: date
    amount: float
    quantity: float
    fee_free: bool


@dataclass(frozen=True)
class SavingsPlan:
    asset_id: int
    rhythm: str
    interval_days: float
    amount: float
    monthly_amount: float
    executions: int
    first: date
    last: date
    invested: float
    quantity: float
    active: bool


RHYTHMS = (
    ("weekly", 7.0, 5, 9),
    ("every two weeks", 14.0, 12, 17),
    ("monthly", 30.44, 25, 36),
    ("quarterly", 91.3, 80, 100),
)
DAYS_PER_MONTH = 30.44


def _rhythm(gap: float) -> Optional[tuple[str, float, int, int]]:
    return next((r for r in RHYTHMS if r[2] <= gap <= r[3]), None)


def detect_savings_plans(
    purchases: Sequence[Purchase], today: date, min_executions: int = 3
) -> List[SavingsPlan]:
    """Recurring purchases per holding, largest monthly amount first."""
    by_asset: Dict[int, List[Purchase]] = {}
    for p in purchases:
        by_asset.setdefault(p.asset_id, []).append(p)

    plans = []
    for asset_id, rows in by_asset.items():
        free = [p for p in rows if p.fee_free]
        rows = free if len(free) >= min_executions else rows
        days: Dict[date, List[Purchase]] = {}
        for p in rows:
            days.setdefault(p.day, []).append(p)
        dated = sorted(days.items())
        if len(dated) < min_executions:
            continue
        gaps = [(b[0] - a[0]).days for a, b in zip(dated, dated[1:])]
        rhythm = _rhythm(median(gaps[-12:]))
        if rhythm is None:
            continue
        name, interval, _, high = rhythm
        start = len(dated) - 1
        while start > 0 and gaps[start - 1] <= 2 * high:
            start -= 1
        run = dated[start:]
        if len(run) < min_executions:
            continue
        in_rhythm = sum(1 for g in gaps[start:] if _rhythm(g) == rhythm)
        if in_rhythm < 0.6 * len(gaps[start:]):
            continue
        amounts = [sum(p.amount for p in ps) for _, ps in run]
        amount = median(amounts[-3:])
        last = run[-1][0]
        plans.append(
            SavingsPlan(
                asset_id=asset_id,
                rhythm=name,
                interval_days=interval,
                amount=amount,
                monthly_amount=amount * DAYS_PER_MONTH / interval,
                executions=len(run),
                first=run[0][0],
                last=last,
                invested=sum(amounts),
                quantity=sum(p.quantity for _, ps in run for p in ps),
                active=(today - last).days <= 1.5 * interval + 4,
            )
        )
    return sorted(plans, key=lambda p: (not p.active, -p.monthly_amount, p.asset_id))


@dataclass(frozen=True)
class Projection:
    months: int
    paths: int
    deposits: float
    percentiles: Dict[int, List[float]]
    final: Dict[int, float]
    probability_pct: Optional[float]
    required_monthly: Dict[int, float]


PERCENTILES = (10, 25, 50, 75, 90)


def monthly_returns(closes: Sequence[float]) -> np.ndarray:
    """Month-end closes → monthly returns (fractions)."""
    values = np.asarray(closes, dtype=float)
    values = values[~np.isnan(values)]
    returns: np.ndarray = values[1:] / values[:-1] - 1
    return returns


def with_annual_mean(returns: np.ndarray, annual_pct: float) -> np.ndarray:
    """Monthly returns shifted so they average (1 + annual)^(1/12) − 1 a month."""
    target = (1 + annual_pct / 100) ** (1 / 12) - 1
    shifted: np.ndarray = returns - returns.mean() + target
    return shifted


def project_goal(
    start_value: float,
    monthly: float,
    months: int,
    history: np.ndarray,
    goal: Optional[float] = None,
    paths: int = 2000,
    block: int = 12,
    seed: int = 0,
) -> Projection:
    """
    Value after each month on `paths` simulated paths. `final` and the
    per-month `percentiles` are the 10th…90th percentile values;
    `required_monthly[p]` reaches `goal` on p % of the paths.
    """
    if months < 1:
        raise ValueError("The goal date must be at least a month away")
    if len(history) < block:
        raise ValueError("Not enough return history to simulate")
    rng = np.random.default_rng(seed)
    blocks = -(-months // block)
    starts = rng.integers(0, len(history), size=(paths, blocks))
    index = (starts[:, :, None] + np.arange(block)) % len(history)
    returns = history[index.reshape(paths, -1)[:, :months]]
    growth = 1 + returns
    # Growth from the start of month m to the end: one euro paid in at month m
    tail = np.cumprod(growth[:, ::-1], axis=1)[:, ::-1]
    total_growth = tail[:, 0]
    annuity = tail.sum(axis=1)

    values = np.empty((paths, months))
    value = np.full(paths, float(start_value))
    for m in range(months):
        value = (value + monthly) * growth[:, m]
        values[:, m] = value
    final = values[:, -1]

    required: Dict[int, float] = {}
    probability = None
    if goal is not None:
        needed = np.clip((goal - start_value * total_growth) / annuity, 0, None)
        required = {p: float(np.percentile(needed, p)) for p in (50, 75, 90)}
        probability = float((final >= goal).mean() * 100)
    return Projection(
        months=months,
        paths=paths,
        deposits=float(start_value + monthly * months),
        percentiles={
            p: [float(v) for v in np.percentile(values, p, axis=0)] for p in PERCENTILES
        },
        final={p: float(np.percentile(final, p)) for p in PERCENTILES},
        probability_pct=probability,
        required_monthly=required,
    )
