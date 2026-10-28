#!/usr/bin/env python3
"""
Comprehensive unit tests for WatchlistService.

This module tests all functionality of the WatchlistService including:
- Watchlist CRUD operations
- Watchlist item management
- Performance tracking
- Alert management
- Real-time data integration
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.database.models import User
from core.database.models.watchlist import Watchlist, WatchlistAlert, WatchlistItem
from core.errors import DomainError
from core.schemas.watchlist import (
    WatchlistAlertCreate,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistUpdate,
)
from core.services.watchlist_service import WatchlistService


class TestWatchlistService:
    """Test suite for WatchlistService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_market_data_service(self):
        """Create a mock market data service."""
        mock_service = Mock()
        mock_service.get_current_price = AsyncMock(return_value=Decimal("150.00"))
        mock_service.get_market_data = AsyncMock(
            return_value={
                "current_price": Decimal("150.00"),
                "price_change": Decimal("5.00"),
                "price_change_percent": Decimal("3.45"),
            }
        )
        return mock_service

    @pytest.fixture
    def watchlist_service(self, mock_db, mock_market_data_service):
        """Create WatchlistService instance with mocked dependencies."""
        service = WatchlistService(mock_db)
        service.market_data_service = mock_market_data_service
        return service

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
            is_active=True,
            is_verified=True,
        )
        return user

    @pytest.fixture
    def sample_watchlist(self, sample_user):
        """Create a sample watchlist for testing."""
        watchlist = Watchlist(
            id=1,
            user_id=sample_user.id,
            name="Test Watchlist",
            description="A test watchlist",
            is_default=True,
            is_public=False,
            color="#FF5733",
            sort_order=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return watchlist

    @pytest.fixture
    def sample_watchlist_item(self, sample_watchlist):
        """Create a sample watchlist item for testing."""
        item = WatchlistItem(
            id=1,
            watchlist_id=sample_watchlist.id,
            symbol="AAPL",
            company_name="Apple Inc.",
            added_price=Decimal("140.00"),
            added_date=datetime.now(timezone.utc) - timedelta(days=30),
            current_price=Decimal("150.00"),
            price_change_since_added=Decimal("10.00"),
            price_change_percent_since_added=Decimal("7.14"),
            notes="Great company",
            personal_rating=5,
            investment_thesis="Strong fundamentals",
            alert_price_high=Decimal("160.00"),
            alert_price_low=Decimal("130.00"),
            alert_price_change_percent=Decimal("5.0"),
            alerts_enabled=True,
            sort_order=1,
            tags=["tech", "large-cap"],
            updated_at=datetime.now(timezone.utc),
        )
        return item

    @pytest.fixture
    def sample_watchlist_data(self):
        """Sample watchlist creation data."""
        return WatchlistCreate(
            name="Test Watchlist",
            description="A test watchlist",
            is_public=False,
            color="#FF5733",
        )

    @pytest.fixture
    def sample_watchlist_item_data(self):
        """Sample watchlist item creation data."""
        return WatchlistItemCreate(
            symbol="AAPL",
            company_name="Apple Inc.",
            added_price=Decimal("140.00"),
            notes="Great company",
            personal_rating=5,
            investment_thesis="Strong fundamentals",
            alert_price_high=Decimal("160.00"),
            alert_price_low=Decimal("130.00"),
            alert_price_change_percent=Decimal("5.0"),
            alerts_enabled=True,
            tags=["tech", "large-cap"],
        )

    # Test Watchlist CRUD Operations

    def test_create_watchlist_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_data
    ):
        """Test successful watchlist creation."""
        # Setup
        mock_db.query.return_value.filter.return_value.count.return_value = (
            0  # No existing watchlists
        )
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Execute
        result = watchlist_service.create_watchlist(
            sample_user.id, sample_watchlist_data
        )

        # Verify
        assert result is not None
        assert result.user_id == sample_user.id
        assert result.name == sample_watchlist_data.name
        assert result.description == sample_watchlist_data.description
        assert result.is_default is True  # First watchlist should be default
        assert result.is_public == sample_watchlist_data.is_public
        assert result.color == sample_watchlist_data.color

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_watchlist_not_first(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_data
    ):
        """Test watchlist creation when user already has watchlists."""
        # Setup
        mock_db.query.return_value.filter.return_value.count.return_value = (
            2  # User has existing watchlists
        )
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Execute
        result = watchlist_service.create_watchlist(
            sample_user.id, sample_watchlist_data
        )

        # Verify
        assert result.is_default is False  # Not the first watchlist

    def test_create_watchlist_database_error(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_data
    ):
        """Test watchlist creation with database error."""
        # Setup
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_db.add = Mock()
        mock_db.commit.side_effect = IntegrityError("Database error", None, None)

        # Execute & Verify
        with pytest.raises(IntegrityError):
            watchlist_service.create_watchlist(sample_user.id, sample_watchlist_data)

    def test_get_watchlist_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test successful watchlist retrieval."""
        # Setup
        mock_query = Mock()
        mock_filter = Mock()
        mock_options = Mock()
        mock_query.filter.return_value = mock_options
        mock_options.options.return_value = mock_filter
        mock_filter.first.return_value = sample_watchlist
        mock_db.query.return_value = mock_query

        # Execute
        result = watchlist_service.get_watchlist(sample_watchlist.id, sample_user.id)

        # Verify
        assert result == sample_watchlist
        mock_db.query.assert_called_once_with(Watchlist)

    def test_get_watchlist_not_found(self, watchlist_service, mock_db, sample_user):
        """Test watchlist retrieval when not found."""
        # Setup
        mock_query = Mock()
        mock_filter = Mock()
        mock_options = Mock()
        mock_query.filter.return_value = mock_options
        mock_options.options.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute
        result = watchlist_service.get_watchlist(999, sample_user.id)

        # Verify
        assert result is None

    def test_get_watchlist_wrong_user(
        self, watchlist_service, mock_db, sample_watchlist
    ):
        """Test watchlist retrieval with wrong user ID."""
        # Setup
        mock_query = Mock()
        mock_filter = Mock()
        mock_options = Mock()
        mock_query.filter.return_value = mock_options
        mock_options.options.return_value = mock_filter
        mock_filter.first.return_value = None
        mock_db.query.return_value = mock_query

        # Execute
        result = watchlist_service.get_watchlist(sample_watchlist.id, 999)

        # Verify
        assert result is None

    def test_get_user_watchlists_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test successful user watchlists retrieval."""
        # Setup
        sample_watchlist.items = []  # Mock items relationship
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            sample_watchlist
        ]

        # Execute
        result = watchlist_service.get_user_watchlists(sample_user.id)

        # Verify
        assert len(result) == 1
        assert result[0] == sample_watchlist
        assert hasattr(result[0], "item_count")
        assert result[0].item_count == 0

    def test_get_user_watchlists_with_items(
        self,
        watchlist_service,
        mock_db,
        sample_user,
        sample_watchlist,
        sample_watchlist_item,
    ):
        """Test user watchlists retrieval with items included."""
        # Setup
        sample_watchlist.items = [sample_watchlist_item]
        mock_db.query.return_value.filter.return_value.order_by.return_value.options.return_value.all.return_value = [
            sample_watchlist
        ]

        # Execute
        result = watchlist_service.get_user_watchlists(
            sample_user.id, include_items=True
        )

        # Verify
        assert len(result) == 1
        assert result[0].item_count == 1

    def test_remove_watchlist_item_not_found(
        self, watchlist_service, mock_db, sample_user
    ):
        """Test removing non-existent watchlist item."""
        # Setup
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        # Execute
        result = watchlist_service.remove_item_from_watchlist(999, sample_user.id)

        # Verify
        assert result is False

    # Test Performance Tracking

    def test_get_watchlist_performance_summary_empty_watchlist(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test performance summary for empty watchlist."""
        # Setup
        sample_watchlist.items = []

        # Mock the get_watchlist method to return our sample watchlist
        with patch.object(
            watchlist_service, "get_watchlist", return_value=sample_watchlist
        ):
            # Execute
            result = watchlist_service.get_watchlist_performance_summary(
                sample_watchlist.id, sample_user.id
            )

        # Verify
        assert result is not None
        assert result["total_items"] == 0
        assert result["items_with_gains"] == 0
        assert result["items_with_losses"] == 0
        assert result["total_gain_loss"] == Decimal("0")
        assert result["total_gain_loss_percent"] == Decimal("0")
        assert result["average_gain_loss"] == Decimal("0")

    def test_get_watchlist_performance_summary_not_found(
        self, watchlist_service, mock_db, sample_user
    ):
        """Test performance summary for non-existent watchlist."""
        # Setup
        # Mock the get_watchlist method to return None
        with patch.object(watchlist_service, "get_watchlist", return_value=None):
            # Execute
            result = watchlist_service.get_watchlist_performance_summary(
                999, sample_user.id
            )

        # Verify
        assert result is None

    # Test Real-time Data Integration

    @pytest.mark.asyncio
    async def test_get_watchlist_with_real_time_data_not_found(
        self, watchlist_service, mock_db, sample_user
    ):
        """Test real-time data retrieval for non-existent watchlist."""
        # Setup
        mock_db.query.return_value.filter.return_value.options.return_value.first.return_value = None

        # Execute
        result = await watchlist_service.get_watchlist_with_real_time_data(
            999, sample_user.id
        )

        # Verify
        assert result is None

    def test_get_public_watchlists_success(
        self, watchlist_service, mock_db, sample_watchlist
    ):
        """Test successful public watchlists retrieval."""
        # Setup
        sample_watchlist.is_public = True
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            sample_watchlist
        ]

        # Execute
        result = watchlist_service.get_public_watchlists(limit=10)

        # Verify
        assert len(result) == 1
        assert result[0] == sample_watchlist
        assert result[0].is_public is True

    # Test Error Handling

    def test_service_handles_database_errors_gracefully(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_data
    ):
        """Test that service handles database errors gracefully."""
        # Setup
        mock_db.query.side_effect = Exception("Database connection error")

        # Execute & Verify
        with pytest.raises(Exception, match="Database connection error"):
            watchlist_service.create_watchlist(sample_user.id, sample_watchlist_data)

    def test_service_logs_errors_appropriately(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_data
    ):
        """Test that service logs errors appropriately."""
        # Setup
        mock_db.query.side_effect = Exception("Test error")

        # Execute & Verify
        with pytest.raises(Exception):
            watchlist_service.create_watchlist(sample_user.id, sample_watchlist_data)

    # Test Edge Cases

    def test_empty_watchlist_operations(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test operations on empty watchlists."""
        # Setup
        sample_watchlist.items = []

        # Mock the get_watchlist method to return our sample watchlist
        with patch.object(
            watchlist_service, "get_watchlist", return_value=sample_watchlist
        ):
            # Execute
            result = watchlist_service.get_watchlist_performance_summary(
                sample_watchlist.id, sample_user.id
            )

        # Verify
        assert result["total_items"] == 0
        assert result["items_with_gains"] == 0
        assert result["items_with_losses"] == 0

    def test_watchlist_with_many_items(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test operations on watchlists with many items."""
        # Setup
        items = []
        for i in range(100):
            item = WatchlistItem(
                id=i,
                watchlist_id=sample_watchlist.id,
                symbol=f"SYMBOL{i}",
                company_name=f"Company {i}",
                added_price=Decimal("100.00"),
                current_price=Decimal("110.00"),
                price_change_since_added=Decimal("10.00"),
                price_change_percent_since_added=Decimal("10.00"),
            )
            items.append(item)

        sample_watchlist.items = items

        # Mock the get_watchlist method to return our sample watchlist
        with patch.object(
            watchlist_service, "get_watchlist", return_value=sample_watchlist
        ):
            # Execute
            result = watchlist_service.get_watchlist_performance_summary(
                sample_watchlist.id, sample_user.id
            )

        # Verify
        assert result["total_items"] == 100
        assert result["items_with_gains"] == 100
        assert result["items_with_losses"] == 0
        assert result["total_gain_loss"] == Decimal("1000.00")  # 100 * 10.00
        assert result["average_gain_loss"] == Decimal("10.00")

    def test_watchlist_item_with_none_values(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test handling of watchlist items with None values."""
        # Setup
        item = WatchlistItem(
            id=1,
            watchlist_id=sample_watchlist.id,
            symbol="TEST",
            company_name="Test Company",
            added_price=None,
            current_price=None,
            price_change_since_added=None,
            price_change_percent_since_added=None,
        )
        sample_watchlist.items = [item]

        # Mock the get_watchlist method to return our sample watchlist
        with patch.object(
            watchlist_service, "get_watchlist", return_value=sample_watchlist
        ):
            # Execute
            result = watchlist_service.get_watchlist_performance_summary(
                sample_watchlist.id, sample_user.id
            )

        # Verify
        assert result["total_items"] == 1
        assert result["items_with_gains"] == 0
        assert result["items_with_losses"] == 0
        assert result["total_gain_loss"] == Decimal("0")
        assert result["average_gain_loss"] == Decimal("0")


class Quotes:
    def __init__(self, prices):
        self.prices = prices

    async def get_current_price(self, symbol, fetch=True):
        return self.prices.get(symbol)

    async def get_symbols_info(self, symbols):
        return [
            {"symbol": s, "current_price": self.prices[s], "short_name": f"{s} Inc."}
            for s in symbols
            if s in self.prices
        ]


class TestWatchlistServiceWithDatabase:
    @pytest.fixture
    def owner(self, test_db):
        user = User(email="owner@example.com", username="owner", password_hash="x")
        other = User(email="other@example.com", username="other", password_hash="x")
        test_db.add_all([user, other])
        test_db.commit()
        return user, other

    @pytest.fixture
    def service(self, test_db):
        service = WatchlistService(test_db)
        service.market_data_service = Quotes(
            {"AAPL": Decimal("150"), "MSFT": Decimal("90")}
        )
        return service

    @pytest.fixture
    def watchlist(self, service, owner):
        user, _ = owner
        return service.create_watchlist(user.id, WatchlistCreate(name="Tech"))

    async def _add(self, service, watchlist, symbol, added_price=None):
        item = await service.add_item_to_watchlist(
            watchlist.id, watchlist.user_id, WatchlistItemCreate(symbol=symbol)
        )
        if added_price is not None:
            item.added_price = added_price
            service.db.commit()
        return item

    def test_update_watchlist(self, service, watchlist, owner):
        user, other = owner

        updated = service.update_watchlist(
            watchlist.id, user.id, WatchlistUpdate(name="Growth", is_public=True)
        )

        assert updated.name == "Growth"
        assert updated.is_public is True
        assert (
            service.update_watchlist(watchlist.id, other.id, WatchlistUpdate(name="x"))
            is None
        )

    def test_delete_watchlist(self, service, watchlist, owner):
        user, other = owner
        second = service.create_watchlist(user.id, WatchlistCreate(name="Second"))

        assert service.delete_watchlist(second.id, other.id) is False
        assert service.delete_watchlist(second.id, user.id) is True
        assert service.get_watchlist(second.id, user.id) is None

    def test_only_watchlist_cannot_be_deleted(self, service, watchlist, owner):
        user, _ = owner
        assert watchlist.is_default is True

        with pytest.raises(DomainError, match="only watchlist"):
            service.delete_watchlist(watchlist.id, user.id)

    @pytest.mark.asyncio
    async def test_add_item_records_current_price(self, service, watchlist, owner):
        user, other = owner

        item = await service.add_item_to_watchlist(
            watchlist.id, user.id, WatchlistItemCreate(symbol="aapl", notes="n")
        )

        assert item.symbol == "AAPL"
        assert item.added_price == Decimal("150")
        assert item.current_price == Decimal("150")
        assert item.sort_order == 1
        assert (
            await service.add_item_to_watchlist(
                watchlist.id, other.id, WatchlistItemCreate(symbol="MSFT")
            )
            is None
        )
        with pytest.raises(DomainError, match="already exists"):
            await service.add_item_to_watchlist(
                watchlist.id, user.id, WatchlistItemCreate(symbol="AAPL")
            )

    @pytest.mark.asyncio
    async def test_update_and_remove_item(self, service, watchlist, owner):
        user, other = owner
        item = await self._add(service, watchlist, "AAPL")

        assert (
            service.update_watchlist_item(
                item.id, other.id, WatchlistItemUpdate(notes="x")
            )
            is None
        )
        updated = service.update_watchlist_item(
            item.id,
            user.id,
            WatchlistItemUpdate(notes="Buy the dip", personal_rating=4),
        )
        assert updated.notes == "Buy the dip"
        assert updated.personal_rating == 4

        assert service.remove_item_from_watchlist(item.id, other.id) is False
        assert service.remove_item_from_watchlist(item.id, user.id) is True
        assert service.get_watchlist(watchlist.id, user.id).items == []

    @pytest.mark.asyncio
    async def test_performance_summary(self, service, watchlist, owner):
        user, _ = owner
        await self._add(service, watchlist, "AAPL", added_price=Decimal("100"))
        await self._add(service, watchlist, "MSFT", added_price=Decimal("100"))

        summary = service.get_watchlist_performance_summary(watchlist.id, user.id)

        assert summary["total_items"] == 2
        assert summary["items_with_gains"] == 1
        assert summary["items_with_losses"] == 1
        assert summary["total_gain_loss"] == Decimal("40")
        assert summary["average_gain_loss"] == Decimal("20")
        assert summary["best_performer"].symbol == "AAPL"
        assert summary["worst_performer"].symbol == "MSFT"

    @pytest.mark.asyncio
    async def test_real_time_data_updates_prices(self, service, watchlist, owner):
        user, other = owner
        item = await self._add(service, watchlist, "AAPL", added_price=Decimal("120"))

        result = await service.get_watchlist_with_real_time_data(watchlist.id, user.id)

        assert result.items[0].id == item.id
        assert item.current_price == Decimal("150")
        assert item.company_name == "AAPL Inc."
        assert item.price_change_since_added == Decimal("30")
        assert item.price_change_percent_since_added == Decimal("25")
        assert (
            await service.get_watchlist_with_real_time_data(watchlist.id, other.id)
            is None
        )

    @pytest.mark.asyncio
    async def test_create_price_alert(self, service, watchlist, owner):
        user, other = owner
        item = await self._add(service, watchlist, "AAPL")
        data = WatchlistAlertCreate(
            alert_type="price_high", threshold_value=Decimal("160"), condition="above"
        )

        alert = service.create_price_alert(item.id, user.id, data)

        assert alert.watchlist_item_id == item.id
        assert alert.user_id == user.id
        assert alert.threshold_value == Decimal("160")
        assert alert.is_active is True
        assert service.create_price_alert(item.id, other.id, data) is None

    @pytest.mark.asyncio
    async def test_alert_events_and_acknowledge(
        self, test_db, service, watchlist, owner
    ):
        user, other = owner
        item = await self._add(service, watchlist, "AAPL")
        now = datetime.now(timezone.utc)
        for i in range(2):
            test_db.add(
                WatchlistAlert(
                    watchlist_item_id=item.id,
                    user_id=user.id,
                    alert_type="price_high",
                    threshold_value=Decimal("140"),
                    condition="above",
                    is_triggered=True,
                    triggered_value=Decimal("150"),
                    triggered_at=now - timedelta(minutes=i),
                )
            )
        test_db.commit()

        events = service.get_alert_events(user.id)
        assert events["unread_count"] == 2
        assert [e["symbol"] for e in events["alerts"]] == ["AAPL", "AAPL"]
        assert events["alerts"][0]["watchlist_name"] == "Tech"
        assert service.get_alert_events(other.id)["alerts"] == []

        assert service.acknowledge_alerts(user.id, [events["alerts"][0]["id"]]) == 1
        assert service.get_alert_events(user.id, unread_only=True)["unread_count"] == 1
        assert len(service.get_alert_events(user.id, unread_only=True)["alerts"]) == 1

    @pytest.mark.asyncio
    async def test_statistics(self, service, watchlist, owner):
        user, _ = owner
        second = service.create_watchlist(
            user.id, WatchlistCreate(name="Public", is_public=True)
        )
        await self._add(service, watchlist, "AAPL")
        await self._add(service, watchlist, "MSFT")
        await self._add(service, second, "AAPL")

        stats = service.get_watchlist_statistics(user.id)

        assert stats["total_watchlists"] == 2
        assert stats["total_items"] == 3
        assert stats["public_watchlists"] == 1
        assert stats["active_alerts"] == 0
        assert stats["most_watched_symbols"][0] == {"symbol": "AAPL", "count": 2}
        assert len(stats["recent_additions"]) == 3
