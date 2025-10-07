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

    def test_update_watchlist_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test successful watchlist update."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_watchlist
        )
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        update_data = WatchlistUpdate(
            name="Updated Watchlist",
            description="Updated description",
            is_public=True,
            color="#00FF00",
        )

        # Execute
        result = watchlist_service.update_watchlist(
            sample_watchlist.id, sample_user.id, update_data
        )

        # Verify
        assert result == sample_watchlist
        assert sample_watchlist.name == update_data.name
        assert sample_watchlist.description == update_data.description
        assert sample_watchlist.is_public == update_data.is_public
        assert sample_watchlist.color == update_data.color
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_watchlist_not_found(self, watchlist_service, mock_db, sample_user):
        """Test watchlist update when not found."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        update_data = WatchlistUpdate(name="Updated Watchlist")

        # Execute
        result = watchlist_service.update_watchlist(999, sample_user.id, update_data)

        # Verify
        assert result is None

    def test_delete_watchlist_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist
    ):
        """Test successful watchlist deletion."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_watchlist
        )
        mock_db.delete = Mock()
        mock_db.commit = Mock()

        # Execute
        result = watchlist_service.delete_watchlist(sample_watchlist.id, sample_user.id)

        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(sample_watchlist)
        mock_db.commit.assert_called_once()

    def test_delete_watchlist_not_found(self, watchlist_service, mock_db, sample_user):
        """Test watchlist deletion when not found."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute
        result = watchlist_service.delete_watchlist(999, sample_user.id)

        # Verify
        assert result is False

    # Test Watchlist Item Operations

    @pytest.mark.asyncio
    async def test_add_watchlist_item_success(
        self,
        watchlist_service,
        mock_db,
        sample_user,
        sample_watchlist,
        sample_watchlist_item_data,
    ):
        """Test successful watchlist item addition."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_watchlist
        )
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Execute
        result = await watchlist_service.add_item_to_watchlist(
            sample_watchlist.id, sample_user.id, sample_watchlist_item_data
        )

        # Verify
        assert result is not None
        assert result.watchlist_id == sample_watchlist.id
        assert result.symbol == sample_watchlist_item_data.symbol
        assert result.company_name == sample_watchlist_item_data.company_name
        assert result.added_price == sample_watchlist_item_data.added_price
        assert result.notes == sample_watchlist_item_data.notes
        assert result.personal_rating == sample_watchlist_item_data.personal_rating
        assert result.investment_thesis == sample_watchlist_item_data.investment_thesis
        assert result.alert_price_high == sample_watchlist_item_data.alert_price_high
        assert result.alert_price_low == sample_watchlist_item_data.alert_price_low
        assert result.alerts_enabled == sample_watchlist_item_data.alerts_enabled
        assert result.tags == sample_watchlist_item_data.tags

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_watchlist_item_watchlist_not_found(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_item_data
    ):
        """Test adding item to non-existent watchlist."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Execute
        result = await watchlist_service.add_item_to_watchlist(
            999, sample_user.id, sample_watchlist_item_data
        )

        # Verify
        assert result is None

    def test_update_watchlist_item_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_item
    ):
        """Test successful watchlist item update."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_watchlist_item
        )
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        update_data = WatchlistItemUpdate(
            notes="Updated notes",
            personal_rating=4,
            investment_thesis="Updated thesis",
            alert_price_high=Decimal("170.00"),
            alert_price_low=Decimal("120.00"),
            alerts_enabled=False,
            tags=["tech", "growth"],
        )

        # Execute
        result = watchlist_service.update_watchlist_item(
            sample_watchlist_item.id, sample_user.id, update_data
        )

        # Verify
        assert result == sample_watchlist_item
        assert sample_watchlist_item.notes == update_data.notes
        assert sample_watchlist_item.personal_rating == update_data.personal_rating
        assert sample_watchlist_item.investment_thesis == update_data.investment_thesis
        assert sample_watchlist_item.alert_price_high == update_data.alert_price_high
        assert sample_watchlist_item.alert_price_low == update_data.alert_price_low
        assert sample_watchlist_item.alerts_enabled == update_data.alerts_enabled
        assert sample_watchlist_item.tags == update_data.tags

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_remove_watchlist_item_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_item
    ):
        """Test successful watchlist item removal."""
        # Setup
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = sample_watchlist_item
        mock_db.delete = Mock()
        mock_db.commit = Mock()

        # Execute
        result = watchlist_service.remove_item_from_watchlist(
            sample_watchlist_item.id, sample_user.id
        )

        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(sample_watchlist_item)
        mock_db.commit.assert_called_once()

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

    def test_get_watchlist_performance_summary_success(
        self,
        watchlist_service,
        mock_db,
        sample_user,
        sample_watchlist,
        sample_watchlist_item,
    ):
        """Test successful performance summary retrieval."""
        # Setup
        sample_watchlist_item.price_change_since_added = Decimal("10.00")
        sample_watchlist_item.price_change_percent_since_added = Decimal("7.14")
        sample_watchlist.items = [sample_watchlist_item]

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
        assert result["total_items"] == 1
        assert result["items_with_gains"] == 1
        assert result["items_with_losses"] == 0
        assert result["total_gain_loss"] == Decimal("10.00")
        assert abs(result["total_gain_loss_percent"] - Decimal("7.14")) < Decimal(
            "0.01"
        )
        assert result["average_gain_loss"] == Decimal("10.00")
        assert result["best_performer"] == "AAPL"
        assert result["worst_performer"] == "AAPL"

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
    async def test_get_watchlist_with_real_time_data_success(
        self,
        watchlist_service,
        mock_db,
        sample_user,
        sample_watchlist,
        sample_watchlist_item,
    ):
        """Test successful real-time data retrieval."""
        # Setup
        sample_watchlist.items = [sample_watchlist_item]
        mock_db.query.return_value.filter.return_value.options.return_value.first.return_value = sample_watchlist
        mock_db.refresh = Mock()

        # Execute
        result = await watchlist_service.get_watchlist_with_real_time_data(
            sample_watchlist.id, sample_user.id
        )

        # Verify
        assert result == sample_watchlist
        assert hasattr(result, "item_count")
        assert result.item_count == 1
        mock_db.refresh.assert_called_once_with(sample_watchlist)

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

    @pytest.mark.asyncio
    async def test_get_watchlist_with_real_time_data_calculates_days_since_added(
        self,
        watchlist_service,
        mock_db,
        sample_user,
        sample_watchlist,
        sample_watchlist_item,
    ):
        """Test that real-time data method calculates days since added."""
        # Setup
        added_date = datetime.now(timezone.utc) - timedelta(days=30)
        sample_watchlist_item.added_date = added_date
        sample_watchlist.items = [sample_watchlist_item]
        mock_db.query.return_value.filter.return_value.options.return_value.first.return_value = sample_watchlist
        mock_db.refresh = Mock()

        # Execute
        result = await watchlist_service.get_watchlist_with_real_time_data(
            sample_watchlist.id, sample_user.id
        )

        # Verify
        assert result == sample_watchlist
        assert hasattr(sample_watchlist_item, "days_since_added")
        assert sample_watchlist_item.days_since_added == 30

    # Test Alert Management

    def test_create_watchlist_alert_success(
        self, watchlist_service, mock_db, sample_user, sample_watchlist_item
    ):
        """Test successful watchlist alert creation."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = (
            sample_watchlist_item
        )
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        alert_data = WatchlistAlertCreate(
            alert_type="price_high",
            threshold_value=Decimal("160.00"),
            condition="above",
            notify_email=True,
            notify_push=False,
            notify_sms=False,
        )

        # Execute
        result = watchlist_service.create_watchlist_alert(
            sample_watchlist_item.id, sample_user.id, alert_data
        )

        # Verify
        assert result is not None
        assert result.watchlist_item_id == sample_watchlist_item.id
        assert result.user_id == sample_user.id
        assert result.alert_type == alert_data.alert_type
        assert result.target_price == alert_data.target_price
        assert result.is_active == alert_data.is_active
        assert result.message == alert_data.message

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_watchlist_alert_item_not_found(
        self, watchlist_service, mock_db, sample_user
    ):
        """Test alert creation for non-existent watchlist item."""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None

        alert_data = WatchlistAlertCreate(
            alert_type="price_high",
            threshold_value=Decimal("160.00"),
            condition="above",
            notify_email=True,
            notify_push=False,
            notify_sms=False,
        )

        # Execute
        result = watchlist_service.create_watchlist_alert(
            999, sample_user.id, alert_data
        )

        # Verify
        assert result is None

    def test_get_user_alerts_success(self, watchlist_service, mock_db, sample_user):
        """Test successful user alerts retrieval."""
        # Setup
        alert1 = WatchlistAlert(
            id=1,
            watchlist_item_id=1,
            user_id=sample_user.id,
            alert_type="price_high",
            threshold_value=Decimal("160.00"),
            condition="above",
            is_active=True,
            notify_email=True,
            notify_push=False,
            notify_sms=False,
        )
        alert2 = WatchlistAlert(
            id=2,
            watchlist_item_id=2,
            user_id=sample_user.id,
            alert_type="price_low",
            threshold_value=Decimal("130.00"),
            condition="below",
            is_active=False,
            notify_email=True,
            notify_push=False,
            notify_sms=False,
        )
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            alert1,
            alert2,
        ]

        # Execute
        result = watchlist_service.get_user_alerts(sample_user.id)

        # Verify
        assert len(result) == 2
        assert result[0] == alert1
        assert result[1] == alert2

    def test_get_user_alerts_active_only(self, watchlist_service, mock_db, sample_user):
        """Test user alerts retrieval with active_only filter."""
        # Setup
        active_alert = WatchlistAlert(
            id=1,
            watchlist_item_id=1,
            user_id=sample_user.id,
            alert_type="price_high",
            threshold_value=Decimal("160.00"),
            condition="above",
            is_active=True,
            notify_email=True,
            notify_push=False,
            notify_sms=False,
        )
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [
            active_alert
        ]

        # Execute
        result = watchlist_service.get_user_alerts(sample_user.id, active_only=True)

        # Verify
        assert len(result) == 1
        assert result[0] == active_alert

    # Test Statistics

    def test_get_watchlist_statistics_success(
        self, watchlist_service, mock_db, sample_user
    ):
        """Test successful watchlist statistics retrieval."""
        # Setup
        mock_db.query.return_value.filter.return_value.count.side_effect = [
            3,
            15,
            1,
        ]  # total_watchlists, total_items, public_watchlists

        # Execute
        result = watchlist_service.get_watchlist_statistics(sample_user.id)

        # Verify
        assert result["total_watchlists"] == 3
        assert result["total_items"] == 15
        assert result["public_watchlists"] == 1
        assert "average_items_per_watchlist" in result
        assert result["average_items_per_watchlist"] == 5.0

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
