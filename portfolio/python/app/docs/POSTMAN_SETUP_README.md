# Postman

`Portfolia_API.postman_collection.json` in this folder is a leftover. It is not updated when routes change, and it still describes endpoints that have moved or gone.

Use the live schema instead:

1. Start the stack ([../../../STARTUP_GUIDE.md](../../../STARTUP_GUIDE.md)).
2. Open <http://127.0.0.1:8000/docs>.
3. `POST /api/v1/auth/login` with the demo user (`demo` / `DemoApp!234`) or your own.
4. Authorize with the access token. Swagger sends it as a bearer token.

The route map, with a link to each feature's behaviour, is [ENDPOINT_STRUCTURE.md](ENDPOINT_STRUCTURE.md).
