from datetime import datetime, timezone
from typing import Optional, NamedTuple

from dateutil.relativedelta import relativedelta


class PeriodType:
    """Standard period types for calculations."""

    LAST_3_MONTHS = "3m"
    LAST_6_MONTHS = "6m"
    LAST_1_YEAR = "1y"
    LAST_2_YEARS = "2y"
    LAST_3_YEARS = "3y"
    LAST_5_YEARS = "5y"
    YTD = "ytd"
    INCEPTION = "inception"

    @classmethod
    def get_start_date(
            cls, period: str, base_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Get start date for a given period using proper calendar calculations."""
        if base_date is None:
            base_date = datetime.now(timezone.utc)

        if period == cls.LAST_3_MONTHS:
            return base_date - relativedelta(months=3)
        elif period == cls.LAST_6_MONTHS:
            return base_date - relativedelta(months=6)
        elif period == cls.LAST_1_YEAR:
            return base_date - relativedelta(years=1)
        elif period == cls.LAST_2_YEARS:
            return base_date - relativedelta(years=2)
        elif period == cls.LAST_3_YEARS:
            return base_date - relativedelta(years=3)
        elif period == cls.LAST_5_YEARS:
            return base_date - relativedelta(years=5)
        elif period == cls.YTD:
            return datetime(base_date.year, 1, 1, tzinfo=timezone.utc)
        elif period == cls.INCEPTION:
            return None  # No start date filter
        else:
            raise ValueError(f"Unknown period type: {period}")


class CashFlow(NamedTuple):
    """Represents a cash flow with date and amount."""

    date: datetime
    amount: float  # Positive for inflows, negative for outflows
