from datetime import datetime, timezone
from typing import Dict, Optional, NamedTuple

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


def get_major_indices() -> Dict[str, str]:
    us_indexes = [
        {
            "name": "S&P 500",
            "symbol": "^GSPC"
        },
        {
            "name": "Dow Jones Industrial Average",
            "symbol": "^DJI"
        },
        {
            "name": "NASDAQ Composite",
            "symbol": "^IXIC"
        },
        {
            "name": "NASDAQ-100",
            "symbol": "^NDX"
        },
        {
            "name": "Russell 2000",
            "symbol": "^RUT"
        },
        {
            "name": "CBOE Volatility Index (VIX)",
            "symbol": "^VIX"
        },
        {
            "name": "S&P 100",
            "symbol": "^OEX"
        },
        {
            "name": "S&P MidCap 400",
            "symbol": "^MID"
        },
        {
            "name": "Russell 1000",
            "symbol": "^RUI"
        },
        {
            "name": "Russell 3000",
            "symbol": "^RUA"
        },
        {
            "name": "NYSE COMPOSITE",
            "symbol": "^NYA"
        },
        {
            "name": "Dow Jones Transportation Average",
            "symbol": "^DJT"
        },
        {
            "name": "Dow Jones Utility Average",
            "symbol": "^DJU"
        }
    ]
    major_world_indexes = [
        # --- Americas ---
        {
            "name": "S&P/TSX Composite (Canada)",
            "symbol": "^GSPTSE"
        },
        {
            "name": "IBOVESPA (Brazil)",
            "symbol": "^BVSP"
        },
        {
            "name": "IPC (Mexico)",
            "symbol": "^MXX"
        },

        # --- Europe ---
        {
            "name": "FTSE 100 (UK)",
            "symbol": "^FTSE"
        },
        {
            "name": "DAX (Germany)",
            "symbol": "^GDAXI"
        },
        {
            "name": "CAC 40 (France)",
            "symbol": "^FCHI"
        },
        {
            "name": "STOXX Europe 600",
            "symbol": "^STOXX"
        },
        {
            "name": "IBEX 35 (Spain)",
            "symbol": "^IBEX"
        },
        {
            "name": "FTSE MIB (Italy)",
            "symbol": "^FTMIB"
        },
        {
            "name": "Swiss Market Index (SMI)",
            "symbol": "^SSMI"
        },
        {
            "name": "AEX (Netherlands)",
            "symbol": "^AEX"
        },

        # --- Asia / Pacific ---
        {
            "name": "Nikkei 225 (Japan)",
            "symbol": "^N225"
        },
        {
            "name": "Hang Seng Index (Hong Kong)",
            "symbol": "^HSI"
        },
        {
            "name": "SSE Composite (Shanghai)",
            "symbol": "000001.SS"
        },
        {
            "name": "Shenzhen Component",
            "symbol": "399001.SZ"
        },
        {
            "name": "KOSPI (South Korea)",
            "symbol": "^KS11"
        },
        {
            "name": "S&P/ASX 200 (Australia)",
            "symbol": "^AXJO"
        },
        {
            "name": "TAIEX (Taiwan)",
            "symbol": "^TWII"
        },
        {
            "name": "Straits Times Index (Singapore)",
            "symbol": "^STI"
        }
    ]
    india_indexes = [
        {
            "name": "NIFTY 50",
            "symbol": "^NSEI"
        },
        {
            "name": "BSE SENSEX",
            "symbol": "^BSESN"
        },
        {
            "name": "NIFTY Bank",
            "symbol": "^NSEBANK"
        },
        {
            "name": "India VIX",
            "symbol": "^NIFVIX"
        },
        {
            "name": "NIFTY Next 50",
            "symbol": "^NN50"
        },
        {
            "name": "NIFTY 100",
            "symbol": "^CNX100"
        },
        {
            "name": "NIFTY 500",
            "symbol": "^CRSLDX"
        },
        {
            "name": "NIFTY Midcap 100",
            "symbol": "^CNXMIDCAP"
        }
    ]

    return us_indexes + india_indexes + major_world_indexes