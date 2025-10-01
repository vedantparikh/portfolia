# Portfolio Calculations API Specification

## Overview

The Portfolio Calculations API provides comprehensive performance metrics including CAGR, XIRR, TWR (Time-Weighted Return), and MWR (Money-Weighted Return) calculations. All endpoints support multiple time periods and include benchmark comparison capabilities.

**Base URL**: `/api/v1/calculations`

## Authentication

All endpoints require authentication via Bearer token:

```
Authorization: Bearer <your_jwt_token>
```

## Available Periods

### GET `/periods`

Get list of available calculation periods.

**Response**: `AvailablePeriodsResponse`

```json
{
  "periods": [
    {
      "key": "3m",
      "name": "Last 3 Months",
      "description": "Performance over the last 3 months"
    },
    {
      "key": "6m",
      "name": "Last 6 Months",
      "description": "Performance over the last 6 months"
    },
    {
      "key": "1y",
      "name": "Last 1 Year",
      "description": "Performance over the last 12 months"
    },
    {
      "key": "2y",
      "name": "Last 2 Years",
      "description": "Performance over the last 24 months"
    },
    {
      "key": "3y",
      "name": "Last 3 Years",
      "description": "Performance over the last 36 months"
    },
    {
      "key": "5y",
      "name": "Last 5 Years",
      "description": "Performance over the last 60 months"
    },
    {
      "key": "ytd",
      "name": "Year to Date",
      "description": "Performance from January 1st to current date"
    },
    {
      "key": "inception",
      "name": "Since Inception",
      "description": "Performance since portfolio creation"
    }
  ]
}
```

## Portfolio Performance Calculations

### POST `/portfolio/{portfolio_id}/performance`

Calculate comprehensive portfolio performance metrics.

**Path Parameters**:

- `portfolio_id` (integer): Portfolio ID

**Request Body**: `PerformanceCalculationRequest`

```json
{
  "period": "1y",
  "end_date": "2024-12-31T23:59:59Z" // Optional
}
```

**Response**: `PortfolioPerformanceResponse`

```json
{
  "portfolio_id": 123,
  "portfolio_name": "Growth Portfolio",
  "period": "1y",
  "start_date": "2023-12-31T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "current_value": 125000.5,
  "metrics": {
    "cagr": 12.45, // Compound Annual Growth Rate (%)
    "xirr": 11.89, // Extended Internal Rate of Return (%)
    "twr": 12.12, // Time-Weighted Return (%)
    "mwr": 11.89, // Money-Weighted Return (%) - same as XIRR
    "volatility": 15.67, // Portfolio volatility (%)
    "max_drawdown": -8.23 // Maximum drawdown (%)
  },
  "calculation_date": "2024-12-31T23:59:59Z",
  "error": null,
  "errors": [], // List of any calculation errors
  "period_adjustment": {
    // Present if period was adjusted due to portfolio age
    "requested_period": "1y",
    "actual_period": "inception",
    "adjustment_reason": "Portfolio age (6 months) is less than requested period (1 year)"
  }
}
```

### GET `/portfolio/{portfolio_id}/performance`

Get portfolio performance metrics (query parameter version).

**Path Parameters**:

- `portfolio_id` (integer): Portfolio ID

**Query Parameters**:

- `period` (string, default: "inception"): Calculation period
- `end_date` (datetime, optional): End date for calculation

**Response**: Same as POST version above.

### GET `/portfolio/{portfolio_id}/multi-period`

Calculate portfolio performance across multiple periods.

**Path Parameters**:

- `portfolio_id` (integer): Portfolio ID

**Query Parameters**:

- `periods` (array[string], default: ["3m", "6m", "1y", "ytd", "inception"]): List of periods
- `end_date` (datetime, optional): End date for calculations

**Response**: `MultiPeriodPerformanceResponse`

```json
{
  "portfolio_id": 123,
  "portfolio_name": "Growth Portfolio",
  "calculation_date": "2024-12-31T23:59:59Z",
  "periods": {
    "3m": {
      "portfolio_id": 123,
      "portfolio_name": "Growth Portfolio",
      "period": "3m",
      "start_date": "2024-09-30T00:00:00Z",
      "end_date": "2024-12-31T23:59:59Z",
      "current_value": 125000.5,
      "metrics": {
        "cagr": 8.45,
        "xirr": 8.12,
        "twr": 8.23,
        "mwr": 8.12,
        "volatility": 12.34,
        "max_drawdown": -3.45
      },
      "calculation_date": "2024-12-31T23:59:59Z"
    },
    "1y": {
      // ... similar structure for 1 year period
    },
    "inception": {
      // ... similar structure for inception period
    }
  }
}
```

## Asset-Specific Performance

### POST `/portfolio/{portfolio_id}/asset/{asset_id}/performance`

Calculate performance metrics for a specific asset within a portfolio.

**Path Parameters**:

- `portfolio_id` (integer): Portfolio ID
- `asset_id` (integer): Asset ID

**Request Body**: `AssetPerformanceCalculationRequest`

```json
{
  "period": "1y",
  "end_date": "2024-12-31T23:59:59Z" // Optional
}
```

**Response**: `AssetPerformanceResponse`

```json
{
  "portfolio_id": 123,
  "asset_id": 456,
  "asset_symbol": "AAPL",
  "asset_name": "Apple Inc.",
  "period": "1y",
  "start_date": "2023-12-31T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "current_value": 25000.0,
  "quantity": 100.0,
  "average_cost": 180.5,
  "current_price": 250.0,
  "metrics": {
    "cagr": 38.47,
    "xirr": 35.23,
    "twr": 36.12,
    "mwr": 35.23,
    "volatility": 22.15,
    "max_drawdown": -12.34
  },
  "calculation_date": "2024-12-31T23:59:59Z"
}
```

### GET `/portfolio/{portfolio_id}/asset/{asset_id}/multi-period`

Calculate asset performance across multiple periods.

**Response**: `AssetMultiPeriodPerformanceResponse` (similar structure to portfolio multi-period)

## Benchmark Performance

### POST `/benchmark/performance`

Calculate hypothetical performance if money was invested in a benchmark.

**Request Body**: `BenchmarkPerformanceCalculationRequest`

```json
{
  "benchmark_symbol": "SPY",
  "investment_schedule": [
    {
      "date": "2023-01-01T00:00:00Z",
      "amount": 10000.0
    },
    {
      "date": "2023-06-01T00:00:00Z",
      "amount": 5000.0
    }
  ],
  "period": "1y",
  "end_date": "2024-12-31T23:59:59Z" // Optional
}
```

**Response**: `BenchmarkPerformanceResponse`

```json
{
  "benchmark_symbol": "SPY",
  "period": "1y",
  "start_date": "2023-12-31T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "current_value": 18500.0,
  "total_invested_period": 15000.0,
  "metrics": {
    "cagr": 23.33,
    "xirr": 22.45,
    "twr": 22.89,
    "mwr": 22.45,
    "volatility": 16.78,
    "max_drawdown": -9.12
  },
  "calculation_date": "2024-12-31T23:59:59Z"
}
```

## Portfolio vs Benchmark Comparison

### GET `/portfolio/{portfolio_id}/compare/{benchmark_symbol}`

Compare portfolio performance against a benchmark.

**Path Parameters**:

- `portfolio_id` (integer): Portfolio ID
- `benchmark_symbol` (string): Benchmark symbol (e.g., "SPY", "QQQ", "AAPL")

**Query Parameters**:

- `period` (string, default: "inception"): Comparison period
- `end_date` (datetime, optional): End date for comparison

**Response**: `PortfolioBenchmarkComparisonResponse`

```json
{
  "portfolio_performance": {
    // Full PortfolioPerformanceResponse structure
    "portfolio_id": 123,
    "metrics": {
      "cagr": 12.45,
      "xirr": 11.89,
      "twr": 12.12,
      "mwr": 11.89
    }
    // ... other portfolio fields
  },
  "benchmark_performance": {
    // Full BenchmarkPerformanceResponse structure
    "benchmark_symbol": "SPY",
    "metrics": {
      "cagr": 10.23,
      "xirr": 9.87,
      "twr": 10.05,
      "mwr": 9.87
    }
    // ... other benchmark fields
  },
  "comparison": {
    "cagr_difference": 2.22, // Portfolio CAGR - Benchmark CAGR
    "xirr_difference": 2.02, // Portfolio XIRR - Benchmark XIRR
    "twr_difference": 2.07, // Portfolio TWR - Benchmark TWR
    "mwr_difference": 2.02, // Portfolio MWR - Benchmark MWR
    "outperforming_cagr": true, // Portfolio CAGR > Benchmark CAGR
    "outperforming_xirr": true, // Portfolio XIRR > Benchmark XIRR
    "outperforming_twr": true, // Portfolio TWR > Benchmark TWR
    "outperforming": true // Overall outperformance indicator
  }
}
```

## Performance Metrics Explained

### CAGR (Compound Annual Growth Rate)

- **Definition**: The geometric progression ratio that provides a constant rate of return over the time period
- **Formula**: `(Ending Value / Beginning Value)^(1/years) - 1`
- **Use Case**: Best for comparing investments over different time periods
- **Note**: Assumes a single lump sum investment

### XIRR (Extended Internal Rate of Return)

- **Definition**: Internal rate of return for irregular cash flows (investments/withdrawals)
- **Formula**: Iterative calculation that finds the rate where NPV = 0
- **Use Case**: Most accurate for portfolios with multiple cash flows at different times
- **Note**: Accounts for timing of cash flows

### TWR (Time-Weighted Return) ⭐ **NEW**

- **Definition**: Compound rate of growth that eliminates the distorting effects of cash flows
- **Formula**: Links sub-period returns geometrically: `[(1 + R1) × (1 + R2) × ... × (1 + Rn)] - 1`
- **Use Case**: Best for evaluating investment manager performance
- **Note**: Removes impact of investor cash flow timing decisions

### MWR (Money-Weighted Return)

- **Definition**: Internal rate of return that accounts for the timing and size of cash flows
- **Implementation**: Currently aliased to XIRR (same calculation)
- **Use Case**: Measures the actual return experienced by the investor

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Error Codes

- **400 Bad Request**: Invalid parameters or calculation errors
- **404 Not Found**: Portfolio or asset not found
- **500 Internal Server Error**: Server-side calculation errors

### Calculation-Specific Errors

When calculations cannot be performed, the response includes:

```json
{
  "portfolio_id": 123,
  "metrics": {
    "cagr": null,
    "xirr": null,
    "twr": null,
    "mwr": null
  },
  "errors": [
    "No current market value available for asset AAPL",
    "Insufficient transaction history for XIRR calculation"
  ]
}
```

## Period Adjustment Logic

When a portfolio is younger than the requested period:

- The system automatically adjusts to "inception" period
- A `period_adjustment` object is included in the response
- This ensures meaningful results for new portfolios

Example:

```json
{
  "period_adjustment": {
    "requested_period": "1y",
    "actual_period": "inception",
    "adjustment_reason": "Portfolio age (3 months) is less than requested period (1 year)"
  }
}
```

## Rate Limiting

- **Rate Limit**: 100 requests per minute per user
- **Headers**:
  - `X-RateLimit-Limit`: Request limit
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

## Example Usage

### Calculate 1-Year Portfolio Performance

```bash
curl -X GET "https://api.portfolia.com/api/v1/calculations/portfolio/123/performance?period=1y" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

### Compare Portfolio to S&P 500

```bash
curl -X GET "https://api.portfolia.com/api/v1/calculations/portfolio/123/compare/SPY?period=1y" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

### Multi-Period Analysis

```bash
curl -X GET "https://api.portfolia.com/api/v1/calculations/portfolio/123/multi-period?periods=3m&periods=1y&periods=inception" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

## UI Integration Notes

### Key Metrics to Display

1. **Primary Metrics**: CAGR, XIRR, TWR (highlight TWR as the new feature)
2. **Risk Metrics**: Volatility, Max Drawdown
3. **Comparison**: Portfolio vs Benchmark differences

### Recommended UI Components

1. **Performance Cards**: Show metrics for different periods
2. **Comparison Charts**: Visual comparison with benchmarks
3. **Period Selector**: Dropdown for different time periods
4. **Error Handling**: Display calculation errors gracefully
5. **Loading States**: Show calculation progress

### TWR Highlighting

Since TWR is newly implemented, consider:

- Adding a "NEW" badge next to TWR metrics
- Tooltip explaining TWR vs other metrics
- Highlighting TWR in benchmark comparisons

## Production Readiness

✅ **Ready for Production**:

- All endpoints fully implemented
- Comprehensive error handling
- Schema validation
- Authentication integration
- Rate limiting support

✅ **TWR Implementation Status**:

- Core TWR calculation: **Fully implemented**
- Multi-period TWR: **Fully implemented**
- Benchmark TWR: **Fully implemented**
- Comparison metrics: **Fully implemented**
- API integration: **Complete**

The TWR implementation is production-ready and provides accurate time-weighted returns for portfolio performance evaluation.
