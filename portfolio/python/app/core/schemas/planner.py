"""Next-euro planner responses (core/domain/planner.py). Money in the portfolio currency, percent units."""

from datetime import date
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PlannedBuy(BaseModel):
    asset_id: int
    symbol: str
    name: Optional[str] = None
    amount: float
    shares: Optional[float] = Field(None, description="amount ÷ today's price")
    price: Optional[float] = None
    value_before: float
    value_after: float
    weight_before_pct: float
    weight_after_pct: float
    target_pct: float


class InvestPlanResponse(BaseModel):
    """Where new money goes to move toward the targets without selling."""

    portfolio_id: int
    currency: str
    amount: float
    min_amount: float
    mode: Literal["targets", "current_weights"] = Field(
        ..., description="current_weights when the portfolio has no targets"
    )
    buys: List[PlannedBuy]
    untargeted_value: float = Field(
        ..., description="Value of holdings without a target, left out of the weights"
    )
    unpriced: List[str] = Field(
        default_factory=list, description="Targeted holdings without a price, skipped"
    )


class SavingsPlanRow(BaseModel):
    asset_id: int
    symbol: str
    name: Optional[str] = None
    rhythm: Literal["weekly", "every two weeks", "monthly", "quarterly"]
    executions_per_month: float = Field(
        ..., description="Weekly = 4: broker plans run on four fixed days a month"
    )
    amount: float = Field(..., description="Median of the last three executions")
    previous_amount: Optional[float] = Field(
        None, description="The amount before the latest change, if it changed"
    )
    monthly_amount: float = Field(..., description="amount × executions_per_month")
    executions: int
    first: date
    last: date
    invested: float
    quantity: float = Field(
        ..., description="Shares bought by the plan, in today's units"
    )
    value_now: Optional[float] = Field(
        None, description="Those shares at today's price, ignoring later sales"
    )
    active: bool


class SavingsPlansResponse(BaseModel):
    portfolio_id: int
    currency: str
    plans: List[SavingsPlanRow]
    monthly_total: float = Field(..., description="Active plans, per month")


class GoalPoint(BaseModel):
    date: date
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


class GoalBasis(BaseModel):
    symbol: str
    name: str
    first_month: date
    months_of_history: int
    history_annual_pct: float = Field(
        ..., description="The history's own average, per year"
    )
    assumed_annual_pct: Optional[float] = Field(
        None, description="Average the simulation used instead; null = the history's"
    )
    paths: int


class GoalProjectionResponse(BaseModel):
    """Simulated range of the portfolio's value at the goal date (block bootstrap)."""

    portfolio_id: int
    currency: str
    target: float
    target_date: date
    months: int
    start_value: float
    monthly: float
    deposits: float = Field(..., description="Today's value plus every monthly amount")
    final: Dict[str, float] = Field(..., description="Percentile (10…90) → value")
    probability_pct: Optional[float] = None
    required_monthly: Dict[str, float] = Field(
        ..., description="Monthly amount reaching the goal on 50/75/90 % of paths"
    )
    points: List[GoalPoint]
    basis: GoalBasis
