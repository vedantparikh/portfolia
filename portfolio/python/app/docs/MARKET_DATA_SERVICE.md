# Market Data Service

## Overview

The Market Data Service is a modern, lightweight system for fetching real-time financial market data using **yfinance** as the primary data source. The service has been completely redesigned to eliminate local data storage and provide direct access to live market data.

## 🚀 Architecture (Updated September 2024)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   yfinance API  │    │   Market Data    │    │   Portfolio     │
│                 │    │   Service        │    │   Services      │
│ • Live prices   │◄──►│                  │◄──►│                 │
│ • Historical    │    │ • Real-time      │    │ • Valuations    │
│ • Company info  │    │ • Caching        │    │ • Analytics     │
│ • Fundamentals  │    │ • Error handling │    │ • Watchlists    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Key Features

### 1. **Real-time Data Fetching**
- **Direct yfinance Integration**: No local storage, always fresh data
- **Retry Logic**: Automatic retry with exponential backoff
- **Error Handling**: Graceful degradation when APIs are unavailable
- **Caching**: Intelligent caching to minimize API calls

### 2. **Comprehensive Data Coverage**
- **Current Prices**: Real-time stock prices and market data
- **Historical Data**: OHLCV data for any time period
- **Company Information**: Fundamentals, sector, industry data
- **Market Status**: Trading hours and market state

### 3. **Performance Optimization**
- **Bulk Operations**: Efficient fetching of multiple symbols
- **Smart Caching**: Configurable TTL for different data types
- **Rate Limiting**: Respects API limits and prevents throttling
- **Async Operations**: Non-blocking data fetching

### 4. **Fallback Mechanisms**
- **Graceful Degradation**: Returns cached data when API fails
- **Default Values**: Sensible defaults when data unavailable
- **Error Logging**: Comprehensive error tracking and monitoring

## API Endpoints

### Market Data Endpoints

#### 1. **Get Ticker Data**
```http
GET /api/v1/market-data/ticker/{symbol}
```
- **Description**: Get historical market data for a symbol
- **Parameters**:
  - `symbol`: Stock symbol (e.g., AAPL)
  - `period`: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
  - `interval`: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

**Response**:
```json
{
  "symbol": "AAPL",
  "period": "1y",
  "interval": "1d",
  "data_points": 252,
  "data": [
    {
      "date": "2024-01-01T00:00:00Z",
      "open": 150.00,
      "high": 155.00,
      "low": 148.00,
      "close": 152.00,
      "volume": 50000000,
      "dividends": 0.0,
      "stock_splits": 0.0
    }
  ]
}
```

#### 2. **Get Current Price**
```http
GET /api/v1/market-data/ticker/{symbol}/price
```
- **Description**: Get current price for a symbol
- **Response**:
```json
{
  "symbol": "AAPL",
  "price": 152.34,
  "currency": "USD",
  "timestamp": "2024-09-11T15:30:00Z"
}
```

#### 3. **Get Bulk Prices**
```http
GET /api/v1/market-data/prices/bulk?symbols=AAPL,GOOGL,MSFT
```
- **Description**: Get current prices for multiple symbols
- **Response**:
```json
{
  "prices": {
    "AAPL": 152.34,
    "GOOGL": 2750.00,
    "MSFT": 310.50
  },
  "timestamp": "2024-09-11T15:30:00Z"
}
```

#### 4. **Get Ticker Information**
```http
GET /api/v1/market-data/ticker/{symbol}/info
```
- **Description**: Get comprehensive company information
- **Response**:
```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "market_cap": 2500000000000,
  "pe_ratio": 25.5,
  "dividend_yield": 0.005,
  "beta": 1.2,
  "currency": "USD",
  "exchange": "NASDAQ"
}
```

#### 5. **Get Market Status**
```http
GET /api/v1/market-data/market-status
```
- **Description**: Get current market status and trading hours

#### 6. **Get Supported Periods/Intervals**
```http
GET /api/v1/market-data/supported-periods
GET /api/v1/market-data/supported-intervals
```
- **Description**: Get list of supported periods and intervals

## Service Implementation

### MarketDataService Class

```python
class MarketDataService:
    """Service for fetching market data using yfinance."""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.cache_ttl = 300  # 5 minutes
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        
    async def get_multiple_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get current prices for multiple symbols."""
        
    async def fetch_ticker_data(
        self,
        symbol: str,
        period: str = "max",
        interval: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Fetch historical data for a symbol."""
        
    async def get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company information for a symbol."""
        
    async def get_stock_data_for_symbols(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """Get stock data for multiple symbols."""
        
    def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for stock symbols."""
        
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status."""
```

## Configuration

### Environment Variables
```bash
# API Settings
API_PORT=8000
DEBUG=True

# Cache Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Market Data Settings
MARKET_DATA_CACHE_TTL=300  # 5 minutes
MARKET_DATA_MAX_RETRIES=3
MARKET_DATA_RETRY_DELAY=5
```

### Default Parameters
```python
# Default period and interval for yfinance calls
DEFAULT_PERIOD = "max"
DEFAULT_INTERVAL = "1d"

# Supported periods
SUPPORTED_PERIODS = [
    "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
]

# Supported intervals
SUPPORTED_INTERVALS = [
    "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"
]
```

## Usage Examples

### 1. **Portfolio Valuation**
```python
from core.services.market_data_service import market_data_service

# Get current prices for portfolio assets
symbols = ["AAPL", "GOOGL", "MSFT"]
prices = await market_data_service.get_multiple_current_prices(symbols)

# Calculate portfolio value
total_value = 0
for symbol, quantity in portfolio_holdings.items():
    current_price = prices.get(symbol, 0)
    total_value += current_price * quantity
```

### 2. **Watchlist Updates**
```python
# Update watchlist with real-time data
watchlist_symbols = ["AAPL", "TSLA", "NVDA"]
stock_data = await market_data_service.get_stock_data_for_symbols(watchlist_symbols)

for data in stock_data:
    # Update watchlist item with current price and info
    update_watchlist_item(data["symbol"], data["latest_price"], data["name"])
```

### 3. **Technical Analysis**
```python
# Get historical data for analysis
data = await market_data_service.fetch_ticker_data(
    symbol="AAPL",
    period="1y",
    interval="1d"
)

# Calculate technical indicators
sma_20 = data["Close"].rolling(20).mean()
rsi = calculate_rsi(data["Close"])
```

## Integration Points

### 1. **Portfolio Service**
- Real-time portfolio valuations
- P&L calculations using current prices
- Performance tracking and analytics

### 2. **Watchlist Service**
- Live price updates for watchlist items
- Price change calculations
- Alert triggering based on price movements

### 3. **Analytics Service**
- Technical indicator calculations
- Risk metric computations
- Performance benchmarking

### 4. **Asset Search Service**
- Symbol lookup and validation
- Company information retrieval
- Market data enrichment

## Error Handling

### 1. **API Failures**
```python
try:
    price = await market_data_service.get_current_price("AAPL")
except Exception as e:
    logger.error(f"Failed to get price for AAPL: {e}")
    # Use cached price or fallback to cost basis
    price = get_cached_price("AAPL") or asset.cost_basis
```

### 2. **Data Validation**
```python
def validate_market_data(data: pd.DataFrame) -> bool:
    """Validate market data quality."""
    if data is None or data.empty:
        return False
    
    # Check for required columns
    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in data.columns for col in required_columns):
        return False
    
    # Check for reasonable price ranges
    if (data["Close"] <= 0).any():
        return False
    
    return True
```

### 3. **Graceful Degradation**
```python
async def get_price_with_fallback(symbol: str) -> float:
    """Get price with fallback to cached data."""
    try:
        # Try to get fresh price
        price = await market_data_service.get_current_price(symbol)
        if price:
            cache_price(symbol, price)
            return price
    except Exception as e:
        logger.warning(f"Failed to get fresh price for {symbol}: {e}")
    
    # Fallback to cached price
    cached_price = get_cached_price(symbol)
    if cached_price:
        return cached_price
    
    # Last resort: return 0 or raise exception
    raise ValueError(f"No price data available for {symbol}")
```

## Performance Considerations

### 1. **Caching Strategy**
- **Price Caching**: 5-minute TTL for current prices
- **Info Caching**: 1-hour TTL for company information
- **Historical Data**: 15-minute TTL for recent data

### 2. **Batch Operations**
- Use `yf.Tickers()` for multiple symbols
- Process symbols in batches of 10-20
- Implement concurrent fetching with proper rate limiting

### 3. **Rate Limiting**
- Respect yfinance API limits
- Implement exponential backoff
- Use connection pooling for efficiency

## Monitoring and Logging

### Key Metrics
- **API Response Times**: Track yfinance API performance
- **Cache Hit Rates**: Monitor caching effectiveness
- **Error Rates**: Track API failures and fallbacks
- **Data Freshness**: Monitor age of cached data

### Log Levels
- **INFO**: Successful data fetches, cache hits
- **WARNING**: API slowness, cache misses, fallbacks
- **ERROR**: API failures, data validation errors

### Health Checks
```python
async def health_check() -> Dict[str, Any]:
    """Check market data service health."""
    try:
        # Test basic functionality
        test_price = await market_data_service.get_current_price("AAPL")
        
        return {
            "status": "healthy",
            "yfinance_accessible": test_price is not None,
            "cache_status": "operational",
            "last_check": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "last_check": datetime.now(timezone.utc).isoformat()
        }
```

## Migration from Local Storage

### What Was Removed
- **Database Tables**: `asset_prices`, `market_data`, `ticker_info`, `data_update_log`
- **Scheduled Updates**: No more daily data synchronization
- **Local Fallback**: No local database backup

### What Was Added
- **Real-time Fetching**: Direct yfinance integration
- **Smart Caching**: Redis-based caching for performance
- **Enhanced Error Handling**: Robust fallback mechanisms

### Migration Benefits
- **Always Fresh Data**: No stale data issues
- **Reduced Complexity**: Simpler architecture
- **Lower Storage Costs**: No database storage for market data
- **Better Performance**: Direct API access with caching

## Conclusion

The updated Market Data Service provides a modern, efficient approach to financial data access. By leveraging yfinance directly with intelligent caching and error handling, it delivers real-time data while maintaining high performance and reliability. The elimination of local storage reduces complexity while ensuring data freshness for all portfolio and analytics operations.