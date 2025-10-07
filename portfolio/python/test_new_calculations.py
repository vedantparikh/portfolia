#!/usr/bin/env python3
"""
Test script for the new CAGR and XIRR calculations.
This script demonstrates the key concepts and formulas implemented.
"""

from datetime import datetime, timezone
from typing import List, NamedTuple

import pyxirr


class CashFlow(NamedTuple):
    """Represents a cash flow with date and amount."""

    date: datetime
    amount: float  # Positive for inflows, negative for outflows


def calculate_cagr(beginning_value: float, ending_value: float, years: float) -> float:
    """
    Calculate CAGR using the formula: (Ending Value / Beginning Value)^(1/Years) - 1

    Args:
        beginning_value: Initial investment value
        ending_value: Final investment value
        years: Time period in years

    Returns:
        CAGR as a percentage
    """
    if beginning_value <= 0 or years <= 0:
        return 0.0

    if years > 1:
        # Annualized CAGR for periods > 1 year
        cagr = ((ending_value / beginning_value) ** (1 / years)) - 1
    else:
        # Simple return for periods <= 1 year
        cagr = (ending_value / beginning_value) - 1

    return cagr * 100


def calculate_xirr(cash_flows: List[CashFlow]) -> float:
    """
    Calculate XIRR for irregular cash flows.

    Args:
        cash_flows: List of cash flows with dates and amounts

    Returns:
        XIRR as a percentage
    """
    dates = [cf.date for cf in cash_flows]
    amounts = [cf.amount for cf in cash_flows]

    # Validate data
    if len(dates) < 2:
        return 0.0

    has_positive = any(a > 0 for a in amounts)
    has_negative = any(a < 0 for a in amounts)

    if not (has_positive and has_negative):
        return 0.0

    try:
        xirr_result = pyxirr.xirr(dates, amounts)
        return xirr_result * 100 if xirr_result is not None else 0.0
    except Exception as e:
        print(f"XIRR calculation error: {e}")
        return 0.0


def test_cagr_examples():
    """Test CAGR calculations with various scenarios."""
    print("=== CAGR Test Examples ===")

    # Example 1: 2-year investment
    print("\n1. Two-year investment:")
    print("   Initial: $10,000, Final: $12,100, Period: 2 years")
    cagr1 = calculate_cagr(10000, 12100, 2.0)
    print(f"   CAGR: {cagr1:.2f}%")

    # Example 2: 6-month investment
    print("\n2. Six-month investment:")
    print("   Initial: $5,000, Final: $5,250, Period: 0.5 years")
    cagr2 = calculate_cagr(5000, 5250, 0.5)
    print(f"   Simple Return: {cagr2:.2f}%")

    # Example 3: 5-year investment
    print("\n3. Five-year investment:")
    print("   Initial: $1,000, Final: $1,610, Period: 5 years")
    cagr3 = calculate_cagr(1000, 1610, 5.0)
    print(f"   CAGR: {cagr3:.2f}%")


def test_xirr_examples():
    """Test XIRR calculations with various cash flow scenarios."""
    print("\n=== XIRR Test Examples ===")

    # Example 1: Regular monthly investments
    print("\n1. Regular monthly investments:")
    cash_flows1 = [
        CashFlow(
            datetime(2023, 1, 1, tzinfo=timezone.utc), -1000
        ),  # Initial investment
        CashFlow(
            datetime(2023, 2, 1, tzinfo=timezone.utc), -1000
        ),  # Monthly investment
        CashFlow(
            datetime(2023, 3, 1, tzinfo=timezone.utc), -1000
        ),  # Monthly investment
        CashFlow(
            datetime(2023, 4, 1, tzinfo=timezone.utc), -1000
        ),  # Monthly investment
        CashFlow(
            datetime(2023, 5, 1, tzinfo=timezone.utc), -1000
        ),  # Monthly investment
        CashFlow(
            datetime(2023, 6, 1, tzinfo=timezone.utc), -1000
        ),  # Monthly investment
        CashFlow(datetime(2023, 12, 31, tzinfo=timezone.utc), 6500),  # Final value
    ]

    print("   Cash flows: -$1000 monthly for 6 months, final value $6500")
    xirr1 = calculate_xirr(cash_flows1)
    print(f"   XIRR: {xirr1:.2f}%")

    # Example 2: Irregular investments with a sale
    print("\n2. Irregular investments with partial sale:")
    cash_flows2 = [
        CashFlow(
            datetime(2022, 1, 15, tzinfo=timezone.utc), -5000
        ),  # Initial investment
        CashFlow(
            datetime(2022, 6, 10, tzinfo=timezone.utc), -2000
        ),  # Additional investment
        CashFlow(datetime(2022, 9, 20, tzinfo=timezone.utc), 1500),  # Partial sale
        CashFlow(datetime(2023, 3, 25, tzinfo=timezone.utc), -1000),  # More investment
        CashFlow(datetime(2024, 1, 1, tzinfo=timezone.utc), 8000),  # Final value
    ]

    print("   Cash flows: -$5000, -$2000, +$1500, -$1000, final value $8000")
    xirr2 = calculate_xirr(cash_flows2)
    print(f"   XIRR: {xirr2:.2f}%")

    # Example 3: Single lump sum investment
    print("\n3. Single lump sum investment:")
    cash_flows3 = [
        CashFlow(
            datetime(2021, 1, 1, tzinfo=timezone.utc), -10000
        ),  # Initial investment
        CashFlow(
            datetime(2024, 1, 1, tzinfo=timezone.utc), 13500
        ),  # Final value after 3 years
    ]

    print("   Cash flows: -$10000 initial, $13500 final after 3 years")
    xirr3 = calculate_xirr(cash_flows3)
    print(f"   XIRR: {xirr3:.2f}%")

    # Compare with CAGR for the same scenario
    cagr3 = calculate_cagr(10000, 13500, 3.0)
    print(f"   CAGR (for comparison): {cagr3:.2f}%")
    print(
        "   Note: XIRR and CAGR should be very similar for single lump sum investments"
    )


def demonstrate_period_calculations():
    """Demonstrate how to calculate metrics for different periods."""
    print("\n=== Period Calculation Examples ===")

    # Simulate a portfolio with transactions over time
    all_cash_flows = [
        CashFlow(
            datetime(2020, 1, 1, tzinfo=timezone.utc), -5000
        ),  # Initial investment
        CashFlow(
            datetime(2020, 6, 1, tzinfo=timezone.utc), -2000
        ),  # Additional investment
        CashFlow(datetime(2021, 3, 1, tzinfo=timezone.utc), -1500),  # More investment
        CashFlow(datetime(2022, 1, 1, tzinfo=timezone.utc), -1000),  # More investment
        CashFlow(datetime(2022, 8, 1, tzinfo=timezone.utc), 2000),  # Partial sale
        CashFlow(datetime(2023, 6, 1, tzinfo=timezone.utc), -3000),  # More investment
    ]

    # Current portfolio value
    current_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    current_value = 15000

    print(f"Portfolio transactions from 2020-2024, current value: ${current_value:,}")

    # Calculate inception XIRR
    inception_flows = all_cash_flows + [CashFlow(current_date, current_value)]
    inception_xirr = calculate_xirr(inception_flows)
    print(f"Inception XIRR: {inception_xirr:.2f}%")

    # Calculate last 2 years XIRR
    two_years_ago = datetime(2022, 1, 1, tzinfo=timezone.utc)

    # For period calculations, we need:
    # 1. Portfolio value at start of period (would need to calculate from holdings)
    # 2. Cash flows within the period
    # 3. Current value

    # Simulate portfolio value 2 years ago (this would be calculated from actual holdings)
    portfolio_value_2_years_ago = 8500

    # Get cash flows from last 2 years
    period_flows = [cf for cf in all_cash_flows if cf.date >= two_years_ago]

    # Create XIRR calculation for 2-year period
    two_year_flows = (
        [
            CashFlow(
                two_years_ago, -portfolio_value_2_years_ago
            )  # Initial value as outflow
        ]
        + period_flows
        + [CashFlow(current_date, current_value)]  # Current value as inflow
    )

    two_year_xirr = calculate_xirr(two_year_flows)
    print(f"Last 2 years XIRR: {two_year_xirr:.2f}%")

    # Calculate 2-year CAGR for comparison
    two_year_cagr = calculate_cagr(portfolio_value_2_years_ago, current_value, 2.0)
    print(f"Last 2 years CAGR: {two_year_cagr:.2f}%")

    print("\nNote: XIRR accounts for timing of cash flows, while CAGR assumes")
    print("      a single investment at the beginning of the period.")


def main():
    """Run all test examples."""
    print("Portfolio Performance Calculation Tests")
    print("=" * 50)

    test_cagr_examples()
    test_xirr_examples()
    demonstrate_period_calculations()

    print("\n" + "=" * 50)
    print("Key Concepts Demonstrated:")
    print("1. CAGR measures compound growth rate between two points in time")
    print("2. XIRR accounts for timing and size of all cash flows")
    print("3. For periods <= 1 year, we return simple returns instead of annualizing")
    print("4. Period calculations require portfolio values at period boundaries")
    print("5. Benchmark comparison applies same cash flows to benchmark symbol")


if __name__ == "__main__":
    main()
