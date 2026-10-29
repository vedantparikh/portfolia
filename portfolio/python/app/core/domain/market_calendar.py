"""
NYSE trading calendar: regular hours 9:30–16:00 New York time on weekdays,
except the exchange's full holidays, and 13:00 closes on its early-close days.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
OPEN = time(9, 30)
CLOSE = time(16, 0)
EARLY_CLOSE = time(13, 0)


def _easter(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed(day: date) -> date:
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def holidays(year: int) -> set[date]:
    days = {
        _nth_weekday(year, 1, 0, 3),
        _nth_weekday(year, 2, 0, 3),
        _easter(year) - timedelta(days=2),
        _last_weekday(year, 5, 0),
        _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1),
        _nth_weekday(year, 11, 3, 4),
        _observed(date(year, 12, 25)),
    }
    # A Saturday New Year is not moved back into the old year
    if date(year, 1, 1).weekday() != 5:
        days.add(_observed(date(year, 1, 1)))
    if year >= 2022:
        days.add(_observed(date(year, 6, 19)))
    return days


def early_closes(year: int) -> set[date]:
    days = {_nth_weekday(year, 11, 3, 4) + timedelta(days=1)}
    for day in (date(year, 7, 3), date(year, 12, 24)):
        if day.weekday() < 4:
            days.add(day)
    return days


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in holidays(day.year)


def session(day: date) -> Optional[Tuple[datetime, datetime]]:
    """Open and close of the day's session in New York time, None when closed all day."""
    if not is_trading_day(day):
        return None
    close = EARLY_CLOSE if day in early_closes(day.year) else CLOSE
    return (
        datetime.combine(day, OPEN, NEW_YORK),
        datetime.combine(day, close, NEW_YORK),
    )


def market_status(now: datetime) -> dict:
    """Whether the market is open at `now` (aware), and its next open and close."""
    now = now.astimezone(NEW_YORK)
    day = now.date()
    today = session(day)
    is_open = bool(today and today[0] <= now < today[1])
    next_close = today[1] if today and now < today[1] else None
    next_open = today[0] if today and now < today[0] else None
    while next_open is None or next_close is None:
        day += timedelta(days=1)
        upcoming = session(day)
        if upcoming is None:
            continue
        next_open = next_open or upcoming[0]
        next_close = next_close or upcoming[1]
    return {
        "is_open": is_open,
        "current_time_et": now.isoformat(),
        "next_open": next_open.isoformat(),
        "next_close": next_close.isoformat(),
        "timezone": "America/New_York",
    }
