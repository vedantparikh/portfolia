"""Request session commits or rolls back, and portfolio ownership is one dependency."""

import ast
from pathlib import Path

import pytest
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from core.auth.dependencies import (
    get_current_active_user,
    get_current_user,
    get_current_verified_user,
    get_optional_current_user,
)
from core.database.connection import get_db
from core.database.models import Portfolio, User
from main import app

APP = Path(__file__).resolve().parents[2]
API = APP / "api"


class Base(DeclarativeBase):
    pass


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)


def _factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_get_db_commits_when_the_request_succeeds(monkeypatch):
    factory = _factory()
    monkeypatch.setattr("core.database.connection.SessionLocal", factory)
    gen = get_db()
    db = next(gen)
    db.add(Note(name="kept"))
    with pytest.raises(StopIteration):
        next(gen)

    assert factory().query(Note).one().name == "kept"


def test_get_db_rolls_back_when_the_request_fails(monkeypatch):
    factory = _factory()
    monkeypatch.setattr("core.database.connection.SessionLocal", factory)
    gen = get_db()
    db = next(gen)
    db.add(Note(name="gone"))
    with pytest.raises(RuntimeError):
        gen.throw(RuntimeError("fail"))

    assert factory().query(Note).count() == 0


def _login_as(user):
    for dependency in (
        get_current_user,
        get_current_active_user,
        get_current_verified_user,
        get_optional_current_user,
    ):
        app.dependency_overrides[dependency] = lambda: user


def test_owned_portfolio_is_visible_to_its_owner(client, test_db):
    user = User(email="owner@example.com", username="owner", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="Mine")
    test_db.add(portfolio)
    test_db.commit()
    _login_as(user)

    response = client.get(f"/api/v1/analytics/portfolios/{portfolio.id}/benchmarks")

    assert response.status_code == 200
    assert response.json() == []


def test_owned_portfolio_rejects_another_user(client, test_db):
    owner = User(email="owner2@example.com", username="owner2", password_hash="x")
    other = User(email="other@example.com", username="other", password_hash="x")
    test_db.add_all([owner, other])
    test_db.flush()
    portfolio = Portfolio(user_id=owner.id, name="Theirs")
    test_db.add(portfolio)
    test_db.commit()
    _login_as(other)

    response = client.get(f"/api/v1/analytics/portfolios/{portfolio.id}/benchmarks")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.json()["error"]["message"] == f"Portfolio {portfolio.id} not found"


def test_owned_portfolio_rejects_an_inactive_portfolio(client, test_db):
    user = User(email="inactive@example.com", username="inactive", password_hash="x")
    test_db.add(user)
    test_db.flush()
    portfolio = Portfolio(user_id=user.id, name="Archived", is_active=False)
    test_db.add(portfolio)
    test_db.commit()
    _login_as(user)

    response = client.get(f"/api/v1/analytics/portfolios/{portfolio.id}/benchmarks")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_database_routes_await_only_when_they_are_async():
    offenders = []
    for path in API.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            awaits = any(
                isinstance(child, (ast.Await, ast.AsyncFor, ast.AsyncWith))
                for child in ast.walk(node)
            )
            if not awaits:
                offenders.append(f"{path.relative_to(APP)}:{node.lineno} {node.name}")
    assert offenders == []
