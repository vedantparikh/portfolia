"""Which daily bar is the previous close for today's P&L."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import pandas as pd


def previous_session_close(bars: pd.Series, now: datetime) -> Optional[Decimal]:
    """Close of the last session that started before the current one.

    A bar dated today in the bar's own timezone is still the current session.
    Naive bars are dated as printed and compared with `now` in UTC.
    """
    bars = bars.dropna().sort_index()
    if bars.empty:
        return None
    today = _as_of(bars.index, now)
    completed = [
        value
        for value, session in zip(bars.to_numpy(), _session_dates(bars.index))
        if session < today
    ]
    if not completed:
        return None
    return Decimal(str(completed[-1]))


def _as_of(index: pd.DatetimeIndex, now: datetime) -> date:
    moment = pd.Timestamp(now)
    if index.tz is not None:
        if moment.tzinfo is None:
            moment = moment.tz_localize("UTC")
        return moment.tz_convert(index.tz).date()
    if moment.tzinfo is not None:
        return moment.tz_convert("UTC").date()
    return moment.date()


def _session_dates(index: pd.DatetimeIndex):
    if index.tz is not None:
        return [stamp.date() for stamp in index]
    return [pd.Timestamp(stamp).date() for stamp in index]
