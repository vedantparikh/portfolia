# Transaction PDF Export API Specification

## Overview

The Transaction PDF Export API provides endpoints for generating professional PDF reports of transaction data with comprehensive filtering and customization options. This API integrates with the existing Portfolia transaction system to create downloadable reports.

## Base URL

```
/api/v1/transactions/pdf
```

## Authentication

All endpoints require Bearer token authentication:

```
Authorization: Bearer <your_jwt_token>
```

## Endpoints

### 1. Export Transaction PDF (Metadata Response)

**Endpoint:** `POST /export`

**Description:** Generate a PDF report and return metadata about the export without the actual PDF file.

**Request Body:**

```json
{
  "filters": {
    "portfolio_ids": [1, 2, 3],
    "start_date": "2023-01-01T00:00:00Z",
    "end_date": "2023-12-31T23:59:59Z",
    "transaction_types": ["buy", "sell", "dividend"],
    "asset_symbols": ["AAPL", "GOOGL", "MSFT"],
    "min_amount": 100.0,
    "max_amount": 50000.0
  },
  "options": {
    "include_summary": true,
    "include_charts": false,
    "include_portfolio_details": true,
    "include_asset_details": true,
    "group_by_portfolio": false,
    "group_by_asset": false,
    "sort_by": "transaction_date",
    "sort_order": "desc"
  },
  "custom_filename": "my_transactions_report"
}
```

**Request Schema:**

| Field                               | Type                       | Required | Description                                      |
| ----------------------------------- | -------------------------- | -------- | ------------------------------------------------ |
| `filters`                           | `TransactionExportFilters` | No       | Filtering criteria for transactions              |
| `filters.portfolio_ids`             | `array[integer]`           | No       | List of portfolio IDs to include                 |
| `filters.start_date`                | `string(datetime)`         | No       | Start date (ISO 8601 format)                     |
| `filters.end_date`                  | `string(datetime)`         | No       | End date (ISO 8601 format)                       |
| `filters.transaction_types`         | `array[string]`            | No       | Transaction types to include                     |
| `filters.asset_symbols`             | `array[string]`            | No       | Asset symbols to include                         |
| `filters.min_amount`                | `number`                   | No       | Minimum transaction amount                       |
| `filters.max_amount`                | `number`                   | No       | Maximum transaction amount                       |
| `options`                           | `PDFExportOptions`         | No       | Export customization options                     |
| `options.include_summary`           | `boolean`                  | No       | Include summary statistics (default: true)       |
| `options.include_charts`            | `boolean`                  | No       | Include charts (future feature, default: false)  |
| `options.include_portfolio_details` | `boolean`                  | No       | Include portfolio information (default: true)    |
| `options.include_asset_details`     | `boolean`                  | No       | Include asset details (default: true)            |
| `options.group_by_portfolio`        | `boolean`                  | No       | Group transactions by portfolio (default: false) |
| `options.group_by_asset`            | `boolean`                  | No       | Group transactions by asset (default: false)     |
| `options.sort_by`                   | `string`                   | No       | Sort field (default: "transaction_date")         |
| `options.sort_order`                | `string`                   | No       | Sort order: "asc" or "desc" (default: "desc")    |
| `custom_filename`                   | `string`                   | No       | Custom filename without extension                |

**Transaction Types:**

- `buy` - Buy transactions
- `sell` - Sell transactions
- `dividend` - Dividend payments
- `split` - Stock splits
- `merger` - Merger transactions
- `spin_off` - Spin-off transactions
- `rights_issue` - Rights issue transactions
- `stock_option_exercise` - Option exercise transactions
- `transfer_in` - Transfer in transactions
- `transfer_out` - Transfer out transactions
- `fee` - Fee transactions
- `other` - Other transaction types

**Response:**

```json
{
  "filename": "transactions_john_doe_my_portfolio_20231208_143022.pdf",
  "file_size": 245760,
  "transaction_count": 156,
  "summary_stats": {
    "total_transactions": 156,
    "total_buy_volume": 45000.0,
    "total_sell_volume": 12000.0,
    "net_flow": -33000.0,
    "total_fees": 234.5,
    "total_taxes": 0.0,
    "unique_assets": 12,
    "date_range": "2023-01-01 to 2023-12-31",
    "portfolios_included": ["My Portfolio", "Growth Portfolio"]
  },
  "generated_at": "2023-12-08T14:30:22Z",
  "export_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response Schema:**

| Field                               | Type                      | Description                     |
| ----------------------------------- | ------------------------- | ------------------------------- |
| `filename`                          | `string`                  | Generated PDF filename          |
| `file_size`                         | `integer`                 | PDF file size in bytes          |
| `transaction_count`                 | `integer`                 | Number of transactions included |
| `summary_stats`                     | `TransactionSummaryStats` | Summary statistics              |
| `summary_stats.total_transactions`  | `integer`                 | Total number of transactions    |
| `summary_stats.total_buy_volume`    | `number`                  | Total buy transaction volume    |
| `summary_stats.total_sell_volume`   | `number`                  | Total sell transaction volume   |
| `summary_stats.net_flow`            | `number`                  | Net cash flow (sell - buy)      |
| `summary_stats.total_fees`          | `number`                  | Total fees paid                 |
| `summary_stats.total_taxes`         | `number`                  | Total taxes paid                |
| `summary_stats.unique_assets`       | `integer`                 | Number of unique assets         |
| `summary_stats.date_range`          | `string`                  | Date range of transactions      |
| `summary_stats.portfolios_included` | `array[string]`           | List of portfolio names         |
| `generated_at`                      | `string(datetime)`        | Generation timestamp            |
| `export_id`                         | `string`                  | Unique export identifier        |

---

### 2. Download Transaction PDF

**Endpoint:** `POST /export/download`

**Description:** Generate and directly download a PDF report.

**Request Body:** Same as the export endpoint above.

**Response:**

- **Content-Type:** `application/pdf`
- **Headers:**
  - `Content-Disposition: attachment; filename=<generated_filename>.pdf`
  - `Content-Length: <file_size_in_bytes>`

**Response Body:** Binary PDF file content

---

### 3. Preview Export

**Endpoint:** `GET /export/preview`

**Description:** Preview what would be included in the PDF export without generating the actual file.

**Request Body:** Same as the export endpoint above.

**Response:**

```json
{
  "filename": "transactions_john_doe_20231208_143022.pdf",
  "transaction_count": 156,
  "summary_stats": {
    "total_transactions": 156,
    "total_buy_volume": 45000.0,
    "total_sell_volume": 12000.0,
    "net_flow": -33000.0,
    "total_fees": 234.5,
    "total_taxes": 0.0,
    "unique_assets": 12,
    "date_range": "2023-01-01 to 2023-12-31",
    "portfolios_included": ["My Portfolio", "Growth Portfolio"]
  },
  "estimated_pages": 7,
  "filters_applied": {
    "portfolio_ids": [1, 2],
    "date_range": {
      "start": "2023-01-01T00:00:00Z",
      "end": "2023-12-31T23:59:59Z"
    },
    "transaction_types": ["buy", "sell"],
    "asset_symbols": null
  },
  "options": {
    "include_summary": true,
    "include_charts": false,
    "include_portfolio_details": true,
    "include_asset_details": true,
    "group_by_portfolio": false,
    "group_by_asset": false,
    "sort_by": "transaction_date",
    "sort_order": "desc"
  }
}
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "No transactions found with the specified filters"
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Failed to generate PDF export"
}
```

## Frontend Integration Examples

### JavaScript/React Example

```javascript
// Export and download PDF
const exportTransactionsPDF = async (filters, options) => {
  try {
    const response = await fetch("/api/v1/transactions/pdf/export/download", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ filters, options }),
    });

    if (!response.ok) {
      throw new Error("Export failed");
    }

    // Create download link
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = response.headers
      .get("Content-Disposition")
      .split("filename=")[1]
      .replace(/"/g, "");
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Export failed:", error);
    throw error;
  }
};

// Preview export
const previewExport = async (filters, options) => {
  const response = await fetch("/api/v1/transactions/pdf/export/preview", {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ filters, options }),
  });

  if (!response.ok) {
    throw new Error("Preview failed");
  }

  return await response.json();
};

// Usage example
const filters = {
  portfolio_ids: [1, 2],
  start_date: "2023-01-01T00:00:00Z",
  end_date: "2023-12-31T23:59:59Z",
  transaction_types: ["buy", "sell"],
};

const options = {
  include_summary: true,
  sort_by: "transaction_date",
  sort_order: "desc",
};

// Export PDF
await exportTransactionsPDF(filters, options);

// Or preview first
const preview = await previewExport(filters, options);
console.log(`Will export ${preview.transaction_count} transactions`);
```

### cURL Example

```bash
# Export PDF with metadata response
curl -X POST "https://api.portfolia.com/api/v1/transactions/pdf/export" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "portfolio_ids": [1, 2],
      "start_date": "2023-01-01T00:00:00Z",
      "end_date": "2023-12-31T23:59:59Z",
      "transaction_types": ["buy", "sell"]
    },
    "options": {
      "include_summary": true,
      "sort_by": "transaction_date",
      "sort_order": "desc"
    }
  }'

# Download PDF directly
curl -X POST "https://api.portfolia.com/api/v1/transactions/pdf/export/download" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "portfolio_ids": [1, 2],
      "start_date": "2023-01-01T00:00:00Z",
      "end_date": "2023-12-31T23:59:59Z"
    },
    "options": {
      "include_summary": true
    }
  }' \
  --output transactions_report.pdf
```

## Rate Limits

- **Rate Limit:** 10 requests per minute per user
- **File Size Limit:** Generated PDFs are limited to 50MB
- **Transaction Limit:** Maximum 10,000 transactions per export

## Notes

- All dates should be in ISO 8601 format with timezone information
- Decimal numbers are returned as strings to preserve precision
- PDF generation is optimized for up to 5,000 transactions
- For larger datasets, consider using date range filters to split exports
- Custom filenames are sanitized to remove invalid characters
- Default filename format: `transactions_{username}_{portfolio}_{timestamp}.pdf`

## PDF Parsing

For parsing Portfolia-generated PDFs, use the existing account statements API with provider `"portfolia"`:

```
POST /api/v1/account-statements/parse
```

This will use the integrated Portfolia parser to extract transaction data from app-generated PDFs.
