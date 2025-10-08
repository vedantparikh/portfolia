# PDF Account Statement Upload Implementation

## Overview

This implementation adds the ability to upload PDF account statements from various brokers and automatically parse transaction data. Users can then review, edit, and bulk import the parsed transactions into their portfolio.

## Features Implemented

### 1. PDF Upload Modal (`PDFUploadModal.jsx`)

- **Provider Selection**: Choose from supported brokers (Trade Republic, Trading212, eToro, Interactive Brokers, DEGIRO)
- **Drag & Drop Upload**: Intuitive file upload with drag-and-drop support
- **File Validation**: Ensures only PDF files are accepted
- **Loading States**: Visual feedback during parsing process

### 2. Parsed Data Table (`ParsedDataTable.jsx`)

- **Editable Table**: Review and modify parsed transaction data
- **Symbol Search**: Auto-complete symbol search with real-time suggestions
- **Confidence Indicators**: Visual indicators for parsing confidence levels
- **Bulk Operations**: Add, edit, delete, and bulk import transactions
- **Portfolio Selection**: Choose target portfolio for import

### 3. API Integration (`api.js`)

- **Real API Endpoints**: Integration with actual backend endpoints
- **Provider Management**: Get list of supported statement providers
- **PDF Parsing**: Upload and parse PDF statements via multipart form data
- **Bulk Transaction Creation**: Import multiple transactions at once

## API Structure

### Endpoints

#### 1. GET `/api/v1/account-statements/providers`

Returns list of supported account statement providers.

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

#### 2. POST `/api/v1/account-statements/parse`

Upload and parse PDF statement.

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

#### 3. POST `/api/v1/transactions/bulk-create`

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

## Component Architecture

### PDFUploadModal

- **Props:**

  - `isOpen`: Boolean to control modal visibility
  - `onClose`: Callback when modal is closed
  - `onParsedData`: Callback with parsed data when parsing is complete

- **State:**
  - `providers`: List of supported providers
  - `selectedProvider`: Currently selected provider
  - `selectedFile`: Selected PDF file
  - `isLoading`: Loading state for providers
  - `isParsing`: Loading state for PDF parsing

### ParsedDataTable

- **Props:**

  - `parsedData`: Parsed transaction data from PDF
  - `onSave`: Callback when transactions are saved
  - `onCancel`: Callback when user cancels
  - `portfolios`: List of available portfolios

- **State:**
  - `transactions`: Array of parsed transactions
  - `editingRow`: Index of currently editing row
  - `searchQuery`: Search filter for transactions
  - `filterType`: Type filter (buy/sell/all)
  - `selectedPortfolio`: Target portfolio for import

## Usage Flow

1. **Upload PDF**: User clicks "Upload PDF" button in transactions view
2. **Select Provider**: Choose the broker that generated the statement
3. **Upload File**: Drag & drop or select PDF file
4. **Parse Statement**: System extracts transaction data (mock implementation)
5. **Review Data**: User reviews parsed transactions in editable table
6. **Edit Transactions**: Modify any fields, add symbols, remove transactions
7. **Select Portfolio**: Choose target portfolio for import
8. **Import**: Bulk create transactions in the selected portfolio

## Transaction Types

The implementation supports all transaction types from the CreateTransactionModal:

- **Trading**: Buy, Sell
- **Income**: Dividend
- **Corporate Actions**: Stock Split, Merger, Spin-off, Rights Issue
- **Options**: Stock Option Exercise
- **Transfers**: Transfer In, Transfer Out
- **Fees**: Management fees and other charges
- **Other**: Miscellaneous transactions

## Error Handling

- File validation (PDF only)
- Provider selection validation
- Portfolio selection validation
- Network error handling
- User-friendly error messages with toast notifications

## Future Enhancements

1. **Real PDF Parsing**: Integrate with actual PDF parsing service
2. **More Providers**: Add support for additional brokers
3. **OCR Integration**: Handle scanned PDFs with OCR
4. **Template Matching**: Custom parsing templates per provider
5. **Batch Processing**: Process multiple statements at once
6. **Data Validation**: Enhanced validation rules for parsed data
7. **Duplicate Detection**: Check for existing transactions before import

## Symbol Search Integration

The implementation uses the same symbol search component as CreateTransactionModal:

- **ClientSideAssetSearch**: Real-time symbol search with suggestions
- **Asset Caching**: Preloaded assets for faster search
- **Auto-complete**: Dropdown suggestions as user types
- **Asset Selection**: Click to select from search results
- **Manual Entry**: Support for manually typing symbols

## Dependencies

- React hooks (useState, useEffect)
- Lucide React icons
- React Hot Toast for notifications
- Existing API service structure
- Market API for symbol search

## File Structure

```
src/components/transactions/
├── PDFUploadModal.jsx      # PDF upload interface
├── ParsedDataTable.jsx     # Transaction review/edit table
├── Transactions.jsx        # Main transactions view (updated)
└── index.js               # Component exports (updated)

src/services/
└── api.js                 # API service with new endpoints (updated)
```

## Integration Points

- **Transactions View**: Added "Upload PDF" button and modal integration
- **API Service**: New `accountStatementsAPI` with mock implementations
- **Portfolio Management**: Integration with existing portfolio selection
- **Transaction Management**: Bulk creation using existing transaction API
- **Symbol Search**: Integration with existing market API for symbol lookup
