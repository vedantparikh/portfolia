"""German tax view responses (core/domain/german_tax.py). Euros, percent units. An estimate, not tax advice."""

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

TaxKind = Literal["share", "fund", "other"]


class TaxAssumptions(BaseModel):
    allowance: float = Field(..., description="Freistellungsauftrag at this bank")
    joint: bool
    church_pct: float
    rate_pct: float = Field(..., description="Abgeltungsteuer + Soli (+ church tax)")
    basiszins_pct: Optional[float] = None
    equity_fund_exemption_pct: float


class TaxSettlement(BaseModel):
    share_net: float = Field(..., description="Share sale gains less share sale losses")
    other_net: float = Field(
        ...,
        description="Everything else after Teilfreistellung: fund and other sales, dividends, Vorabpauschale",
    )
    share_loss_in: float = Field(
        ..., description="Share loss carried in from last year"
    )
    other_loss_in: float
    income: float = Field(
        ..., description="Taxable capital income before the allowance"
    )
    allowance: float
    allowance_used: float
    allowance_left: float
    taxable: float
    tax: float
    share_loss_carried: float = Field(..., description="Carried into next year (≤ 0)")
    other_loss_carried: float
    withheld: float = Field(
        ..., description="Tax the broker withheld this year, net of refunds"
    )


class TaxItem(BaseModel):
    asset_id: int
    symbol: str
    name: Optional[str] = None
    kind: TaxKind
    sale_gain: float
    vorabpauschale_credit: float = Field(
        ..., description="Vorabpauschalen already taxed on the sold fund shares"
    )
    dividends: float
    vorabpauschale: float = Field(..., description="Last year's, taxed in January")
    taxable: float


class TaxYear(BaseModel):
    year: int
    income: float
    allowance_used: float
    tax: float
    withheld: float
    share_loss_carried: float
    other_loss_carried: float


class VorabpauschaleFund(BaseModel):
    asset_id: int
    symbol: str
    name: Optional[str] = None
    kind: TaxKind
    shares: float
    start_price: float
    end_price: float = Field(..., description="Latest close while the year runs")
    distributions: float = Field(..., description="Per share in the year")
    per_share: float
    amount: float
    taxable: float


class Vorabpauschale(BaseModel):
    year: int
    basiszins_pct: Optional[float] = None
    estimate: bool = Field(..., description="True while the year is still running")
    due: date
    funds: List[VorabpauschaleFund]
    amount: float
    taxable: float
    tax: float = Field(..., description="At the rate, before any allowance left")


class HarvestCandidate(BaseModel):
    asset_id: int
    symbol: str
    name: Optional[str] = None
    kind: TaxKind
    unrealized: float
    taxable: float = Field(..., description="After Teilfreistellung for funds")
    tax_saved: float = Field(0.0, description="This year's tax less if sold today")


class GermanTaxResponse(BaseModel):
    portfolio_id: int
    currency: str
    year: int
    years: List[int]
    assumptions: TaxAssumptions
    settlement: TaxSettlement
    items: List[TaxItem]
    history: List[TaxYear]
    vorabpauschale: Vorabpauschale
    harvest: List[HarvestCandidate]
    tax_free_gains: List[HarvestCandidate]
    excluded: List[str] = Field(
        default_factory=list,
        description="Crypto: private sales (§ 23 EStG), not capital income",
    )


class AllowancePortfolio(BaseModel):
    portfolio_id: int
    name: str
    income: float
    suggested: float


class AllowanceSplitResponse(BaseModel):
    year: int
    allowance: float
    income: float
    portfolios: List[AllowancePortfolio]
