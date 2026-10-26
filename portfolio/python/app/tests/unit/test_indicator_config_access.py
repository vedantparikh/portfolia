"""Saved indicator configurations: private ones stay private."""

import pytest

from core.auth.dependencies import get_current_user, get_optional_current_user
from core.database.models import User
from core.database.models.analysis_configuration import AnalysisConfiguration
from main import app

URL = "/api/v1/statistical-indicators"


@pytest.fixture
def configs(test_db):
    owner = User(email="owner@example.com", username="owner", password_hash="x")
    other = User(email="peer@example.com", username="peer", password_hash="x")
    test_db.add_all([owner, other])
    test_db.flush()
    indicators = [{"indicator_name": "rsi_indicator", "parameters": {"window": 9}}]
    private = AnalysisConfiguration(
        user_id=owner.id, name="Mine", indicators=indicators, is_public=False, tags=[]
    )
    public = AnalysisConfiguration(
        user_id=owner.id, name="Shared", indicators=indicators, is_public=True, tags=[]
    )
    test_db.add_all([private, public])
    test_db.commit()
    return owner, other, private, public


def _as(user):
    app.dependency_overrides[get_optional_current_user] = lambda: user
    app.dependency_overrides[get_current_user] = lambda: user


def test_private_configuration_is_hidden_from_others(client, configs):
    owner, other, private, public = configs

    _as(None)
    assert client.get(f"{URL}/configurations/{private.id}").status_code == 404
    assert client.get(f"{URL}/configurations/{public.id}").status_code == 200
    _as(other)
    assert client.get(f"{URL}/configurations/{private.id}").status_code == 404
    _as(owner)
    assert client.get(f"{URL}/configurations/{private.id}").json()["name"] == "Mine"


def test_calculate_cannot_use_someone_elses_private_configuration(
    client, configs, monkeypatch
):
    import pandas as pd

    from core.services.market_data_service import MarketDataService

    owner, other, private, _ = configs

    async def prices(
        self, symbol, period="max", interval="1d", start_date=None, end_date=None
    ):
        index = pd.date_range("2025-01-01", periods=60, freq="D")
        return pd.DataFrame(
            {
                "Date": index,
                "Open": 1.0,
                "High": 1.0,
                "Low": 1.0,
                "Close": 1.0,
                "Volume": 1.0,
            }
        )

    monkeypatch.setattr(MarketDataService, "fetch_ticker_data", prices)
    _as(other)

    response = client.post(
        f"{URL}/calculate", json={"symbol": "ACME", "configuration_id": private.id}
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == (
        f"Configuration {private.id} not found"
    )
