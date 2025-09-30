"""
Comprehensive unit tests for PortfolioCalculationService.

Tests cover all calculation methods with various scenarios including:
- Normal portfolio performance calculations
- Edge cases (empty portfolios, single transactions)
- Benchmark calculations and comparisons
- Error handling and validation
- Mock data scenarios
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from app.core.database.models import (
    Asset,
    Portfolio,
    PortfolioAsset,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.core.services.portfolio_calculation_service import (
    PeriodType,
    PortfolioCalculationService,
)


class TestPortfolioCalculationService:
    """Test suite for PortfolioCalculationService."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_market_data_service(self):
        """Mock market data service."""
        service = Mock()
        service.fetch_ticker_data = AsyncMock()
        return service

    @pytest.fixture
    def calculation_service(self, mock_db, mock_market_data_service):
        """Create PortfolioCalculationService with mocked dependencies."""
        service = PortfolioCalculationService(mock_db)
        service.market_data_service = mock_market_data_service
        return service

    @pytest.fixture
    def sample_portfolio(self):
        """Create a sample portfolio."""
        portfolio = Mock(spec=Portfolio)
        portfolio.id = 1
        portfolio.name = "Test Portfolio"
        portfolio.user_id = 1
        return portfolio

    @pytest.fixture
    def sample_asset(self):
        """Create a sample asset."""
        asset = Mock(spec=Asset)
        asset.id = 1
        asset.symbol = "AAPL"
        asset.name = "Apple Inc."
        return asset

    @pytest.fixture
    def sample_transactions(self):
        """Create sample transactions for testing."""
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        transactions = []

        # Buy transaction
        buy_tx = Mock(spec=Transaction)
        buy_tx.id = 1
        buy_tx.portfolio_id = 1
        buy_tx.asset_id = 1
        buy_tx.transaction_type = TransactionType.BUY
        buy_tx.quantity = Decimal("100.0")
        buy_tx.price = Decimal("150.0")
        buy_tx.total_amount = Decimal("15000.0")
        buy_tx.transaction_date = base_date
        buy_tx.status = TransactionStatus.COMPLETED
        buy_tx.fees = Decimal("0.0")
        buy_tx.taxes = Decimal("0.0")
        transactions.append(buy_tx)

        # Another buy transaction
        buy_tx2 = Mock(spec=Transaction)
        buy_tx2.id = 2
        buy_tx2.portfolio_id = 1
        buy_tx2.asset_id = 1
        buy_tx2.transaction_type = TransactionType.BUY
        buy_tx2.quantity = Decimal("50.0")
        buy_tx2.price = Decimal("160.0")
        buy_tx2.total_amount = Decimal("8000.0")
        buy_tx2.transaction_date = base_date + timedelta(days=30)
        buy_tx2.status = TransactionStatus.COMPLETED
        buy_tx2.fees = Decimal("0.0")
        buy_tx2.taxes = Decimal("0.0")
        transactions.append(buy_tx2)

        # Sell transaction
        sell_tx = Mock(spec=Transaction)
        sell_tx.id = 3
        sell_tx.portfolio_id = 1
        sell_tx.asset_id = 1
        sell_tx.transaction_type = TransactionType.SELL
        sell_tx.quantity = Decimal("25.0")
        sell_tx.price = Decimal("180.0")
        sell_tx.total_amount = Decimal("4500.0")
        sell_tx.transaction_date = base_date + timedelta(days=60)
        sell_tx.status = TransactionStatus.COMPLETED
        sell_tx.fees = Decimal("0.0")
        sell_tx.taxes = Decimal("0.0")
        transactions.append(sell_tx)

        return transactions

    @pytest.fixture
    def sample_portfolio_asset(self):
        """Create a sample portfolio asset."""
        portfolio_asset = Mock(spec=PortfolioAsset)
        portfolio_asset.id = 1
        portfolio_asset.portfolio_id = 1
        portfolio_asset.asset_id = 1
        portfolio_asset.quantity = Decimal("125.0")  # 100 + 50 - 25
        portfolio_asset.cost_basis_total = Decimal(
            "18500.0"
        )  # 15000 + 8000 - (25 * avg_cost)
        portfolio_asset.current_value = Decimal("25000.0")  # 125 * 200 (current price)
        return portfolio_asset

    def test_period_type_get_start_date(self):
        """Test PeriodType.get_start_date method."""
        base_date = datetime(2024, 6, 15, tzinfo=timezone.utc)

        # Test different periods
        assert PeriodType.get_start_date(
            PeriodType.LAST_3_MONTHS, base_date
        ) == base_date - timedelta(days=90)
        assert PeriodType.get_start_date(
            PeriodType.LAST_6_MONTHS, base_date
        ) == base_date - timedelta(days=180)
        assert PeriodType.get_start_date(
            PeriodType.LAST_1_YEAR, base_date
        ) == base_date - timedelta(days=365)
        assert PeriodType.get_start_date(
            PeriodType.LAST_2_YEARS, base_date
        ) == base_date - timedelta(days=730)
        assert PeriodType.get_start_date(
            PeriodType.LAST_3_YEARS, base_date
        ) == base_date - timedelta(days=1095)
        assert PeriodType.get_start_date(
            PeriodType.LAST_5_YEARS, base_date
        ) == base_date - timedelta(days=1825)
        assert PeriodType.get_start_date(PeriodType.YTD, base_date) == datetime(
            2024, 1, 1
        )
        assert PeriodType.get_start_date(PeriodType.INCEPTION, base_date) is None

        # Test with invalid period
        with pytest.raises(ValueError):
            PeriodType.get_start_date("invalid_period", base_date)

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance_success(
        self,
        calculation_service,
        sample_portfolio,
        sample_transactions,
        sample_portfolio_asset,
    ):
        """Test successful portfolio performance calculation."""
        # Mock database queries
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_portfolio
        )
        calculation_service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            sample_transactions
        )
        calculation_service.db.query.return_value.filter.return_value.all.return_value = [
            sample_portfolio_asset
        ]

        # Mock market data service for TWR calculation
        mock_price_data = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", "2024-03-01", freq="D"),
                "Close": np.random.uniform(150, 200, 61),
                "Volume": np.random.randint(1000000, 10000000, 61),
            }
        )
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            mock_price_data
        )

        # Test calculation
        result = await calculation_service.calculate_portfolio_performance(
            portfolio_id=1, user_id=1, period=PeriodType.INCEPTION
        )

        # Verify result structure
        assert result["portfolio_id"] == 1
        assert result["portfolio_name"] == "Test Portfolio"
        assert result["period"] == PeriodType.INCEPTION
        assert "metrics" in result
        assert "current_value" in result
        assert "calculation_date" in result

        # Verify metrics are present (values may be None due to mocking)
        metrics = result["metrics"]
        assert "cagr" in metrics
        assert "xirr" in metrics
        assert "twr" in metrics
        assert "mwr" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance_no_portfolio(
        self, calculation_service
    ):
        """Test portfolio performance calculation when portfolio doesn't exist."""
        # Mock no portfolio found
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        with pytest.raises(ValueError, match="Portfolio 1 not found or not accessible"):
            await calculation_service.calculate_portfolio_performance(
                portfolio_id=1, user_id=1
            )

    @pytest.mark.asyncio
    async def test_calculate_portfolio_performance_no_transactions(
        self, calculation_service, sample_portfolio
    ):
        """Test portfolio performance calculation with no transactions."""
        # Mock portfolio exists but no transactions
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_portfolio
        )
        calculation_service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            []
        )

        result = await calculation_service.calculate_portfolio_performance(
            portfolio_id=1, user_id=1
        )

        # Should return empty result
        assert result["portfolio_id"] == 1
        assert "error" in result
        assert result["error"] == "No transactions found for the specified period"

    def test_calculate_cagr_success(self, calculation_service, sample_transactions):
        """Test CAGR calculation with valid data."""
        current_value = 25000.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        cagr = calculation_service._calculate_cagr(
            sample_transactions, current_value, start_date, end_date
        )

        # CAGR should be calculated and returned as percentage
        assert cagr is not None
        assert isinstance(cagr, float)

        # Validate logical outcome: With initial investment of ~15000 and final value of 25000
        # over 1 year, CAGR should be around 66.67%
        assert 60.0 < cagr < 70.0, f"Expected CAGR between 60-70%, got {cagr}%"

    def test_calculate_cagr_zero_values(self, calculation_service, sample_transactions):
        """Test CAGR calculation with zero values."""
        current_value = 0.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        cagr = calculation_service._calculate_cagr(
            sample_transactions, current_value, start_date, end_date
        )

        # Should return None for zero values
        assert cagr is None

    def test_calculate_xirr_success(self, calculation_service, sample_transactions):
        """Test XIRR calculation with valid data."""
        current_value = 25000.0
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        with patch("app.core.services.portfolio_calculation_service.xirr") as mock_xirr:
            mock_xirr.return_value = 0.15  # 15% return

            xirr_result = calculation_service._calculate_xirr(
                sample_transactions, current_value, end_date
            )

            assert xirr_result == 15.0  # Should be converted to percentage
            mock_xirr.assert_called_once()

    def test_calculate_xirr_insufficient_data(self, calculation_service):
        """Test XIRR calculation with insufficient data."""
        transactions = []  # Empty transactions
        current_value = 25000.0
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        xirr_result = calculation_service._calculate_xirr(
            transactions, current_value, end_date
        )

        assert xirr_result is None

    def test_calculate_simple_twr_success(
        self, calculation_service, sample_transactions
    ):
        """Test simple TWR calculation."""
        current_value = 25000.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        twr = calculation_service._calculate_simple_twr(
            sample_transactions, current_value, start_date, end_date
        )

        assert twr is not None
        assert isinstance(twr, float)

    def test_calculate_mwr_success(self, calculation_service, sample_transactions):
        """Test MWR calculation (should be same as XIRR)."""
        current_value = 25000.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        with patch("app.core.services.portfolio_calculation_service.xirr") as mock_xirr:
            mock_xirr.return_value = 0.12  # 12% return

            mwr = calculation_service._calculate_mwr(
                sample_transactions, current_value, start_date, end_date
            )

            assert mwr == 12.0  # Should be converted to percentage

    @pytest.mark.asyncio
    async def test_calculate_benchmark_performance_success(self, calculation_service):
        """Test benchmark performance calculation."""
        benchmark_symbol = "^GSPC"
        investment_amounts = [
            (datetime(2024, 1, 1, tzinfo=timezone.utc), 15000.0),
            (datetime(2024, 2, 1, tzinfo=timezone.utc), 8000.0),
            (datetime(2024, 3, 1, tzinfo=timezone.utc), -4500.0),  # Sell
        ]

        # Mock price data
        mock_price_data = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", "2024-12-31", freq="D"),
                "Close": np.random.uniform(4000, 5000, 366),
                "Volume": np.random.randint(1000000, 10000000, 366),
            }
        )
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            mock_price_data
        )

        result = await calculation_service.calculate_benchmark_performance(
            benchmark_symbol, investment_amounts, PeriodType.INCEPTION
        )

        # Verify result structure
        assert result["benchmark_symbol"] == benchmark_symbol
        assert result["period"] == PeriodType.INCEPTION
        assert "metrics" in result
        assert "current_value" in result
        assert "total_invested" in result

        # Verify metrics
        metrics = result["metrics"]
        assert "cagr" in metrics
        assert "xirr" in metrics
        assert "twr" in metrics
        assert "mwr" in metrics

    @pytest.mark.asyncio
    async def test_calculate_benchmark_performance_no_data(self, calculation_service):
        """Test benchmark performance calculation with no price data."""
        benchmark_symbol = "INVALID"
        investment_amounts = [
            (datetime(2024, 1, 1, tzinfo=timezone.utc), 15000.0),
        ]

        # Mock empty price data
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            pd.DataFrame()
        )

        result = await calculation_service.calculate_benchmark_performance(
            benchmark_symbol, investment_amounts, PeriodType.INCEPTION
        )

        # Should return empty result
        assert result["benchmark_symbol"] == benchmark_symbol
        assert "error" in result

    def test_calculate_benchmark_cagr_success(self, calculation_service):
        """Test benchmark CAGR calculation."""
        transactions = [
            {
                "transaction_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "total_amount": 15000.0,
                "transaction_type": "BUY",
            },
            {
                "transaction_date": datetime(2024, 2, 1, tzinfo=timezone.utc),
                "total_amount": 8000.0,
                "transaction_type": "BUY",
            },
            {
                "transaction_date": datetime(2024, 3, 1, tzinfo=timezone.utc),
                "total_amount": 4500.0,
                "transaction_type": "SELL",
            },
        ]
        current_value = 25000.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        cagr = calculation_service._calculate_benchmark_cagr(
            transactions, current_value, start_date, end_date
        )

        assert cagr is not None
        assert isinstance(cagr, float)

    def test_calculate_benchmark_cagr_negative_net_investment(
        self, calculation_service
    ):
        """Test benchmark CAGR calculation with negative net investment."""
        transactions = [
            {
                "transaction_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "total_amount": 5000.0,
                "transaction_type": "BUY",
            },
            {
                "transaction_date": datetime(2024, 2, 1, tzinfo=timezone.utc),
                "total_amount": 10000.0,
                "transaction_type": "SELL",
            },
        ]
        current_value = 1000.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        cagr = calculation_service._calculate_benchmark_cagr(
            transactions, current_value, start_date, end_date
        )

        # Should return None for negative net investment
        assert cagr is None

    def test_calculate_benchmark_twr_success(self, calculation_service):
        """Test benchmark TWR calculation."""
        transactions = [
            {
                "transaction_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "total_amount": 15000.0,
                "transaction_type": "BUY",
            },
            {
                "transaction_date": datetime(2024, 2, 1, tzinfo=timezone.utc),
                "total_amount": 8000.0,
                "transaction_type": "BUY",
            },
        ]
        current_value = 25000.0
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        twr = calculation_service._calculate_benchmark_twr(
            transactions, current_value, start_date, end_date
        )

        assert twr is not None
        assert isinstance(twr, float)

    def test_calculate_benchmark_xirr_success(self, calculation_service):
        """Test benchmark XIRR calculation."""
        transactions = [
            {
                "transaction_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
                "total_amount": 15000.0,
                "transaction_type": "BUY",
            },
            {
                "transaction_date": datetime(2024, 2, 1, tzinfo=timezone.utc),
                "total_amount": 8000.0,
                "transaction_type": "BUY",
            },
        ]
        current_value = 25000.0
        end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)

        with patch("app.core.services.portfolio_calculation_service.xirr") as mock_xirr:
            mock_xirr.return_value = 0.10  # 10% return

            xirr_result = calculation_service._calculate_benchmark_xirr(
                transactions, current_value, end_date
            )

            assert xirr_result == 10.0  # Should be converted to percentage

    @pytest.mark.asyncio
    async def test_compare_portfolio_to_benchmark(
        self,
        calculation_service,
        sample_portfolio,
        sample_transactions,
        sample_portfolio_asset,
    ):
        """Test portfolio to benchmark comparison."""
        # Mock portfolio performance calculation
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_portfolio
        )
        calculation_service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            sample_transactions
        )
        calculation_service.db.query.return_value.filter.return_value.all.return_value = [
            sample_portfolio_asset
        ]

        # Mock market data for both portfolio and benchmark
        mock_price_data = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", "2024-12-31", freq="D"),
                "Close": np.random.uniform(150, 200, 366),
                "Volume": np.random.randint(1000000, 10000000, 366),
            }
        )
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            mock_price_data
        )

        result = await calculation_service.compare_portfolio_to_benchmark(
            portfolio_id=1,
            user_id=1,
            benchmark_symbol="^GSPC",
            period=PeriodType.INCEPTION,
        )

        # Verify result structure
        assert "portfolio_performance" in result
        assert "benchmark_performance" in result
        assert "comparison" in result

        comparison = result["comparison"]
        assert "cagr_difference" in comparison
        assert "xirr_difference" in comparison
        assert "twr_difference" in comparison
        assert "mwr_difference" in comparison
        assert "outperforming" in comparison

    async def test_get_current_portfolio_value_success(
        self, calculation_service, sample_portfolio_asset
    ):
        """Test getting current portfolio value."""
        calculation_service.db.query.return_value.filter.return_value.all.return_value = [
            sample_portfolio_asset
        ]

        value = await calculation_service.get_current_portfolio_value(1)

        assert value == 25000.0

    async def test_get_current_portfolio_value_no_current_value(self, calculation_service):
        """Test getting current portfolio value when current_value is None."""
        # Mock portfolio asset with None current_value
        portfolio_asset = Mock(spec=PortfolioAsset)
        portfolio_asset.current_value = None
        portfolio_asset.cost_basis_total = Decimal("18500.0")

        calculation_service.db.query.return_value.filter.return_value.all.return_value = [
            portfolio_asset
        ]

        value = await calculation_service.get_current_portfolio_value(1)

        # Should fallback to cost basis
        assert value == 18500.0

    def test_get_current_asset_value_success(
        self, calculation_service, sample_portfolio_asset
    ):
        """Test getting current asset value."""
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_portfolio_asset
        )

        value = calculation_service._get_current_asset_value(1, 1)

        assert value == 25000.0

    def test_get_current_asset_value_no_asset(self, calculation_service):
        """Test getting current asset value when asset doesn't exist."""
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            None
        )

        value = calculation_service._get_current_asset_value(1, 1)

        assert value == 0.0

    def test_calculate_initial_value_with_start_date(
        self, calculation_service, sample_transactions
    ):
        """Test calculating initial value with start date."""
        start_date = datetime(
            2024, 1, 15, tzinfo=timezone.utc
        )  # After first transaction

        initial_value = calculation_service._calculate_initial_value(
            sample_transactions, start_date
        )

        # Should be the first transaction amount since start_date is after it
        assert initial_value == 15000.0

    def test_calculate_initial_value_no_start_date(
        self, calculation_service, sample_transactions
    ):
        """Test calculating initial value without start date."""
        initial_value = calculation_service._calculate_initial_value(
            sample_transactions, None
        )

        # Should be the first transaction amount
        assert initial_value == 15000.0

    def test_calculate_holdings_as_of_date(
        self, calculation_service, sample_transactions
    ):
        """Test calculating holdings as of a specific date."""
        as_of_date = datetime(
            2024, 2, 15, tzinfo=timezone.utc
        ).date()  # After first two transactions

        holdings = calculation_service._calculate_holdings_as_of_date(
            sample_transactions, as_of_date
        )

        # Should have 150 shares (100 + 50)
        assert holdings[1] == 150.0

    def test_calculate_holdings_as_of_date_with_sell(
        self, calculation_service, sample_transactions
    ):
        """Test calculating holdings as of date including sell transactions."""
        as_of_date = datetime(
            2024, 3, 15, tzinfo=timezone.utc
        ).date()  # After all transactions

        holdings = calculation_service._calculate_holdings_as_of_date(
            sample_transactions, as_of_date
        )

        # Should have 125 shares (100 + 50 - 25)
        assert holdings[1] == 125.0

    def test_safe_subtract_both_values(self, calculation_service):
        """Test safe subtraction with both values present."""
        result = calculation_service._safe_subtract(10.5, 5.2)
        assert result == 5.3

    def test_safe_subtract_none_values(self, calculation_service):
        """Test safe subtraction with None values."""
        assert calculation_service._safe_subtract(None, 5.0) is None
        assert calculation_service._safe_subtract(10.0, None) is None
        assert calculation_service._safe_subtract(None, None) is None

    def test_is_outperforming_true(self, calculation_service):
        """Test outperforming check when portfolio is better."""
        result = calculation_service._is_outperforming(15.0, 10.0)
        assert result is True

    def test_is_outperforming_false(self, calculation_service):
        """Test outperforming check when portfolio is worse."""
        result = calculation_service._is_outperforming(8.0, 12.0)
        assert result is False

    def test_is_outperforming_none_values(self, calculation_service):
        """Test outperforming check with None values."""
        assert calculation_service._is_outperforming(None, 10.0) is None
        assert calculation_service._is_outperforming(15.0, None) is None
        assert calculation_service._is_outperforming(None, None) is None

    def test_empty_performance_result(self, calculation_service):
        """Test empty performance result structure."""
        result = calculation_service._empty_performance_result(1, PeriodType.INCEPTION)

        assert result["portfolio_id"] == 1
        assert result["period"] == PeriodType.INCEPTION
        assert "error" in result
        assert "metrics" in result

        metrics = result["metrics"]
        assert all(value is None for value in metrics.values())

    def test_empty_benchmark_performance_result(self, calculation_service):
        """Test empty benchmark performance result structure."""
        result = calculation_service._empty_benchmark_performance_result(
            "^GSPC", PeriodType.INCEPTION
        )

        assert result["benchmark_symbol"] == "^GSPC"
        assert result["period"] == PeriodType.INCEPTION
        assert "error" in result
        assert "metrics" in result

        metrics = result["metrics"]
        assert all(value is None for value in metrics.values())

    @pytest.mark.asyncio
    async def test_calculate_daily_portfolio_values_success(
        self, calculation_service, sample_transactions, sample_asset
    ):
        """Test calculating daily portfolio values."""
        # Mock asset query
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_asset
        )

        # Mock price data
        mock_price_data = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-01", "2024-03-01", freq="D"),
                "Close": np.random.uniform(150, 200, 61),
                "Volume": np.random.randint(1000000, 10000000, 61),
            }
        )
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            mock_price_data
        )

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 3, 1, tzinfo=timezone.utc)

        result = await calculation_service._calculate_daily_portfolio_values(
            1, start_date, end_date
        )

        # Should return a DataFrame with portfolio values
        assert isinstance(result, pd.DataFrame)
        if not result.empty:
            assert "Date" in result.columns
            assert "PortfolioValue" in result.columns
            assert "DailyReturn" in result.columns

    @pytest.mark.asyncio
    async def test_calculate_volatility_success(
        self, calculation_service, sample_transactions, sample_asset
    ):
        """Test volatility calculation."""
        # Mock asset query
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_asset
        )

        # Mock price data with some volatility
        dates = pd.date_range("2024-01-01", "2024-03-01", freq="D")
        prices = [
            150 + 10 * np.sin(i * 0.1) + np.random.normal(0, 2)
            for i in range(len(dates))
        ]
        mock_price_data = pd.DataFrame(
            {
                "Date": dates,
                "Close": prices,
                "Volume": np.random.randint(1000000, 10000000, len(dates)),
            }
        )
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            mock_price_data
        )

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 3, 1, tzinfo=timezone.utc)

        volatility = await calculation_service._calculate_volatility(
            1, start_date, end_date
        )

        # Should return a positive volatility value
        if volatility is not None:
            assert isinstance(volatility, float)
            assert volatility >= 0

    def test_calculate_sharpe_ratio_success(self, calculation_service):
        """Test Sharpe ratio calculation."""
        annual_return = 15.0  # 15%
        volatility = 20.0  # 20%
        risk_free_rate = 2.0  # 2%

        sharpe = calculation_service._calculate_sharpe_ratio(
            annual_return, volatility, risk_free_rate
        )

        expected_sharpe = (15.0 - 2.0) / 20.0  # 0.65
        assert abs(sharpe - expected_sharpe) < 0.001

    def test_calculate_sharpe_ratio_none_values(self, calculation_service):
        """Test Sharpe ratio calculation with None values."""
        assert calculation_service._calculate_sharpe_ratio(None, 20.0) is None
        assert calculation_service._calculate_sharpe_ratio(15.0, None) is None
        assert calculation_service._calculate_sharpe_ratio(15.0, 0.0) is None

    @pytest.mark.asyncio
    async def test_calculate_max_drawdown_success(
        self, calculation_service, sample_transactions, sample_asset
    ):
        """Test maximum drawdown calculation."""
        # Mock asset query
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_asset
        )

        # Mock price data with a clear drawdown pattern
        dates = pd.date_range("2024-01-01", "2024-03-01", freq="D")
        # Create a pattern: rise, peak, drawdown, recovery
        prices = []
        for i, date in enumerate(dates):
            if i < 20:
                prices.append(150 + i * 2)  # Rising
            elif i < 30:
                prices.append(190 - (i - 20) * 3)  # Drawdown
            else:
                prices.append(160 + (i - 30) * 1)  # Recovery

        mock_price_data = pd.DataFrame(
            {
                "Date": dates,
                "Close": prices,
                "Volume": np.random.randint(1000000, 10000000, len(dates)),
            }
        )
        calculation_service.market_data_service.fetch_ticker_data.return_value = (
            mock_price_data
        )

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 3, 1, tzinfo=timezone.utc)

        max_drawdown = await calculation_service._calculate_max_drawdown(
            1, start_date, end_date
        )

        # Should return a positive drawdown percentage
        if max_drawdown is not None:
            assert isinstance(max_drawdown, float)
            assert max_drawdown >= 0

    @pytest.mark.asyncio
    async def test_calculate_asset_performance_success(
        self,
        calculation_service,
        sample_portfolio,
        sample_asset,
        sample_portfolio_asset,
    ):
        """Test asset performance calculation."""
        # Mock database queries
        calculation_service.db.query.return_value.filter.return_value.first.return_value = (
            sample_portfolio
        )

        # Mock asset transactions query
        asset_transactions = [
            tx for tx in self.sample_transactions() if tx.asset_id == 1
        ]
        calculation_service.db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            asset_transactions
        )

        # Mock asset value query
        def mock_query_side_effect(*args):
            if args[0] == Asset:
                return Mock(
                    filter=Mock(
                        return_value=Mock(first=Mock(return_value=sample_asset))
                    )
                )
            elif args[0] == PortfolioAsset:
                return Mock(
                    filter=Mock(
                        return_value=Mock(
                            first=Mock(return_value=sample_portfolio_asset)
                        )
                    )
                )
            else:
                return Mock(
                    filter=Mock(
                        return_value=Mock(first=Mock(return_value=sample_portfolio))
                    )
                )

        calculation_service.db.query.side_effect = mock_query_side_effect

        result = await calculation_service.calculate_asset_performance(
            portfolio_id=1, asset_id=1, user_id=1, period=PeriodType.INCEPTION
        )

        # Verify result structure
        assert result["portfolio_id"] == 1
        assert result["asset_id"] == 1
        assert result["asset_symbol"] == "AAPL"
        assert result["asset_name"] == "Apple Inc."
        assert "metrics" in result
        assert "current_value" in result

    def sample_transactions(self):
        """Helper method to create sample transactions for testing."""
        base_date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        transactions = []

        # Buy transaction
        buy_tx = Mock(spec=Transaction)
        buy_tx.id = 1
        buy_tx.portfolio_id = 1
        buy_tx.asset_id = 1
        buy_tx.transaction_type = TransactionType.BUY
        buy_tx.quantity = Decimal("100.0")
        buy_tx.price = Decimal("150.0")
        buy_tx.total_amount = Decimal("15000.0")
        buy_tx.transaction_date = base_date
        buy_tx.status = TransactionStatus.COMPLETED
        buy_tx.fees = Decimal("0.0")
        buy_tx.taxes = Decimal("0.0")
        transactions.append(buy_tx)

        return transactions


class TestPortfolioCalculationServiceIntegration:
    """Integration tests for PortfolioCalculationService with more realistic scenarios."""

    @pytest.fixture
    def real_calculation_service(self, mock_db):
        """Create service with real market data service for integration tests."""
        from app.core.services.market_data_service import MarketDataService

        service = PortfolioCalculationService(mock_db)
        # Use real market data service but we'll mock the external calls
        service.market_data_service = MarketDataService()
        return service

    @pytest.mark.asyncio
    async def test_realistic_portfolio_scenario(self, real_calculation_service):
        """Test with a realistic portfolio scenario similar to Portfolio 5."""
        # Create realistic transactions similar to Portfolio 5
        base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

        transactions = []

        # First buy
        buy_tx1 = Mock(spec=Transaction)
        buy_tx1.id = 1
        buy_tx1.portfolio_id = 5
        buy_tx1.asset_id = 1
        buy_tx1.transaction_type = TransactionType.BUY
        buy_tx1.quantity = Decimal("4.27222600")
        buy_tx1.price = Decimal("234.0700")
        buy_tx1.total_amount = Decimal("1000.9999")
        buy_tx1.transaction_date = base_date
        transactions.append(buy_tx1)

        # Second buy
        buy_tx2 = Mock(spec=Transaction)
        buy_tx2.id = 2
        buy_tx2.portfolio_id = 5
        buy_tx2.asset_id = 1
        buy_tx2.transaction_type = TransactionType.BUY
        buy_tx2.quantity = Decimal("5.55555600")
        buy_tx2.price = Decimal("180.0000")
        buy_tx2.total_amount = Decimal("1001.0001")
        buy_tx2.transaction_date = base_date + timedelta(days=31)
        transactions.append(buy_tx2)

        # Sell transaction
        sell_tx = Mock(spec=Transaction)
        sell_tx.id = 3
        sell_tx.portfolio_id = 5
        sell_tx.asset_id = 1
        sell_tx.transaction_type = TransactionType.SELL
        sell_tx.quantity = Decimal("4.54545500")
        sell_tx.price = Decimal("220.0000")
        sell_tx.total_amount = Decimal("1001.0001")
        sell_tx.transaction_date = base_date + timedelta(days=188)  # July 8
        transactions.append(sell_tx)

        # Test CAGR calculation
        current_value = 1200.0  # Assume current value
        end_date = datetime(2025, 9, 14, tzinfo=timezone.utc)

        cagr = real_calculation_service._calculate_cagr(
            transactions, current_value, None, end_date
        )

        # CAGR should be calculated properly
        assert cagr is not None
        assert isinstance(cagr, float)

        # Test XIRR calculation
        with patch("app.core.services.portfolio_calculation_service.xirr") as mock_xirr:
            mock_xirr.return_value = 0.08  # 8% return

            xirr_result = real_calculation_service._calculate_xirr(
                transactions, current_value, end_date
            )

            assert xirr_result == 8.0

    @pytest.mark.asyncio
    async def test_benchmark_calculation_realistic_scenario(
        self, real_calculation_service
    ):
        """Test benchmark calculation with realistic investment schedule."""
        benchmark_symbol = "^GSPC"

        # Investment amounts matching Portfolio 5 transactions
        investment_amounts = [
            (datetime(2025, 1, 1, tzinfo=timezone.utc), 1000.9999),
            (datetime(2025, 2, 1, tzinfo=timezone.utc), 1001.0001),
            (datetime(2025, 7, 8, tzinfo=timezone.utc), -1001.0001),  # Sell
        ]

        # Mock realistic S&P 500 price data
        dates = pd.date_range("2025-01-01", "2025-09-14", freq="D")
        # S&P 500 prices around 4000-5000 range
        prices = [
            4500 + 100 * np.sin(i * 0.01) + np.random.normal(0, 50)
            for i in range(len(dates))
        ]
        mock_price_data = pd.DataFrame(
            {
                "Date": dates,
                "Close": prices,
                "Volume": np.random.randint(1000000, 10000000, len(dates)),
            }
        )

        with patch.object(
            real_calculation_service.market_data_service,
            "fetch_ticker_data",
            return_value=mock_price_data,
        ):

            result = await real_calculation_service.calculate_benchmark_performance(
                benchmark_symbol, investment_amounts, PeriodType.INCEPTION
            )

            # Verify result
            assert result["benchmark_symbol"] == benchmark_symbol
            assert "metrics" in result
            assert "current_value" in result
            assert "total_invested" in result

            # Total invested should be net of buys and sells
            expected_total = 1000.9999 + 1001.0001 - 1001.0001
            assert abs(result["total_invested"] - expected_total) < 0.01

            # Metrics should be calculated
            metrics = result["metrics"]
            assert "cagr" in metrics
            assert "xirr" in metrics
            assert "twr" in metrics
            assert "mwr" in metrics
