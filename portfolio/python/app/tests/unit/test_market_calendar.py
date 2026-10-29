from datetime import date, datetime, timezone

from core.domain.market_calendar import (
    NEW_YORK,
    early_closes,
    holidays,
    market_status,
)


def test_nyse_holidays_2026():
    assert holidays(2026) == {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 4, 3),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
    assert early_closes(2026) == {date(2026, 11, 27), date(2026, 12, 24)}


def test_observed_days_move_off_weekends():
    assert date(2027, 6, 18) in holidays(2027)
    assert date(2027, 12, 24) in holidays(2027)
    assert date(2027, 12, 24) not in early_closes(2027)
    assert date(2022, 1, 1) not in holidays(2022)
    assert date(2021, 12, 31) not in holidays(2021)
    assert date(2023, 1, 2) in holidays(2023)
    assert date(2025, 7, 3) in early_closes(2025)
    assert date(2021, 6, 18) not in holidays(2021)


def ny(*args):
    return datetime(*args, tzinfo=NEW_YORK)


def test_open_during_the_session():
    status = market_status(ny(2026, 10, 29, 10, 0).astimezone(timezone.utc))
    assert status["is_open"] is True
    assert status["next_close"] == "2026-10-29T16:00:00-04:00"
    assert status["next_open"] == "2026-10-30T09:30:00-04:00"


def test_closed_on_a_holiday_until_the_next_session():
    status = market_status(ny(2026, 11, 26, 11, 0))
    assert status["is_open"] is False
    assert status["next_open"] == "2026-11-27T09:30:00-05:00"
    assert status["next_close"] == "2026-11-27T13:00:00-05:00"


def test_closed_after_an_early_close_and_over_the_weekend():
    status = market_status(ny(2026, 11, 27, 13, 0))
    assert status["is_open"] is False
    assert status["next_open"] == "2026-11-30T09:30:00-05:00"


def test_before_the_open():
    status = market_status(ny(2026, 10, 29, 9, 29))
    assert status["is_open"] is False
    assert status["next_open"] == "2026-10-29T09:30:00-04:00"
    assert status["next_close"] == "2026-10-29T16:00:00-04:00"
