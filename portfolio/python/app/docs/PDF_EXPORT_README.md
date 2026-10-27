# Transaction PDF export

ReportLab export of the signed-in user's transactions. The UI path is Transactions → Export, which previews and then downloads.

| Method and path | Returns |
|---|---|
| `POST /api/v1/transactions/pdf/export` | JSON metadata (`PDFExportResponse`). The bytes are not in this body |
| `POST /api/v1/transactions/pdf/export/download` | The PDF file |
| `POST /api/v1/transactions/pdf/export/preview` | A JSON preview the dialog renders |

All three take `TransactionExportRequest` (filters, options, optional filename) and require a bearer token. A `ValueError` from the service becomes 400 with a fixed sentence. Anything else is 500 `Failed to generate PDF export`.

Each amount is converted into its portfolio currency. Totals are listed per currency and are not added across currencies. The PDF prints the currency code, for example `EUR 10.00`. A missing rate leaves that row in its own currency.

This service does not parse PDFs. Parsing a broker file is [ACCOUNT_STATEMENTS_README.md](ACCOUNT_STATEMENTS_README.md).
