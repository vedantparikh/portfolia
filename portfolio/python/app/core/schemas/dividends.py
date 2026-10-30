"""Dividend income responses (core/domain/dividends.py). Money in the portfolio currency, percent units."""

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DividendsReceived(BaseModel):
    gross: float = Field(..., description="Before tax withheld")
    tax: float
    net: float
    gross_12m: float = Field(..., description="Paid in the last 12 months")
    net_12m: float
    payments: int
    first: Optional[date] = None


class DividendsExpected(BaseModel):
    gross_12m: float = Field(
        ..., description="Last 12 months' dividends per share × shares held now"
    )
    net_12m: float = Field(..., description="gross_12m less tax at tax_rate_pct")
    tax_rate_pct: float = Field(
        ..., description="Tax withheld ÷ gross over the last 12 months' payments"
    )
    yield_pct: Optional[float] = Field(None, description="gross_12m ÷ portfolio value")
    yield_on_cost_pct: Optional[float] = Field(
        None, description="gross_12m ÷ cost of the paying holdings"
    )


class DividendIncome(BaseModel):
    period: date = Field(..., description="First day of the month or year")
    gross: float
    tax: float
    net: float
    payments: int


class ExpectedDividend(BaseModel):
    asset_id: int
    symbol: str
    day: date
    per_share: float
    amount: float


class DividendMonth(BaseModel):
    month: date
    amount: float
    payments: List[ExpectedDividend]


class DividendPerShareYear(BaseModel):
    year: int
    per_share: float


class DividendHolding(BaseModel):
    asset_id: int
    symbol: str
    name: Optional[str] = None
    quantity: float
    source: Literal["market", "payments"] = Field(
        ...,
        description="market: the listing's ex-dates; payments: your own payments per share",
    )
    per_share_12m: float
    expected_12m: float
    current_yield_pct: Optional[float] = None
    yield_on_cost_pct: Optional[float] = None
    growth_pct: Optional[float] = Field(
        None, description="Last complete year's dividend per share vs the year before"
    )
    per_share_by_year: List[DividendPerShareYear]
    last_dividend: date
    pay_lag_days: int = Field(..., description="Median days from ex-date to payment")
    received_total: float
    received_12m: float


class DividendsResponse(BaseModel):
    portfolio_id: int
    currency: str
    received: DividendsReceived
    expected: DividendsExpected
    monthly: List[DividendIncome]
    yearly: List[DividendIncome]
    calendar: List[DividendMonth]
    holdings: List[DividendHolding]
    no_dividends: List[str] = Field(
        default_factory=list, description="Held listings without any dividend on record"
    )
