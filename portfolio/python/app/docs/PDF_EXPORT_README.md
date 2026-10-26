# Transaction PDF export

ReportLab export of the signed-in user's transactions. The UI path is Transactions → Export, which previews and then downloads.

| Method and path | Returns |
|---|---|
| `POST /api/v1/transactions/pdf/export` | JSON metadata (`PDFExportResponse`). The bytes are not in this body |
| `POST /api/v1/transactions/pdf/export/download` | The PDF file |
| `POST /api/v1/transactions/pdf/export/preview` | A JSON preview the dialog renders |

All three take `TransactionExportRequest` (filters, options, optional filename) and require a bearer token. A `ValueError` from the service becomes 400 with a fixed sentence. Anything else is 500 `Failed to generate PDF export`.

The PDF still prints `$` and does not convert currency. That is open work (plan items 2.3 and 3.5), not a setting.

This service does not parse PDFs. Parsing a broker file is [ACCOUNT_STATEMENTS_README.md](ACCOUNT_STATEMENTS_README.md).
