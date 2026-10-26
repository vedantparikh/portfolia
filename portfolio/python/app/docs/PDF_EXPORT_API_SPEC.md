# Transaction PDF export — request shape

Behaviour and the three routes: [PDF_EXPORT_README.md](PDF_EXPORT_README.md). Schemas: `core/schemas/pdf_export.py`.

Authenticated `POST` with JSON:

```json
{
  "filters": {},
  "options": {},
  "custom_filename": "transactions.pdf"
}
```

`filters` and `options` are the fields on `TransactionExportRequest`. Read the Pydantic model rather than a second copy of it here; the model is what FastAPI validates, and `/docs` renders it.

Download (`/export/download`) responds with `application/pdf`. Preview (`/export/preview`) responds with JSON. `/export` responds with `PDFExportResponse` and does not include the file bytes.

Errors:

| Status | When |
|---|---|
| 401 | Missing or expired access token |
| 400 | The service raised `ValueError` (bad filter, empty in a way the service rejects) |
| 500 | Any other failure. The body is `Failed to generate PDF export`. The exception is in the API log |

There is no separate rate limit on these routes beyond the auth dependency. The client in `js/src/services/api.js` is `transactionPDFExportAPI`.
