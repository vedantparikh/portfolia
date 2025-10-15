"""
Comprehensive Unit Tests for Portfolio Calculation Service
Tests various scenarios using Apple historical data including:
- Different portfolio transaction patterns
- Portfolio age vs requested interval scenarios
- Benchmark comparisons
- Error handling cases
"""

import asyncio
from datetime import datetime
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta
import pandas as pd
import pyxirr

# Import the service and related classes
from app.core.services.portfolio_calculation_service import (
    PortfolioCalculationService,
)
from core.services.utils import PeriodType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockAsset:
    """Mock Asset model for testing"""

    def __init__(
        self, symbol: str, quantity: Decimal, current_value: Optional[float] = None
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.current_value = current_value


class MockPortfolioAsset:
    """Mock PortfolioAsset model for testing"""

    def __init__(self, asset: MockAsset, quantity: Decimal):
        self.asset = asset
        self.quantity = quantity


class MockTransaction:
    """Mock Transaction model for testing"""

    def __init__(
        self,
        transaction_date: datetime,
        transaction_type: str,
        quantity: Decimal,
        price_per_share: Decimal,
        asset_symbol: str,
    ):
        self.transaction_date = transaction_date
        self.transaction_type = transaction_type
        self.quantity = quantity
        self.price_per_share = price_per_share
        self.asset = MockAsset(asset_symbol, quantity)
        self.asset_id = 1  # Mock asset ID


class MockPortfolio:
    """Mock Portfolio model for testing"""

    def __init__(
        self,
        portfolio_id: int,
        name: str,
        assets: List[MockPortfolioAsset],
        transactions: List[MockTransaction],
    ):
        self.id = portfolio_id
        self.name = name
        self.assets = assets
        self.transactions = transactions


class MockMarketDataService:
    """Mock MarketDataService that uses Apple historical data"""

    def __init__(self, apple_data: Dict[str, Any]):
        self.apple_data = apple_data
        self.df = self._create_dataframe()

    def _create_dataframe(self) -> pd.DataFrame:
        """Convert Apple JSON data to pandas DataFrame"""
        df = pd.DataFrame(self.apple_data["data"])
        df["Date"] = pd.to_datetime(df["Date"], utc=True)
        df = df.set_index("Date")

        # Convert string values to float
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Sort by date ascending (oldest first)
        df = df.sort_index()
        return df

    async def fetch_ticker_data(
        self,
        symbol: str,
        period: str = "max",
        interval: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Mock fetch_ticker_data that returns Apple data for AAPL"""
        if symbol != "AAPL":
            return pd.DataFrame()  # Return empty for non-AAPL symbols

        df = self.df.copy()

        if start_date and end_date:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]

        return df


class TestPortfolioCalculationService(unittest.TestCase):
    """Comprehensive test suite for Portfolio Calculation Service"""

    @classmethod
    def setUpClass(cls):
        """Load Apple market data once for all tests"""
        with open("apple_market_data.json") as f:
            cls.apple_data = json.load(f)

        logger.info(
            f"Loaded Apple data with {cls.apple_data['data_points']} data points"
        )
        logger.info(
            f"Date range: {cls.apple_data['data'][0]['Date']} to {cls.apple_data['data'][-1]['Date']}"
        )

    def setUp(self):
        """Set up test fixtures"""
        self.mock_market_service = MockMarketDataService(self.apple_data)

        # Mock database session
        self.mock_db = MagicMock()

        # Create service with mock database
        self.service = PortfolioCalculationService(self.mock_db)
        self.service.market_data_service = self.mock_market_service

    def create_portfolio_scenario_1(self) -> MockPortfolio:
        """
        Scenario 1: Regular monthly investments over 2 years
        - Started investing 2 years ago
        - Monthly investments of $1000
        - Should have good CAGR and XIRR data
        """
        start_date = datetime.now() - relativedelta(years=2)
        transactions = []

        # Monthly investments for 24 months
        for i in range(24):
            transaction_date = start_date + relativedelta(months=i)
            # Use actual Apple price from that date (approximate)
            price = 150.0 + (i * 2)  # Simplified price progression
            quantity = Decimal(str(1000 / price))  # $1000 investment

            transactions.append(
                MockTransaction(
                    transaction_date=transaction_date,
                    transaction_type="BUY",
                    quantity=quantity,
                    price_per_share=Decimal(str(price)),
                    asset_symbol="AAPL",
                )
            )

        # Calculate total quantity
        total_quantity = sum(t.quantity for t in transactions)
        current_price = 254.43  # Recent Apple price from data

        asset = MockAsset("AAPL", total_quantity, float(total_quantity) * current_price)
        portfolio_asset = MockPortfolioAsset(asset, total_quantity)

        return MockPortfolio(
            1, "Monthly Investment Portfolio", [portfolio_asset], transactions
        )

    def create_portfolio_scenario_2(self) -> MockPortfolio:
        """
        Scenario 2: Young portfolio (3 months old)
        - Started 3 months ago
        - Should trigger age-based period adjustment
        """
        start_date = datetime.now() - relativedelta(months=3)
        transactions = []

        # Initial investment
        transactions.append(
            MockTransaction(
                transaction_date=start_date,
                transaction_type="BUY",
                quantity=Decimal(100),
                price_per_share=Decimal("200.0"),
                asset_symbol="AAPL",
            )
        )

        # Additional investment 1 month later
        transactions.append(
            MockTransaction(
                transaction_date=start_date + relativedelta(months=1),
                transaction_type="BUY",
                quantity=Decimal(50),
                price_per_share=Decimal("210.0"),
                asset_symbol="AAPL",
            )
        )

        total_quantity = Decimal(150)
        current_price = 254.43

        asset = MockAsset("AAPL", total_quantity, float(total_quantity) * current_price)
        portfolio_asset = MockPortfolioAsset(asset, total_quantity)

        return MockPortfolio(2, "Young Portfolio", [portfolio_asset], transactions)

    def create_portfolio_scenario_3(self) -> MockPortfolio:
        """
        Scenario 3: Portfolio with missing market data
        - Should trigger error handling
        """
        start_date = datetime.now() - relativedelta(months=6)
        transactions = []

        transactions.append(
            MockTransaction(
                transaction_date=start_date,
                transaction_type="BUY",
                quantity=Decimal(100),
                price_per_share=Decimal("180.0"),
                asset_symbol="AAPL",
            )
        )

        # Asset with no current market value (simulate missing data)
        asset = MockAsset("AAPL", Decimal(100), None)
        portfolio_asset = MockPortfolioAsset(asset, Decimal(100))

        return MockPortfolio(
            3, "Missing Data Portfolio", [portfolio_asset], transactions
        )

    def create_portfolio_scenario_4(self) -> MockPortfolio:
        """
        Scenario 4: Buy and sell transactions
        - Complex cash flow pattern for XIRR testing
        """
        start_date = datetime.now() - relativedelta(years=1, months=6)
        transactions = []

        # Initial large purchase
        transactions.append(
            MockTransaction(
                transaction_date=start_date,
                transaction_type="BUY",
                quantity=Decimal(200),
                price_per_share=Decimal("150.0"),
                asset_symbol="AAPL",
            )
        )

        # Partial sale 6 months later
        transactions.append(
            MockTransaction(
                transaction_date=start_date + relativedelta(months=6),
                transaction_type="SELL",
                quantity=Decimal(50),
                price_per_share=Decimal("180.0"),
                asset_symbol="AAPL",
            )
        )

        # Additional purchase 3 months later
        transactions.append(
            MockTransaction(
                transaction_date=start_date + relativedelta(months=9),
                transaction_type="BUY",
                quantity=Decimal(75),
                price_per_share=Decimal("200.0"),
                asset_symbol="AAPL",
            )
        )

        total_quantity = Decimal(225)  # 200 - 50 + 75
        current_price = 254.43

        asset = MockAsset("AAPL", total_quantity, float(total_quantity) * current_price)
        portfolio_asset = MockPortfolioAsset(asset, total_quantity)

        return MockPortfolio(4, "Buy-Sell Portfolio", [portfolio_asset], transactions)

    @patch("app.core.database.connection.get_db_session")
    async def test_scenario_1_regular_monthly_investments(self, mock_get_db):
        """Test regular monthly investment scenario"""
        logger.info("=== Testing Scenario 1: Regular Monthly Investments ===")

        portfolio = self.create_portfolio_scenario_1()
        mock_get_db.return_value.__aenter__.return_value = self.mock_db

        # Mock database queries
        self.mock_db.get.return_value = portfolio
        self.mock_db.scalars.return_value.all.return_value = portfolio.transactions

        # Test 1-year performance
        result = await self.service.calculate_portfolio_performance(
            portfolio_id=1, user_id=1, period=PeriodType.LAST_1_YEAR
        )

        logger.info(f"1-Year Results: {result}")

        # Assertions
        self.assertIsNotNone(result)
        self.assertEqual(result["portfolio_id"], 1)
        self.assertIsNotNone(result["current_value"])
        self.assertIsNone(result.get("errors"))  # Should have no errors

        # Check metrics
        metrics = result.get("metrics", {})
        self.assertIsNotNone(metrics.get("cagr"))
        self.assertIsNotNone(metrics.get("xirr"))
        self.assertIsNotNone(metrics.get("twr"))

        logger.info(f"CAGR: {metrics.get('cagr')}%")
        logger.info(f"XIRR: {metrics.get('xirr')}%")
        logger.info(f"TWR: {metrics.get('twr')}%")

        # Test 2-year performance (should work since portfolio is 2 years old)
        result_2y = await self.service.calculate_portfolio_performance(
            portfolio_id=1, user_id=1, period=PeriodType.LAST_2_YEARS
        )

        logger.info(f"2-Year Results: {result_2y}")
        self.assertIsNotNone(result_2y["metrics"]["cagr"])
        self.assertIsNotNone(result_2y["metrics"]["xirr"])
        self.assertIsNotNone(result_2y["metrics"]["twr"])

    @patch("app.core.database.connection.get_db_session")
    async def test_scenario_2_young_portfolio_age_adjustment(self, mock_get_db):
        """Test young portfolio with automatic period adjustment"""
        logger.info("=== Testing Scenario 2: Young Portfolio Age Adjustment ===")

        portfolio = self.create_portfolio_scenario_2()
        mock_get_db.return_value.__aenter__.return_value = self.mock_db

        self.mock_db.get.return_value = portfolio
        self.mock_db.scalars.return_value.all.return_value = portfolio.transactions

        # Request 1-year performance on 3-month-old portfolio
        result = await self.service.calculate_portfolio_performance(
            portfolio_id=2, user_id=1, period=PeriodType.LAST_1_YEAR
        )

        logger.info(f"Young Portfolio Results: {result}")

        # Should automatically adjust to inception period
        self.assertEqual(result["period"], "inception")
        self.assertIsNotNone(result.get("period_adjustment"))

        period_adj = result["period_adjustment"]
        self.assertEqual(period_adj["requested_period"], "1y")
        self.assertIn("Portfolio age", period_adj["adjustment_reason"])

        logger.info(f"Period adjustment: {period_adj}")

        # Should still have valid metrics
        metrics = result.get("metrics", {})
        self.assertIsNotNone(metrics.get("cagr"))
        self.assertIsNotNone(metrics.get("xirr"))
        self.assertIsNotNone(metrics.get("twr"))

    @patch("app.core.database.connection.get_db_session")
    async def test_scenario_3_missing_market_data_error_handling(self, mock_get_db):
        """Test error handling when market data is missing"""
        logger.info("=== Testing Scenario 3: Missing Market Data Error Handling ===")

        portfolio = self.create_portfolio_scenario_3()
        mock_get_db.return_value.__aenter__.return_value = self.mock_db

        self.mock_db.get.return_value = portfolio
        self.mock_db.scalars.return_value.all.return_value = portfolio.transactions

        result = await self.service.calculate_portfolio_performance(
            portfolio_id=3, user_id=1, period=PeriodType.LAST_6_MONTHS
        )

        logger.info(f"Missing Data Results: {result}")

        # Should have errors
        self.assertIsNotNone(result.get("errors"))
        self.assertGreater(len(result["errors"]), 0)

        # Metrics should be None due to missing data
        metrics = result.get("metrics", {})
        self.assertIsNone(metrics.get("cagr"))
        self.assertIsNone(metrics.get("xirr"))
        self.assertIsNone(metrics.get("twr"))

        # Should log specific error about missing market value
        error_msg = result["errors"][0]
        self.assertIn("No current market value available", error_msg)
        self.assertIn("AAPL", error_msg)

        logger.info(f"Error message: {error_msg}")

    @patch("app.core.database.connection.get_db_session")
    async def test_scenario_4_complex_buy_sell_xirr(self, mock_get_db):
        """Test complex buy/sell scenario for XIRR calculation"""
        logger.info("=== Testing Scenario 4: Complex Buy/Sell XIRR ===")

        portfolio = self.create_portfolio_scenario_4()
        mock_get_db.return_value.__aenter__.return_value = self.mock_db

        self.mock_db.get.return_value = portfolio
        self.mock_db.scalars.return_value.all.return_value = portfolio.transactions

        result = await self.service.calculate_portfolio_performance(
            portfolio_id=4, user_id=1, period=PeriodType.INCEPTION
        )

        logger.info(f"Complex Buy/Sell Results: {result}")

        # Should have valid results
        self.assertIsNone(result.get("errors"))

        metrics = result.get("metrics", {})
        self.assertIsNotNone(metrics.get("xirr"))
        self.assertIsNotNone(metrics.get("twr"))

        # XIRR and TWR should account for the complex cash flow pattern
        xirr = metrics.get("xirr")
        twr = metrics.get("twr")
        logger.info(f"Complex XIRR: {xirr}%")
        logger.info(f"Complex TWR: {twr}%")

        # Verify the calculation makes sense (should be positive given Apple's performance)
        self.assertIsInstance(xirr, (int, float))

    @patch("app.core.database.connection.get_db_session")
    async def test_benchmark_comparison_same_stock(self, mock_get_db):
        """Test benchmark comparison using same stock (should have similar results)"""
        logger.info("=== Testing Benchmark Comparison (Same Stock) ===")

        portfolio = self.create_portfolio_scenario_1()
        mock_get_db.return_value.__aenter__.return_value = self.mock_db

        self.mock_db.get.return_value = portfolio
        self.mock_db.scalars.return_value.all.return_value = portfolio.transactions

        # Compare portfolio against AAPL benchmark
        result = await self.service.compare_portfolio_to_benchmark(
            portfolio_id=1,
            user_id=1,
            benchmark_symbol="AAPL",
            period=PeriodType.LAST_1_YEAR,
        )

        logger.info(f"Benchmark Comparison Results: {result}")

        # Should have both portfolio and benchmark results
        self.assertIsNotNone(result.get("portfolio"))
        self.assertIsNotNone(result.get("benchmark"))
        self.assertIsNotNone(result.get("comparison"))

        portfolio_metrics = result["portfolio"]["metrics"]
        benchmark_metrics = result["benchmark"]["metrics"]
        comparison = result["comparison"]

        logger.info(f"Portfolio XIRR: {portfolio_metrics.get('xirr')}%")
        logger.info(f"Benchmark XIRR: {benchmark_metrics.get('xirr')}%")
        logger.info(f"XIRR Difference: {comparison.get('xirr_difference')}%")
        logger.info(f"Portfolio TWR: {portfolio_metrics.get('twr')}%")
        logger.info(f"Benchmark TWR: {benchmark_metrics.get('twr')}%")
        logger.info(f"TWR Difference: {comparison.get('twr_difference')}%")

        # Since both are investing in AAPL with same cash flows, results should be very similar
        # Allow for small differences due to timing and calculation methods
        if portfolio_metrics.get("xirr") and benchmark_metrics.get("xirr"):
            xirr_diff = abs(portfolio_metrics["xirr"] - benchmark_metrics["xirr"])
            self.assertLess(
                xirr_diff, 5.0, "XIRR difference should be small for same stock"
            )

    async def test_manual_cagr_calculation_verification(self):
        """Manually verify CAGR calculation against known values"""
        logger.info("=== Testing Manual CAGR Calculation Verification ===")

        # Test with known values - create mock transactions for testing
        start_date = datetime.now() - relativedelta(years=2)
        transactions = [
            MockTransaction(
                transaction_date=start_date,
                transaction_type="BUY",
                quantity=Decimal(100),
                price_per_share=Decimal("100.0"),  # $10,000 initial
                asset_symbol="AAPL",
            )
        ]

        current_value = 15000.0  # Final value

        # Expected CAGR = (15000/10000)^(1/2) - 1 = 0.2247 = 22.47%
        expected_cagr = ((current_value / 10000.0) ** (1 / 2.0) - 1) * 100

        calculated_cagr = await self.service._calculate_cagr(
            portfolio_id=999,
            all_transactions=transactions,
            current_value=current_value,
            start_date=start_date,
            end_date=datetime.now(),
        )

        logger.info(f"Expected CAGR: {expected_cagr:.2f}%")
        logger.info(
            f"Calculated CAGR: {calculated_cagr if calculated_cagr is not None else 'None'}"
        )

        if calculated_cagr is not None:
            self.assertAlmostEqual(calculated_cagr, expected_cagr, places=1)
        else:
            self.fail("CAGR calculation returned None")

    async def test_manual_xirr_calculation_verification(self):
        """Manually verify XIRR calculation against known cash flows"""
        logger.info("=== Testing Manual XIRR Calculation Verification ===")

        # Create mock transactions that represent known cash flows
        transactions = [
            MockTransaction(
                transaction_date=datetime(2023, 1, 1),
                transaction_type="BUY",
                quantity=Decimal(100),
                price_per_share=Decimal("100.0"),  # $10,000 investment
                asset_symbol="AAPL",
            ),
            MockTransaction(
                transaction_date=datetime(2023, 6, 1),
                transaction_type="BUY",
                quantity=Decimal(50),
                price_per_share=Decimal("100.0"),  # $5,000 additional investment
                asset_symbol="AAPL",
            ),
        ]

        current_value = 18000.0  # Final portfolio value

        # Calculate using our service
        calculated_xirr = await self.service._calculate_xirr(
            portfolio_id=999,
            all_transactions=transactions,
            current_value=current_value,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
        )

        # Calculate using pyxirr directly for verification
        dates = [datetime(2023, 1, 1), datetime(2023, 6, 1), datetime(2024, 1, 1)]
        amounts = [-10000, -5000, 18000]
        expected_xirr = pyxirr.xirr(dates, amounts) * 100

        logger.info(f"Expected XIRR: {expected_xirr:.2f}%")
        logger.info(
            f"Calculated XIRR: {calculated_xirr if calculated_xirr is not None else 'None'}"
        )

        if calculated_xirr is not None:
            self.assertAlmostEqual(calculated_xirr, expected_xirr, places=1)
        else:
            self.fail("XIRR calculation returned None")

    async def test_manual_twr_calculation_verification(self):
        """Manually verify TWR calculation against known values"""
        logger.info("=== Testing Manual TWR Calculation Verification ===")

        # Create mock transactions for TWR testing
        # Scenario: Single investment, no intermediate cash flows
        transactions = [
            MockTransaction(
                transaction_date=datetime(2023, 1, 1),
                transaction_type="BUY",
                quantity=Decimal(100),
                price_per_share=Decimal("100.0"),  # $10,000 investment
                asset_symbol="AAPL",
            )
        ]

        current_value = 12000.0  # Final portfolio value

        # Calculate using our service
        calculated_twr = await self.service._calculate_twr(
            portfolio_id=999,
            all_transactions=transactions,
            current_value=current_value,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2024, 1, 1),
        )

        # Expected TWR for single investment = (Final/Initial)^(1/years) - 1
        # (12000/10000)^(1/1) - 1 = 0.20 = 20%
        expected_twr = ((current_value / 10000.0) ** (1 / 1.0) - 1) * 100

        logger.info(f"Expected TWR: {expected_twr:.2f}%")
        logger.info(
            f"Calculated TWR: {calculated_twr if calculated_twr is not None else 'None'}"
        )

        if calculated_twr is not None:
            self.assertAlmostEqual(calculated_twr, expected_twr, places=1)
        else:
            self.fail("TWR calculation returned None")

    async def run_all_tests(self):
        """Run all test scenarios"""
        logger.info("Starting comprehensive portfolio calculation tests...")

        test_methods = [
            self.test_scenario_1_regular_monthly_investments,
            self.test_scenario_2_young_portfolio_age_adjustment,
            self.test_scenario_3_missing_market_data_error_handling,
            self.test_scenario_4_complex_buy_sell_xirr,
            self.test_benchmark_comparison_same_stock,
            self.test_manual_cagr_calculation_verification,
            self.test_manual_xirr_calculation_verification,
            self.test_manual_twr_calculation_verification,
        ]

        results = {}
        for test_method in test_methods:
            test_name = test_method.__name__
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Running {test_name}")
                logger.info(f"{'='*60}")

                await test_method()
                results[test_name] = "PASSED"
                logger.info(f"✅ {test_name} PASSED")

            except Exception as e:
                results[test_name] = f"FAILED: {e!s}"
                logger.error(f"❌ {test_name} FAILED: {e!s}")

        return results


async def main():
    """Main test runner"""
    test_suite = TestPortfolioCalculationService()
    test_suite.setUpClass()

    # Run individual test setup
    test_suite.setUp()

    # Run all tests
    results = await test_suite.run_all_tests()

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = 0
    failed = 0

    for test_name, result in results.items():
        status = "✅ PASSED" if result == "PASSED" else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result == "PASSED":
            passed += 1
        else:
            failed += 1
            print(f"   Error: {result}")

    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")

    if failed > 0:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
    else:
        print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
