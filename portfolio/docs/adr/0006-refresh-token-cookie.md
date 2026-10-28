# 0006 Refresh token in an httpOnly cookie

**Context.** Access and refresh tokens were in `localStorage`, readable by any script that ran in the page.

**Decision.** Login and refresh return only the access token in the body and set the refresh token as cookie `portfolia_refresh`: `HttpOnly`, `Secure`, `SameSite=Strict`, path `/api/v1/auth`. The browser keeps the access token in memory (`shared/auth/tokenStore.ts`) and calls `/auth/refresh` once on load. Refresh tokens stay single-use and hashed at rest; reuse revokes the session. Logout expires the cookie.

**Consequences.** A script in the page can still use the in-memory access token while the page is open, but cannot steal a long-lived credential. `SameSite=Strict` and the narrow path keep the cookie off every other request. Over plain http on a non-localhost origin the browser drops a `Secure` cookie, so the HTTPS tailnet URL is the supported way in; `REFRESH_COOKIE_SECURE=false` exists for that case. Non-browser clients (the demo seed) send the cookie header themselves.
