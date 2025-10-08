# Account Statement Parsing API

This document describes the account statement parsing functionality that allows users to upload PDF statements from various brokers and automatically extract transaction data for bulk import into their portfolios.

## Overview

The account statement parsing system provides three main endpoints:

1. **GET `/api/v1/account-statements/providers`** - Get supported statement providers
2. **POST `/api/v1/account-statements/parse`** - Parse PDF statement and extract transactions
3. **POST `/api/v1/account-statements/transactions/bulk-create`** - Create multiple transactions from parsed data

## Architecture

### Components

- **Schemas** (`app/core/schemas/account_statements.py`): Pydantic models for request/response validation
- **Service** (`app/core/services/account_statement_service.py`): Core business logic for parsing and processing
- **Router** (`app/api/v1/account_statements/router.py`): FastAPI endpoints with authentication
- **Parsers**: Provider-specific PDF parsing implementations

### Parser System

The system uses a plugin-based architecture for PDF parsers:

```python
class PDFParser(ABC):
    @abstractmethod
    def parse(self, pdf_content: bytes) -> ParsedData:
        pass
```

Each provider (e.g., Trade Republic) has its own parser implementation that understands the specific format of their statements.

## API Endpoints

### 1. Get Supported Providers

**GET** `/api/v1/account-statements/providers`

Returns a list of supported account statement providers.

**Response:**

```json
{
  "providers": [
    {
      "id": "trade_republic",
      "name": "Trade Republic",
      "description": "German neobroker",
      "supported_formats": ["pdf"],
      "logo_url": "/logos/trade_republic.png"
    }
  ]
}
```

### 2. Parse Statement

**POST** `/api/v1/account-statements/parse`

Upload and parse a PDF statement.

**Request:**

```json
{
  "provider_id": "trade_republic",
  "file": "base64_encoded_pdf_content",
  "filename": "statement_2024_01.pdf"
}
```

**Response:**

```json
{
  "parsed_data": {
    "provider": "trade_republic",
    "statement_period": {
      "start_date": "2024-01-01",
      "end_date": "2024-01-31"
    },
    "transactions": [
      {
        "id": "temp_1",
        "transaction_date": "2024-01-15",
        "transaction_type": "buy",
        "name": "Apple Inc.",
        "symbol": "AAPL",
        "total_amount": 1500.0,
        "quantity": 10,
        "purchase_price": 150.0,
        "fees": 0.0,
        "confidence_score": 0.95,
        "needs_review": false
      }
    ],
    "metadata": {
      "total_transactions": 1,
      "parsing_confidence": 0.92,
      "warnings": ["Symbol for 'Unknown Company' could not be identified"]
    }
  }
}
```

### 3. Bulk Create Transactions

**POST** `/api/v1/account-statements/transactions/bulk-create`

Create multiple transactions from parsed data.

**Request:**

```json
{
  "portfolio_id": 1,
  "transactions": [
    {
      "transaction_date": "2024-01-15",
      "transaction_type": "buy",
      "symbol": "AAPL",
      "quantity": 10,
      "price": 150.0,
      "fees": 0.0,
      "notes": "Imported from Trade Republic statement"
    }
  ]
}
```

**Response:**

```json
{
  "created_transactions": [
    {
      "id": 123,
      "transaction_date": "2024-01-15",
      "transaction_type": "buy",
      "symbol": "AAPL",
      "quantity": 10,
      "price": 150.0,
      "fees": 0.0,
      "total_amount": 1500.0,
      "portfolio_id": 1,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "summary": {
    "total_created": 1,
    "total_failed": 0,
    "errors": []
  }
}
```

## Usage Flow

1. **Get Providers**: Client calls `/providers` to see supported brokers
2. **Upload PDF**: User selects provider and uploads PDF statement
3. **Parse Statement**: System extracts transaction data using provider-specific parser
4. **Review Data**: User reviews parsed transactions in editable table
5. **Edit Transactions**: User can modify fields, add symbols, remove transactions
6. **Select Portfolio**: User chooses target portfolio for import
7. **Import**: System creates transactions and updates portfolio holdings

## Security

- All endpoints require authentication via `get_current_verified_user`
- Users can only create transactions in their own portfolios
- Portfolio ownership is verified before any operations

## Error Handling

The system provides comprehensive error handling:

- **Validation Errors**: Invalid request data returns 400 Bad Request
- **Authentication Errors**: Unauthorized access returns 401 Unauthorized
- **Permission Errors**: Access denied returns 403 Forbidden
- **Not Found Errors**: Missing resources return 404 Not Found
- **Server Errors**: Internal issues return 500 Internal Server Error

## Dependencies

- **PyPDF2**: PDF text extraction
- **FastAPI**: Web framework
- **Pydantic**: Data validation
- **SQLAlchemy**: Database operations

## Adding New Providers

To add support for a new broker:

1. Create a new parser class inheriting from `PDFParser`
2. Implement the `parse()` method with provider-specific logic
3. Add the parser to `AccountStatementService._parsers`
4. Add provider info to `get_supported_providers()`

Example:

```python
class NewBrokerParser(PDFParser):
    def parse(self, pdf_content: bytes) -> ParsedData:
        # Implement parsing logic
        pass
```

## Testing

Run the test script to verify functionality:

```bash
python3 app/test_account_statements.py
```

This will generate sample request data and verify the API structure.

## Future Enhancements

- Support for CSV and XLSX formats
- Machine learning-based parsing for better accuracy
- Automatic symbol resolution using financial APIs
- Batch processing for multiple statements
- Transaction validation and duplicate detection
- Support for more international brokers
