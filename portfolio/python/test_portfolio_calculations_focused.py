"""
Focused Unit Tests for Portfolio Calculation Service
Tests the core calculation logic using Apple historical data
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta
import pandas as pd
import pyxirr

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppleDataProcessor:
    """Processes Apple historical data for testing"""

    def __init__(self, apple_data_file: str):
        with open(apple_data_file, "r") as f:
            self.apple_data = json.load(f)

        self.df = self._create_dataframe()
        logger.info(
            f"Loaded Apple data: {len(self.df)} records from {self.df.index.min()} to {self.df.index.max()}"
        )

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

    def get_price_at_date(self, target_date: datetime) -> float:
        """Get Apple price at a specific date"""
        try:
            # Convert to pandas timestamp with UTC timezone
            if not isinstance(target_date, pd.Timestamp):
                target_date = pd.Timestamp(target_date, tz="UTC")
            elif target_date.tz is None:
                target_date = target_date.tz_localize("UTC")

            # Use asof to find the last available price on or before target date
            price_row = self.df.asof(target_date)

            if pd.notna(price_row["Close"]):
                return float(price_row["Close"])

            return None
        except Exception as e:
            logger.warning(f"Could not get price for date {target_date}: {e}")
            return None

    def get_price_range(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get Apple price data for a date range"""
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)

        return self.df[(self.df.index >= start_ts) & (self.df.index <= end_ts)]


class PortfolioScenario:
    """Represents a portfolio scenario for testing"""

    def __init__(
        self, name: str, transactions: List[Dict], apple_processor: AppleDataProcessor
    ):
        self.name = name
        self.transactions = transactions
        self.apple_processor = apple_processor

        # Calculate current portfolio value
        self.current_quantity = self._calculate_current_quantity()
        self.current_price = apple_processor.get_price_at_date(datetime.now())
        self.current_value = (
            self.current_quantity * self.current_price if self.current_price else None
        )

        current_price_str = (
            f"${self.current_price:.2f}" if self.current_price else "N/A"
        )
        current_value_str = (
            f"${self.current_value:.2f}" if self.current_value else "N/A"
        )
        logger.info(
            f"Scenario '{name}': {self.current_quantity} shares, current price {current_price_str}, value {current_value_str}"
        )

    def _calculate_current_quantity(self) -> float:
        """Calculate current quantity from transactions"""
        quantity = 0.0
        for txn in self.transactions:
            if txn["type"] == "BUY":
                quantity += txn["quantity"]
            elif txn["type"] == "SELL":
                quantity -= txn["quantity"]
        return quantity

    def get_cash_flows(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> List[Dict]:
        """Get cash flows for XIRR calculation"""
        cash_flows = []

        # Add transaction cash flows
        for txn in self.transactions:
            txn_date = txn["date"]
            if start_date and txn_date < start_date:
                continue
            if end_date and txn_date > end_date:
                continue

            if txn["type"] == "BUY":
                amount = -txn["quantity"] * txn["price"]  # Negative for outflow
            else:  # SELL
                amount = txn["quantity"] * txn["price"]  # Positive for inflow

            cash_flows.append({"date": txn_date, "amount": amount})

        # Add final value as positive cash flow
        final_date = end_date or datetime.now()
        if self.current_value:
            cash_flows.append({"date": final_date, "amount": self.current_value})

        return cash_flows

    def calculate_manual_cagr(
        self, start_date: datetime, end_date: datetime = None
    ) -> float:
        """Calculate CAGR manually"""
        if not end_date:
            end_date = datetime.now()

        # Get initial investment value
        initial_value = 0.0
        for txn in self.transactions:
            if txn["date"] <= start_date:
                if txn["type"] == "BUY":
                    initial_value += txn["quantity"] * txn["price"]
                else:  # SELL
                    initial_value -= txn["quantity"] * txn["price"]

        if initial_value <= 0:
            logger.warning("Initial value is zero or negative, cannot calculate CAGR")
            return None

        # Calculate years
        years = (end_date - start_date).days / 365.25
        if years <= 0:
            return None

        # CAGR formula: (Final Value / Initial Value)^(1/years) - 1
        cagr = ((self.current_value / initial_value) ** (1 / years) - 1) * 100
        return cagr

    def calculate_manual_xirr(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> float:
        """Calculate XIRR manually using pyxirr"""
        cash_flows = self.get_cash_flows(start_date, end_date)

        if len(cash_flows) < 2:
            logger.warning("Need at least 2 cash flows for XIRR")
            return None

        dates = [cf["date"] for cf in cash_flows]
        amounts = [cf["amount"] for cf in cash_flows]

        # Check for both positive and negative cash flows
        has_positive = any(amount > 0 for amount in amounts)
        has_negative = any(amount < 0 for amount in amounts)

        if not (has_positive and has_negative):
            logger.warning("XIRR requires both positive and negative cash flows")
            return None

        try:
            xirr = pyxirr.xirr(dates, amounts) * 100
            return xirr
        except Exception as e:
            logger.error(f"XIRR calculation failed: {e}")
            return None

    def calculate_manual_twr(
        self, start_date: datetime = None, end_date: datetime = None
    ) -> float:
        """Calculate TWR manually using sub-period returns."""
        try:
            if not end_date:
                end_date = datetime.now()

            if not start_date:
                start_date = min(txn["date"] for txn in self.transactions)

            # Get cash flow dates within the period
            cash_flow_dates = []
            for txn in self.transactions:
                if start_date <= txn["date"] <= end_date:
                    cash_flow_dates.append(txn["date"])

            cash_flow_dates = sorted(list(set(cash_flow_dates)))

            if not cash_flow_dates:
                # No cash flows in period, calculate simple return
                initial_value = self._get_portfolio_value_at_date(start_date)
                if not initial_value or initial_value <= 0:
                    return None

                simple_return = (self.current_value / initial_value) - 1

                # Annualize if needed
                days = (end_date - start_date).days
                years = days / 365.25
                if years > 0 and years != 1:
                    annualized_return = ((1 + simple_return) ** (1 / years)) - 1
                    return annualized_return * 100
                else:
                    return simple_return * 100

            # Calculate TWR with cash flows using sub-periods
            sub_periods = self._create_twr_sub_periods(
                start_date, end_date, cash_flow_dates
            )

            if not sub_periods:
                return None

            # Calculate return for each sub-period
            sub_period_returns = []

            for period_start, period_end in sub_periods:
                sub_return = self._calculate_twr_sub_period_return(
                    period_start, period_end
                )
                if sub_return is not None:
                    sub_period_returns.append(sub_return)

            if not sub_period_returns:
                return None

            # Link sub-period returns geometrically
            twr = 1.0
            for sub_return in sub_period_returns:
                twr *= 1 + sub_return

            twr = twr - 1  # Convert back to return

            # Annualize if needed
            days = (end_date - start_date).days
            years = days / 365.25
            if years > 0 and years != 1:
                twr = ((1 + twr) ** (1 / years)) - 1

            return twr * 100

        except Exception as e:
            logger.error(f"TWR calculation failed: {e}")
            return None

    def _get_portfolio_value_at_date(self, target_date: datetime) -> float:
        """Get portfolio value at a specific date."""
        try:
            # Calculate quantity held at target date
            quantity_at_date = 0.0
            for txn in self.transactions:
                if txn["date"] <= target_date:
                    if txn["type"] == "BUY":
                        quantity_at_date += txn["quantity"]
                    elif txn["type"] == "SELL":
                        quantity_at_date -= txn["quantity"]

            if quantity_at_date <= 0:
                return 0.0

            # Get price at target date
            price_at_date = self.apple_processor.get_price_at_date(target_date)
            if not price_at_date:
                return None

            return quantity_at_date * price_at_date

        except Exception as e:
            logger.error(f"Error getting portfolio value at date {target_date}: {e}")
            return None

    def _create_twr_sub_periods(
        self, start_date: datetime, end_date: datetime, cash_flow_dates: List[datetime]
    ) -> List[tuple]:
        """Create sub-periods for TWR calculation."""
        period_dates = [start_date] + cash_flow_dates + [end_date]
        period_dates = sorted(list(set(period_dates)))

        sub_periods = []
        for i in range(len(period_dates) - 1):
            period_start = period_dates[i]
            period_end = period_dates[i + 1]

            if period_start != period_end:
                sub_periods.append((period_start, period_end))

        return sub_periods

    def _calculate_twr_sub_period_return(
        self, period_start: datetime, period_end: datetime
    ) -> Optional[float]:
        """Calculate return for a single sub-period using correct TWR formula."""
        try:
            # Get portfolio value at start and end of period
            start_value = self._get_portfolio_value_at_date(period_start)
            end_value = self._get_portfolio_value_at_date(period_end)

            if not start_value or start_value <= 0:
                return None
            if end_value is None:
                return None

            # Calculate net cash flow during the period
            net_cash_flow = 0.0
            for txn in self.transactions:
                if period_start < txn["date"] <= period_end:
                    if txn["type"] == "BUY":
                        net_cash_flow += (
                            txn["quantity"] * txn["price"]
                        )  # Positive inflow
                    elif txn["type"] == "SELL":
                        net_cash_flow -= (
                            txn["quantity"] * txn["price"]
                        )  # Negative outflow

            # Correct TWR formula: Return = (End Value - Net Cash Flow) / Start Value - 1
            sub_return = (end_value - net_cash_flow) / start_value - 1
            return sub_return

        except Exception as e:
            logger.error(f"Error calculating sub-period return: {e}")
            return None


class PortfolioCalculationTester:
    """Main test runner for portfolio calculations"""

    def __init__(self, apple_data_file: str):
        self.apple_processor = AppleDataProcessor(apple_data_file)
        self.scenarios = self._create_test_scenarios()

    def _create_test_scenarios(self) -> List[PortfolioScenario]:
        """Create various test scenarios"""
        scenarios = []

        # Scenario 1: Regular monthly investments over 2 years
        start_date = datetime.now() - relativedelta(years=2)
        transactions_1 = []

        for i in range(24):  # 24 months
            txn_date = start_date + relativedelta(months=i)
            # Get actual Apple price at that date
            price = self.apple_processor.get_price_at_date(txn_date)
            if price:
                quantity = 1000 / price  # $1000 investment each month
                transactions_1.append(
                    {
                        "date": txn_date,
                        "type": "BUY",
                        "quantity": quantity,
                        "price": price,
                    }
                )

        scenarios.append(
            PortfolioScenario(
                "Monthly Investment (2 years)", transactions_1, self.apple_processor
            )
        )

        # Scenario 2: Young portfolio (3 months old)
        start_date_2 = datetime.now() - relativedelta(months=3)
        transactions_2 = [
            {
                "date": start_date_2,
                "type": "BUY",
                "quantity": 100,
                "price": self.apple_processor.get_price_at_date(start_date_2) or 200.0,
            },
            {
                "date": start_date_2 + relativedelta(months=1),
                "type": "BUY",
                "quantity": 50,
                "price": self.apple_processor.get_price_at_date(
                    start_date_2 + relativedelta(months=1)
                )
                or 210.0,
            },
        ]

        scenarios.append(
            PortfolioScenario(
                "Young Portfolio (3 months)", transactions_2, self.apple_processor
            )
        )

        # Scenario 3: Buy and sell transactions
        start_date_3 = datetime.now() - relativedelta(years=1, months=6)
        transactions_3 = [
            {
                "date": start_date_3,
                "type": "BUY",
                "quantity": 200,
                "price": self.apple_processor.get_price_at_date(start_date_3) or 150.0,
            },
            {
                "date": start_date_3 + relativedelta(months=6),
                "type": "SELL",
                "quantity": 50,
                "price": self.apple_processor.get_price_at_date(
                    start_date_3 + relativedelta(months=6)
                )
                or 180.0,
            },
            {
                "date": start_date_3 + relativedelta(months=9),
                "type": "BUY",
                "quantity": 75,
                "price": self.apple_processor.get_price_at_date(
                    start_date_3 + relativedelta(months=9)
                )
                or 200.0,
            },
        ]

        scenarios.append(
            PortfolioScenario(
                "Buy-Sell Portfolio", transactions_3, self.apple_processor
            )
        )

        # Scenario 4: Simple lump sum investment
        start_date_4 = datetime.now() - relativedelta(years=1)
        price_4 = self.apple_processor.get_price_at_date(start_date_4) or 180.0
        transactions_4 = [
            {"date": start_date_4, "type": "BUY", "quantity": 100, "price": price_4}
        ]

        scenarios.append(
            PortfolioScenario("Lump Sum (1 year)", transactions_4, self.apple_processor)
        )

        return scenarios

    def test_scenario_calculations(self, scenario: PortfolioScenario):
        """Test calculations for a specific scenario"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing Scenario: {scenario.name}")
        logger.info(f"{'='*60}")

        results = {
            "scenario_name": scenario.name,
            "current_quantity": scenario.current_quantity,
            "current_price": scenario.current_price,
            "current_value": scenario.current_value,
            "transaction_count": len(scenario.transactions),
            "tests": {},
        }

        # Test 1: CAGR calculation (since inception)
        first_txn_date = min(txn["date"] for txn in scenario.transactions)
        cagr = scenario.calculate_manual_cagr(first_txn_date)
        results["tests"]["cagr_inception"] = cagr
        logger.info(
            f"CAGR (since inception): {cagr:.2f}%"
            if cagr
            else "CAGR: Could not calculate"
        )

        # Test 2: CAGR for last 1 year (if portfolio is old enough)
        one_year_ago = datetime.now() - relativedelta(years=1)
        if first_txn_date <= one_year_ago:
            cagr_1y = scenario.calculate_manual_cagr(one_year_ago)
            results["tests"]["cagr_1year"] = cagr_1y
            logger.info(
                f"CAGR (1 year): {cagr_1y:.2f}%"
                if cagr_1y
                else "CAGR (1 year): Could not calculate"
            )
        else:
            results["tests"]["cagr_1year"] = "Portfolio too young"
            logger.info("CAGR (1 year): Portfolio too young")

        # Test 3: XIRR calculation (since inception)
        xirr = scenario.calculate_manual_xirr()
        results["tests"]["xirr_inception"] = xirr
        logger.info(
            f"XIRR (since inception): {xirr:.2f}%"
            if xirr
            else "XIRR: Could not calculate"
        )

        # Test 3.5: TWR calculation (since inception)
        twr = scenario.calculate_manual_twr()
        results["tests"]["twr_inception"] = twr
        logger.info(
            f"TWR (since inception): {twr:.2f}%" if twr else "TWR: Could not calculate"
        )

        # Test 4: XIRR for last 1 year (if portfolio is old enough)
        if first_txn_date <= one_year_ago:
            xirr_1y = scenario.calculate_manual_xirr(one_year_ago)
            results["tests"]["xirr_1year"] = xirr_1y
            logger.info(
                f"XIRR (1 year): {xirr_1y:.2f}%"
                if xirr_1y
                else "XIRR (1 year): Could not calculate"
            )

            # Test 4.5: TWR for last 1 year
            twr_1y = scenario.calculate_manual_twr(one_year_ago)
            results["tests"]["twr_1year"] = twr_1y
            logger.info(
                f"TWR (1 year): {twr_1y:.2f}%"
                if twr_1y
                else "TWR (1 year): Could not calculate"
            )
        else:
            results["tests"]["xirr_1year"] = "Portfolio too young"
            results["tests"]["twr_1year"] = "Portfolio too young"
            logger.info("XIRR (1 year): Portfolio too young")
            logger.info("TWR (1 year): Portfolio too young")

        # Test 5: Cash flow analysis
        cash_flows = scenario.get_cash_flows()
        total_invested = sum(cf["amount"] for cf in cash_flows if cf["amount"] < 0)
        total_returned = sum(cf["amount"] for cf in cash_flows if cf["amount"] > 0)

        results["tests"]["total_invested"] = abs(total_invested)
        results["tests"]["total_returned"] = total_returned
        results["tests"]["absolute_return"] = (
            total_returned + total_invested
        )  # Net gain/loss

        logger.info(f"Total Invested: ${abs(total_invested):,.2f}")
        logger.info(f"Current Value: ${total_returned:,.2f}")
        logger.info(f"Absolute Return: ${total_returned + total_invested:,.2f}")

        return results

    def test_benchmark_comparison(self):
        """Test benchmark comparison logic"""
        logger.info(f"\n{'='*60}")
        logger.info("Testing Benchmark Comparison")
        logger.info(f"{'='*60}")

        # Use the monthly investment scenario
        scenario = self.scenarios[0]  # Monthly investment scenario

        # Create benchmark cash flows (same investment schedule, but in AAPL directly)
        benchmark_cash_flows = []
        benchmark_quantity = 0.0

        for txn in scenario.transactions:
            if txn["type"] == "BUY":
                benchmark_quantity += txn["quantity"]
                benchmark_cash_flows.append(
                    {"date": txn["date"], "amount": -txn["quantity"] * txn["price"]}
                )

        # Add current benchmark value
        current_benchmark_value = benchmark_quantity * scenario.current_price
        benchmark_cash_flows.append(
            {"date": datetime.now(), "amount": current_benchmark_value}
        )

        # Calculate benchmark XIRR
        dates = [cf["date"] for cf in benchmark_cash_flows]
        amounts = [cf["amount"] for cf in benchmark_cash_flows]
        benchmark_xirr = pyxirr.xirr(dates, amounts) * 100

        # Compare with portfolio XIRR
        portfolio_xirr = scenario.calculate_manual_xirr()

        logger.info(
            f"Portfolio XIRR: {portfolio_xirr:.2f}%"
            if portfolio_xirr
            else "Portfolio XIRR: Could not calculate"
        )
        logger.info(f"Benchmark XIRR: {benchmark_xirr:.2f}")

        if portfolio_xirr and benchmark_xirr:
            difference = portfolio_xirr - benchmark_xirr
            logger.info(f"Performance Difference: {difference:.2f}%")

            # Since both are investing in the same stock (AAPL), they should be very similar
            if abs(difference) < 1.0:
                logger.info(
                    "✅ Benchmark comparison working correctly (minimal difference)"
                )
                return True
            else:
                logger.warning(f"⚠️  Large difference detected: {difference:.2f}%")
                return False
        else:
            logger.error("❌ Could not compare - missing XIRR values")
            return False

    def run_all_tests(self):
        """Run all tests and provide summary"""
        logger.info("Starting comprehensive portfolio calculation tests...")

        all_results = []

        # Test each scenario
        for scenario in self.scenarios:
            try:
                results = self.test_scenario_calculations(scenario)
                results["status"] = "PASSED"
                all_results.append(results)
            except Exception as e:
                logger.error(f"❌ Scenario '{scenario.name}' failed: {e}")
                all_results.append(
                    {
                        "scenario_name": scenario.name,
                        "status": "FAILED",
                        "error": str(e),
                    }
                )

        # Test benchmark comparison
        try:
            benchmark_success = self.test_benchmark_comparison()
            all_results.append(
                {
                    "scenario_name": "Benchmark Comparison",
                    "status": "PASSED" if benchmark_success else "FAILED",
                }
            )
        except Exception as e:
            logger.error(f"❌ Benchmark comparison failed: {e}")
            all_results.append(
                {
                    "scenario_name": "Benchmark Comparison",
                    "status": "FAILED",
                    "error": str(e),
                }
            )

        # Print summary
        self._print_summary(all_results)

        return all_results

    def _print_summary(self, results: List[Dict]):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)

        passed = 0
        failed = 0

        for result in results:
            status = result.get("status", "UNKNOWN")
            if status == "PASSED":
                print(f"✅ {result['scenario_name']}: PASSED")
                passed += 1

                # Print key metrics if available
                if "tests" in result:
                    tests = result["tests"]
                    if tests.get("cagr_inception"):
                        print(f"   CAGR (inception): {tests['cagr_inception']:.2f}%")
                    if tests.get("xirr_inception"):
                        print(f"   XIRR (inception): {tests['xirr_inception']:.2f}%")
                    if tests.get("twr_inception"):
                        print(f"   TWR (inception): {tests['twr_inception']:.2f}%")
                    if tests.get("absolute_return"):
                        print(f"   Absolute Return: ${tests['absolute_return']:,.2f}")

            else:
                print(f"❌ {result['scenario_name']}: FAILED")
                if "error" in result:
                    print(f"   Error: {result['error']}")
                failed += 1

        print(f"\nTotal Tests: {len(results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {(passed/len(results)*100):.1f}%")

        if failed == 0:
            print(
                "\n🎉 All tests passed! Portfolio calculation service is working correctly."
            )
        else:
            print(f"\n⚠️  {failed} test(s) failed. Check the logs above for details.")


def main():
    """Main test runner"""
    try:
        tester = PortfolioCalculationTester("apple_market_data.json")
        results = tester.run_all_tests()
        return results
    except Exception as e:
        logger.error(f"Test runner failed: {e}")
        return []


if __name__ == "__main__":
    main()
