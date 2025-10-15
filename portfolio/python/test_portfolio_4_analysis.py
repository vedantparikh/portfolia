#!/usr/bin/env python3
"""
Test script to analyze portfolio 4 and identify benchmarking issues.
This script will help us understand the current state and fix the benchmarking problems.
"""

import asyncio
import os
import sys
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal

from sqlalchemy.orm import Session

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database.connection import SessionLocal
from app.core.database.models import Asset
from app.core.database.models import Portfolio
from app.core.database.models import PortfolioAsset
from app.core.database.models import Transaction
from app.core.database.models import TransactionType
from core.services.utils import PeriodType
from app.core.services.portfolio_calculation_service import PortfolioCalculationService


async def analyze_portfolio_4():
    """Analyze portfolio 4 data and test calculations."""
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Check if portfolio 4 exists
        portfolio = db.query(Portfolio).filter(Portfolio.id == 4).first()
        if not portfolio:
            print("Portfolio 4 not found!")
            return
        
        print(f"Portfolio 4 Analysis:")
        print(f"- ID: {portfolio.id}")
        print(f"- Name: {portfolio.name}")
        print(f"- User ID: {portfolio.user_id}")
        print(f"- Currency: {portfolio.currency}")
        print(f"- Created: {portfolio.created_at}")
        print(f"- Is Active: {portfolio.is_active}")
        
        # Get all transactions
        transactions = db.query(Transaction).filter(Transaction.portfolio_id == 4).order_by(Transaction.transaction_date).all()
        print(f"\nTotal Transactions: {len(transactions)}")
        
        if not transactions:
            print("No transactions found for portfolio 4")
            return
        
        # Analyze transactions
        first_transaction = transactions[0]
        last_transaction = transactions[-1]
        
        print(f"\nTransaction Analysis:")
        print(f"- First transaction: {first_transaction.transaction_date} - {first_transaction.transaction_type.value}")
        print(f"- Last transaction: {last_transaction.transaction_date} - {last_transaction.transaction_type.value}")
        print(f"- Time span: {(last_transaction.transaction_date - first_transaction.transaction_date).days} days")
        
        # Show detailed transaction breakdown
        print(f"\nDetailed Transactions:")
        for i, tx in enumerate(transactions[:10]):  # Show first 10
            print(f"  {i+1}. {tx.transaction_date} | {tx.transaction_type.value} | "
                  f"{tx.asset.symbol if tx.asset else 'N/A'} | "
                  f"Qty: {tx.quantity} | Price: ${tx.price} | Total: ${tx.total_amount}")
        
        if len(transactions) > 10:
            print(f"  ... and {len(transactions) - 10} more transactions")
        
        # Get current portfolio assets
        portfolio_assets = db.query(PortfolioAsset).filter(PortfolioAsset.portfolio_id == 4).all()
        print(f"\nCurrent Portfolio Assets: {len(portfolio_assets)}")
        
        for asset in portfolio_assets:
            if asset.quantity and float(asset.quantity) > 0:
                print(f"- {asset.asset.symbol if asset.asset else 'Unknown'}: "
                      f"Qty {asset.quantity} | "
                      f"Cost Basis: ${asset.cost_basis_total} | "
                      f"Current Value: ${asset.current_value or 'N/A'}")
        
        # Test portfolio calculations
        print(f"\n" + "="*50)
        print("TESTING PORTFOLIO CALCULATIONS")
        print("="*50)
        
        service = PortfolioCalculationService(db)
        
        # Test different periods
        periods_to_test = [
            PeriodType.INCEPTION,
            PeriodType.LAST_6_MONTHS,
            PeriodType.LAST_1_YEAR,
            PeriodType.YTD
        ]
        
        for period in periods_to_test:
            print(f"\n--- Testing Period: {period} ---")
            try:
                result = await service.calculate_portfolio_performance(
                    portfolio_id=4,
                    user_id=portfolio.user_id,
                    period=period
                )
                
                print(f"Portfolio Performance ({period}):")
                print(f"- Start Date: {result.get('start_date')}")
                print(f"- End Date: {result.get('end_date')}")
                print(f"- Current Value: ${result.get('current_value', 0):,.2f}")
                
                metrics = result.get('metrics', {})
                print(f"- CAGR: {metrics.get('cagr')}")
                print(f"- XIRR: {metrics.get('xirr')}")
                print(f"- TWR: {metrics.get('twr')}")
                print(f"- MWR: {metrics.get('mwr')}")
                print(f"- Volatility: {metrics.get('volatility')}")
                print(f"- Sharpe Ratio: {metrics.get('sharpe_ratio')}")
                print(f"- Max Drawdown: {metrics.get('max_drawdown')}")
                
            except Exception as e:
                print(f"Error calculating {period}: {e}")
        
        # Test benchmark comparison
        print(f"\n" + "="*50)
        print("TESTING BENCHMARK COMPARISON")
        print("="*50)
        
        benchmark_symbol = "AAPL"
        
        for period in periods_to_test:
            print(f"\n--- Testing Benchmark Comparison: {period} vs {benchmark_symbol} ---")
            try:
                comparison = await service.compare_portfolio_to_benchmark(
                    portfolio_id=4,
                    user_id=portfolio.user_id,
                    benchmark_symbol=benchmark_symbol,
                    period=period
                )
                
                portfolio_perf = comparison.get('portfolio_performance', {})
                benchmark_perf = comparison.get('benchmark_performance', {})
                comparison_metrics = comparison.get('comparison', {})
                
                print(f"Portfolio vs Benchmark ({period}):")
                print(f"Portfolio CAGR: {portfolio_perf.get('metrics', {}).get('cagr')}")
                print(f"Benchmark CAGR: {benchmark_perf.get('metrics', {}).get('cagr')}")
                print(f"CAGR Difference: {comparison_metrics.get('cagr_difference')}")
                print(f"Portfolio TWR: {portfolio_perf.get('metrics', {}).get('twr')}")
                print(f"Benchmark TWR: {benchmark_perf.get('metrics', {}).get('twr')}")
                print(f"TWR Difference: {comparison_metrics.get('twr_difference')}")
                print(f"Outperforming: {comparison_metrics.get('outperforming')}")
                
                if benchmark_perf.get('error'):
                    print(f"Benchmark Error: {benchmark_perf.get('error')}")
                
            except Exception as e:
                print(f"Error in benchmark comparison for {period}: {e}")
        
        # Test specific date range scenarios
        print(f"\n" + "="*50)
        print("TESTING ALIGNED START DATE LOGIC")
        print("="*50)
        
        # Find actual first transaction date within 6 months
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        
        transactions_in_6m = [t for t in transactions if t.transaction_date >= six_months_ago]
        
        if transactions_in_6m:
            actual_start_date = transactions_in_6m[0].transaction_date
            print(f"6-month period requested, but actual first transaction in period: {actual_start_date}")
            print(f"Suggested aligned calculation period: {(datetime.now(timezone.utc) - actual_start_date).days} days")
        else:
            print("No transactions in the last 6 months - this is where the issue occurs!")
            
        # Test with 1 year period
        one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
        transactions_in_1y = [t for t in transactions if t.transaction_date >= one_year_ago]
        
        if transactions_in_1y:
            actual_start_date = transactions_in_1y[0].transaction_date
            print(f"1-year period requested, but actual first transaction in period: {actual_start_date}")
            print(f"Suggested aligned calculation period: {(datetime.now(timezone.utc) - actual_start_date).days} days")
        else:
            print("No transactions in the last 1 year")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(analyze_portfolio_4())
            actual_start_date = transactions_in_1y[0].transaction_date
            print(f"1-year period requested, but actual first transaction in period: {actual_start_date}")
            print(f"Suggested aligned calculation period: {(datetime.now(timezone.utc) - actual_start_date).days} days")
        else:
            print("No transactions in the last 1 year")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(analyze_portfolio_4())
