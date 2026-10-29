import os
import sys
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set testing environment BEFORE importing app modules
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_USER"] = "test_user"
os.environ["POSTGRES_PASSWORD"] = "test_password"
os.environ["POSTGRES_DB"] = "test_db"
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_DB"] = "1"
os.environ["REDIS_PASSWORD"] = ""
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-testing-only"

# Force SQLite for testing
os.environ["FORCE_SQLITE"] = "true"

# Import after setting environment variables to ensure test config is used
from core.database.connection import get_db
from core.database.models.base import Base
from main import app

_QUARANTINE = [
    line.strip()
    for line in open(os.path.join(os.path.dirname(__file__), "quarantine.txt"))
    if line.strip() and not line.startswith("#")
]
collect_ignore = [e.removeprefix("tests/") for e in _QUARANTINE if "::" not in e]
_QUARANTINED_TESTS = {e for e in _QUARANTINE if "::" in e}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.nodeid in _QUARANTINED_TESTS:
            item.add_marker(
                pytest.mark.xfail(
                    strict=True, reason="quarantined: tests/quarantine.txt"
                )
            )


# Create test database
@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for testing
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    return engine


@pytest.fixture(scope="session")
def test_db_session_factory(test_db_engine):
    """Create test database session factory."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_db_engine
    )
    return TestingSessionLocal


@pytest.fixture(scope="function")
def test_db(test_db_engine, test_db_session_factory):
    """
    Create test database session for each test function.

    Each test gets a fresh database session with:
    - Clean tables (recreated for each test)
    - Isolated data (no cross-test contamination)
    - Automatic cleanup after each test
    """
    # Create tables for this test
    Base.metadata.create_all(bind=test_db_engine)

    # Create session
    session = test_db_session_factory()

    yield session

    # Cleanup - rollback changes and close session
    session.rollback()
    session.close()

    # Clean tables after each test to ensure isolation
    Base.metadata.drop_all(bind=test_db_engine)


@pytest.fixture(scope="function")
def client(test_db) -> Generator:
    """Create test client with test database."""

    def override_get_db():
        try:
            yield test_db
            test_db.commit()
        except Exception:
            test_db.rollback()
            raise

    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(test_db) -> AsyncGenerator:
    """Create async test client with test database."""

    def override_get_db():
        try:
            yield test_db
            test_db.commit()
        except Exception:
            test_db.rollback()
            raise

    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db

    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database(test_db_engine):
    """
    Clean up test database after all tests complete.

    This fixture runs automatically after all tests finish and ensures:
    1. All SQLite tables are dropped
    2. Database engine is properly disposed
    3. No test data persists between test runs
    4. Clean test environment for next run
    """
    yield
    # Drop all tables and close engine after all tests
    Base.metadata.drop_all(bind=test_db_engine)
    test_db_engine.dispose()


# Test data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
    }


@pytest.fixture
def sample_login_data():
    """Sample login data for testing."""
    return {"username": "testuser", "password": "testpassword123"}


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {"symbol": "AAPL", "period": "1d", "interval": "1m"}


@pytest.fixture
def sample_indicator_data():
    """Sample indicator data for testing."""
    return {"name": "AAPL", "period": 14, "interval": "1d"}
