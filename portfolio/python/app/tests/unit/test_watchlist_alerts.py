"""Watchlist alerts: rules, notify-once-per-crossing, worker step, API."""

from decimal import Decimal as D

import pytest

from core.auth.dependencies import get_current_user
from core.database.models import User
from core.database.models.watchlist import (
    Watchlist,
    WatchlistAlert,
    WatchlistItem,
    WatchlistPerformance,
)
from core.domain.alerts import PRICE_HIGH, PRICE_LOW, check_alerts
from core.schemas.watchlist import WatchlistItemCreate
from core.services.watchlist_service import WatchlistService
from main import app


def _holding(checks):
    return {c.alert_type: c.holds for c in checks}


def test_high_and_low_fire_at_the_threshold():
    assert _holding(check_alerts(D("100"), None, D("100"), D("90"), None)) == {
        PRICE_HIGH: True,
        PRICE_LOW: False,
    }
    assert _holding(check_alerts(D("90"), None, D("100"), D("90"), None)) == {
        PRICE_HIGH: False,
        PRICE_LOW: True,
    }


def test_percent_change_fires_on_a_move_either_way():
    up = check_alerts(D("110"), D("100"), None, None, D("10"))
    down = check_alerts(D("89"), D("100"), None, None, D("10"))
    small = check_alerts(D("105"), D("100"), None, None, D("10"))

    assert [(c.condition, c.holds) for c in up] == [("above", True)]
    assert [(c.condition, c.holds) for c in down] == [("below", True)]
    assert [c.holds for c in small] == [False]


def test_unset_or_meaningless_thresholds_are_not_checked():
    assert check_alerts(D("50"), None, None, None, D("10")) == []
    assert check_alerts(D("50"), D("40"), None, None, D("0")) == []
    assert check_alerts(D("50"), D("40"), None, None, None) == []


class Prices:
    def __init__(self):
        self.now = {}

    async def get_current_prices(self, symbols):
        return {s: self.now[s] for s in symbols if s in self.now}


@pytest.fixture
def watch(test_db):
    user = User(email="alerts@example.com", username="alerts", password_hash="x")
    test_db.add(user)
    test_db.flush()
    watchlist = Watchlist(user_id=user.id, name="Tech")
    test_db.add(watchlist)
    test_db.flush()
    item = WatchlistItem(
        watchlist_id=watchlist.id,
        symbol="ACME",
        added_price=D("80"),
        alert_price_high=D("100"),
    )
    test_db.add(item)
    test_db.commit()
    service = WatchlistService(test_db)
    service.market_data_service = Prices()
    return user, item, service


async def _step(service, price):
    service.market_data_service.now["ACME"] = D(price)
    return await service.refresh_prices_and_alerts()


def _events(test_db, item):
    return (
        test_db.query(WatchlistAlert)
        .filter(WatchlistAlert.watchlist_item_id == item.id)
        .order_by(WatchlistAlert.id)
        .all()
    )


@pytest.mark.asyncio
async def test_alert_fires_once_per_crossing(test_db, watch):
    _, item, service = watch

    steps = [await _step(service, p) for p in ("90", "101", "105", "95", "102")]

    assert [s["triggered"] for s in steps] == [0, 1, 0, 0, 1]
    events = _events(test_db, item)
    assert [(e.triggered_value, e.is_active) for e in events] == [
        (D("101"), False),
        (D("102"), True),
    ]
    assert item.current_price == D("102")
    assert item.price_change_percent_since_added == D("27.5")


@pytest.mark.asyncio
async def test_new_threshold_beyond_the_price_fires_once(test_db, watch):
    _, item, service = watch
    await _step(service, "120")
    item.alert_price_high = D("110")
    test_db.commit()

    assert (await _step(service, "120"))["triggered"] == 1
    assert (await _step(service, "121"))["triggered"] == 0
    assert [(e.threshold_value, e.is_active) for e in _events(test_db, item)] == [
        (D("100"), False),
        (D("110"), True),
    ]


@pytest.mark.asyncio
async def test_disabling_alerts_closes_open_ones(test_db, watch):
    _, item, service = watch
    await _step(service, "101")
    item.alerts_enabled = False
    test_db.commit()

    assert (await _step(service, "130"))["triggered"] == 0
    assert [e.is_active for e in _events(test_db, item)] == [False]


@pytest.mark.asyncio
async def test_percent_move_fires_and_one_price_row_per_day(test_db, watch):
    _, item, service = watch
    item.alert_price_high = None
    item.alert_price_change_percent = D("20")
    test_db.commit()

    await _step(service, "90")
    await _step(service, "60")

    (event,) = _events(test_db, item)
    assert (event.alert_type, event.condition) == ("percent_change", "below")
    rows = (
        test_db.query(WatchlistPerformance).filter_by(watchlist_item_id=item.id).all()
    )
    assert [r.price for r in rows] == [D("60")]


@pytest.mark.asyncio
async def test_symbols_without_a_price_are_skipped(test_db, watch):
    _, item, service = watch

    result = await service.refresh_prices_and_alerts()

    assert (result["symbols"], result["priced"], result["updated"]) == (1, 0, 0)
    assert item.current_price is None


@pytest.mark.asyncio
async def test_alerts_api_lists_and_acknowledges_only_your_alerts(
    client, test_db, watch
):
    user, item, service = watch
    await _step(service, "101")
    other = User(email="other@example.com", username="other", password_hash="x")
    test_db.add(other)
    test_db.commit()

    app.dependency_overrides[get_current_user] = lambda: other
    assert client.get("/api/v1/watchlists/alerts").json() == {
        "unread_count": 0,
        "alerts": [],
    }
    assert client.post("/api/v1/watchlists/alerts/acknowledge", json={}).json() == {
        "acknowledged": 0
    }

    app.dependency_overrides[get_current_user] = lambda: user
    listed = client.get("/api/v1/watchlists/alerts").json()
    assert listed["unread_count"] == 1
    (alert,) = listed["alerts"]
    assert (alert["symbol"], alert["watchlist_name"], alert["still_true"]) == (
        "ACME",
        "Tech",
        True,
    )
    ack = client.post(
        "/api/v1/watchlists/alerts/acknowledge", json={"alert_ids": [alert["id"]]}
    )
    assert ack.json() == {"acknowledged": 1}
    assert client.get("/api/v1/watchlists/alerts?unread_only=true").json() == {
        "unread_count": 0,
        "alerts": [],
    }


@pytest.mark.asyncio
async def test_worker_pass_uses_its_own_session(
    monkeypatch, test_db_session_factory, watch
):
    import workers.run as worker

    _, item, service = watch
    prices = Prices()
    prices.now["ACME"] = D("150")
    monkeypatch.setattr(worker, "SessionLocal", test_db_session_factory)
    monkeypatch.setattr(
        "core.services.watchlist_service.MarketDataService", lambda: prices
    )

    result = await worker.run_once()

    assert (result["updated"], result["triggered"]) == (1, 1)


def test_saving_a_crossed_threshold_records_an_alert_immediately(
    client, test_db, watch
):
    user, item, _ = watch
    item.current_price = D("150")
    item.alert_price_high = None
    test_db.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    url = f"/api/v1/watchlists/{item.watchlist_id}/items/{item.id}"

    assert client.put(url, json={"alert_price_high": "140"}).status_code == 200
    assert [
        (e.threshold_value, e.is_active, e.triggered_value)
        for e in _events(test_db, item)
    ] == [(D("140"), True, D("150"))]

    assert client.put(url, json={"alert_price_high": "140"}).status_code == 200
    assert len(_events(test_db, item)) == 1

    assert client.put(url, json={"alert_price_high": None}).status_code == 200
    assert [e.is_active for e in _events(test_db, item)] == [False]


def test_item_update_saves_and_clears_alert_thresholds(client, test_db, watch):
    user, item, _ = watch
    app.dependency_overrides[get_current_user] = lambda: user
    url = f"/api/v1/watchlists/{item.watchlist_id}/items/{item.id}"

    saved = client.put(
        url,
        json={
            "alert_price_high": "120.5",
            "alert_price_low": "70",
            "alert_price_change_percent": "15",
            "alerts_enabled": False,
        },
    )
    assert saved.status_code == 200
    test_db.refresh(item)
    assert (
        item.alert_price_high,
        item.alert_price_low,
        item.alert_price_change_percent,
        item.alerts_enabled,
    ) == (D("120.5"), D("70"), D("15"), False)

    client.put(url, json={"alert_price_high": None})
    test_db.refresh(item)
    assert (item.alert_price_high, item.alert_price_low) == (None, D("70"))
    assert client.put(url, json={"alert_price_low": "-1"}).status_code == 422


@pytest.mark.asyncio
async def test_adding_an_item_records_its_first_price(test_db, watch):
    user, item, service = watch

    async def price(symbol):
        return D("42")

    service.market_data_service.get_current_price = price
    added = await service.add_item_to_watchlist(
        item.watchlist_id, user.id, WatchlistItemCreate(symbol="beta")
    )

    assert (added.symbol, added.added_price, added.sort_order) == (
        "BETA",
        D("42"),
        item.sort_order + 1,
    )
    history = (
        test_db.query(WatchlistPerformance)
        .filter(WatchlistPerformance.watchlist_item_id == added.id)
        .all()
    )
    assert [p.price for p in history] == [D("42")]
