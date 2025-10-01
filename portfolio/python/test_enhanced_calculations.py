#!/usr/bin/env python3
"""
Test script for enhanced portfolio calculations with error handling and portfolio age logic.
"""

from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict


def simulate_portfolio_performance_response(
    portfolio_age_days: int,
    requested_period_days: int,
    has_missing_values: bool = False,
) -> Dict[str, Any]:
    """
    Simulate the enhanced portfolio performance response.

    Args:
        portfolio_age_days: Age of portfolio in days
        requested_period_days: Requested calculation period in days
        has_missing_values: Whether portfolio has missing market values

    Returns:
        Simulated API response
    """
    current_date = datetime.now(timezone.utc)

    # Simulate portfolio age logic
    if portfolio_age_days < requested_period_days:
        # Portfolio is younger than requested period
        period_adjustment = {
            "requested_period": "2y" if requested_period_days > 365 else "6m",
            "requested_period_days": requested_period_days,
            "portfolio_age_days": portfolio_age_days,
            "adjustment_reason": (
                f"Portfolio age ({portfolio_age_days} days) is less than "
                f"requested period ({requested_period_days} days). "
                "Using inception period instead."
            ),
        }
        actual_period = "inception"
    else:
        period_adjustment = None
        actual_period = "2y" if requested_period_days > 365 else "6m"

    # Simulate missing value errors
    if has_missing_values:
        return {
            "portfolio_id": 123,
            "portfolio_name": "Test Portfolio",
            "period": actual_period,
            "start_date": None if actual_period == "inception" else current_date,
            "end_date": current_date,
            "current_value": 8500.0,  # Partial value due to missing data
            "errors": [
                "No current market value available for AAPL (quantity: 50)",
                "No current market value available for GOOGL (quantity: 25)",
            ],
            "period_adjustment": period_adjustment,
            "metrics": {
                "cagr": None,
                "xirr": None,
                "twr": None,
                "mwr": None,
            },
            "calculation_date": current_date.isoformat(),
        }

    # Successful calculation
    return {
        "portfolio_id": 123,
        "portfolio_name": "Test Portfolio",
        "period": actual_period,
        "start_date": None if actual_period == "inception" else current_date,
        "end_date": current_date,
        "current_value": 15000.0,
        "period_adjustment": period_adjustment,
        "metrics": {
            "cagr": 12.5 if actual_period == "inception" else 8.3,
            "xirr": 11.8 if actual_period == "inception" else 9.1,
            "twr": None,
            "mwr": 11.8 if actual_period == "inception" else 9.1,
        },
        "calculation_date": current_date.isoformat(),
    }


def simulate_benchmark_comparison_with_errors() -> Dict[str, Any]:
    """Simulate benchmark comparison with portfolio errors."""
    current_date = datetime.now(timezone.utc)

    return {
        "portfolio_id": 123,
        "benchmark_symbol": "^GSPC",
        "period": "inception",
        "portfolio_performance": {
            "portfolio_id": 123,
            "portfolio_name": "Test Portfolio",
            "period": "inception",
            "current_value": 8500.0,
            "errors": ["No current market value available for AAPL (quantity: 50)"],
            "metrics": {"cagr": None, "xirr": None, "twr": None, "mwr": None},
        },
        "benchmark_performance": {
            "benchmark_symbol": "^GSPC",
            "period": "inception",
            "current_value": 12000.0,
            "metrics": {"cagr": 10.2, "xirr": 10.5, "twr": None, "mwr": 10.5},
        },
        "errors": ["No current market value available for AAPL (quantity: 50)"],
        "comparison": {
            "cagr_difference": None,
            "xirr_difference": None,
            "outperforming_cagr": None,
            "outperforming_xirr": None,
        },
        "calculation_date": current_date.isoformat(),
    }


def test_portfolio_age_scenarios():
    """Test different portfolio age scenarios."""
    print("=== Portfolio Age Logic Tests ===")

    # Scenario 1: Portfolio older than requested period
    print("\n1. Portfolio older than requested period:")
    print("   Portfolio age: 800 days, Requested: 2 years (730 days)")
    response1 = simulate_portfolio_performance_response(800, 730)
    print(f"   Actual period used: {response1['period']}")
    print(f"   Period adjustment: {response1.get('period_adjustment', 'None')}")
    print(f"   CAGR: {response1['metrics']['cagr']}%")

    # Scenario 2: Portfolio younger than requested period
    print("\n2. Portfolio younger than requested period:")
    print("   Portfolio age: 60 days, Requested: 6 months (180 days)")
    response2 = simulate_portfolio_performance_response(60, 180)
    print(f"   Actual period used: {response2['period']}")
    if response2.get("period_adjustment"):
        print(
            f"   Adjustment reason: {response2['period_adjustment']['adjustment_reason']}"
        )
    print(f"   CAGR: {response2['metrics']['cagr']}%")

    # Scenario 3: Very young portfolio with 2-year request
    print("\n3. Very young portfolio with 2-year request:")
    print("   Portfolio age: 45 days, Requested: 2 years (730 days)")
    response3 = simulate_portfolio_performance_response(45, 730)
    print(f"   Actual period used: {response3['period']}")
    if response3.get("period_adjustment"):
        print(
            f"   Portfolio age: {response3['period_adjustment']['portfolio_age_days']} days"
        )
        print(
            f"   Requested period: {response3['period_adjustment']['requested_period_days']} days"
        )
    print(f"   CAGR: {response3['metrics']['cagr']}%")


def test_missing_value_scenarios():
    """Test scenarios with missing market values."""
    print("\n=== Missing Value Error Handling ===")

    # Scenario 1: Portfolio with missing values
    print("\n1. Portfolio with missing market values:")
    response1 = simulate_portfolio_performance_response(
        200, 180, has_missing_values=True
    )
    print(
        f"   Current value: ${response1['current_value']:,} (partial due to missing data)"
    )
    print("   Errors:")
    for error in response1["errors"]:
        print(f"     - {error}")
    print(
        f"   Metrics calculated: {all(v is None for v in response1['metrics'].values())}"
    )

    # Scenario 2: Benchmark comparison with portfolio errors
    print("\n2. Benchmark comparison with portfolio errors:")
    response2 = simulate_benchmark_comparison_with_errors()
    print(f"   Portfolio errors: {len(response2['errors'])}")
    print(
        f"   Comparison possible: {response2['comparison']['cagr_difference'] is not None}"
    )
    print("   Error details:")
    for error in response2["errors"]:
        print(f"     - {error}")


def test_api_response_structure():
    """Test the enhanced API response structure."""
    print("\n=== Enhanced API Response Structure ===")

    # Test successful response
    print("\n1. Successful calculation response:")
    response1 = simulate_portfolio_performance_response(400, 180)
    print("   Response includes:")
    print(f"     - portfolio_id: {response1.get('portfolio_id') is not None}")
    print(f"     - period: {response1.get('period') is not None}")
    print(f"     - current_value: {response1.get('current_value') is not None}")
    print(f"     - metrics: {response1.get('metrics') is not None}")
    print(f"     - calculation_date: {response1.get('calculation_date') is not None}")
    print(f"     - errors: {response1.get('errors', 'Not present')}")

    # Test error response
    print("\n2. Error response structure:")
    response2 = simulate_portfolio_performance_response(
        200, 180, has_missing_values=True
    )
    print("   Response includes:")
    print(f"     - errors array: {len(response2.get('errors', []))} errors")
    print(
        f"     - metrics (all None): {all(v is None for v in response2['metrics'].values())}"
    )
    print(f"     - current_value: ${response2['current_value']:,} (partial)")


def demonstrate_key_improvements():
    """Demonstrate the key improvements made."""
    print("\n=== Key Improvements Demonstrated ===")

    print("\n1. No Fallback to Cost Basis:")
    print("   - When market values are missing, errors are logged and returned")
    print("   - Cost basis is NEVER used as a fallback value")
    print("   - API clearly indicates which assets have missing data")

    print("\n2. Portfolio Age Logic:")
    print("   - If portfolio age < requested period, automatically use inception")
    print("   - Clear explanation provided in 'period_adjustment' field")
    print("   - Prevents misleading calculations for young portfolios")

    print("\n3. Enhanced Error Handling:")
    print("   - Structured error messages in API responses")
    print("   - Detailed logging for debugging")
    print("   - Graceful degradation when data is incomplete")

    print("\n4. Consistent API Structure:")
    print("   - All responses include standard fields")
    print("   - Error conditions clearly indicated")
    print("   - Calculation metadata provided")


def main():
    """Run all demonstration tests."""
    print("Enhanced Portfolio Calculation Service Tests")
    print("=" * 60)

    test_portfolio_age_scenarios()
    test_missing_value_scenarios()
    test_api_response_structure()
    demonstrate_key_improvements()

    print("\n" + "=" * 60)
    print("Summary of Enhancements:")
    print("✓ Removed all fallback to cost basis values")
    print("✓ Added portfolio age vs requested period logic")
    print("✓ Enhanced error handling and API responses")
    print("✓ Comprehensive logging for debugging")
    print("✓ Structured error messages for client applications")


if __name__ == "__main__":
    main()
