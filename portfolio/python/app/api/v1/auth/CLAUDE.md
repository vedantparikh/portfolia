# Auth & user profile

**Purpose:** accounts with JWT access/refresh tokens, email verification and password reset.

**State (2026-10-28):** ✅ register/login/refresh/logout/verify/reset work. Access tokens are PyJWT and live only in the browser's memory. The refresh token is an httpOnly cookie (`portfolia_refresh`, `Secure`, `SameSite=Strict`, path `/api/v1/auth`); JavaScript never sees it. The database stores its SHA-256. An unknown username still runs one bcrypt check. ⚠️ no profile/settings UI.

## Backend — `router.py` (prefix `/api/v1/auth`), `modules/auth/repository.py`, `core/auth/utils.py`, `core/auth/dependencies.py`
| Endpoint | Behaviour |
|---|---|
| `POST /register` | Creates user + profile, sends verification email (Brevo SMTP). Rate limited |
| `POST /login` | Username/email + password (bcrypt, 72-byte truncation) → access token in the body, refresh token as the cookie. Unknown usernames check a dummy hash. Rate limited |
| `POST /refresh` | Reads the cookie only (no body). Single-use rotation: a new access token and a new cookie; the session stores the token's SHA-256. Reuse revokes the session |
| `POST /logout` | Revokes the session and expires the cookie |
| `GET /me`, `GET /me/profile`, `PUT /me`, `DELETE /me` | Current user / profile |
| `POST /change-password`, `POST /forgot-password`, `GET /validate-reset-token/`, `POST /reset-password` | Reset tokens kept in Redis |
| `POST /verify-email`, `POST /resend-verification` | Many endpoints need `is_verified` (`get_current_verified_user`) |

Tables `users`, `user_profiles`, `user_sessions` (`core/database/models/user.py`). Access token `ACCESS_TOKEN_EXPIRE_MINUTES` (15), refresh `REFRESH_TOKEN_EXPIRE_DAYS` (7) unless `REFRESH_TOKEN_EXPIRE_MINUTES` is set. `REFRESH_COOKIE_SECURE=false` only for a plain-http origin other than localhost (browsers drop a `Secure` cookie there, so a reload signs the user out). Every other router uses `get_current_active_user` / `get_current_user`; every resource is scoped by `user_id`.

## Frontend
Routes `/login`, `/register`, `/forgot-password`, `/reset-password`, `/validate-reset-token`, `/verify-email` live in `js/src/app/router.jsx`. Pages are `js/src/features/auth/`. `ProtectedLayout` gates the signed-in routes. `EmailVerificationPrompt` is used by the dashboard and the watchlist. `contexts/AuthContext.jsx`. `authAPI` is in `js/src/features/auth/api.ts`; the 401 interceptor and the single-flight `refreshAccessToken` are in `js/src/shared/api/client.ts`. The access token goes through `shared/auth/tokenStore.ts` (memory only; it also deletes tokens and `user`/`profile` left in localStorage by older builds). `user` and `profile` live in `AuthContext` state only. On start `AuthContext` calls `refreshAccessToken()`; no cookie means signed out.

## Workflow
Register → email link → `/verify-email` → login (cookie set) → protected pages; the axios interceptor refreshes on 401, and a reload refreshes once on start. Forgot password → email link → validate → reset. Dev/demo: verification can be set in the DB (`seed_demo_application.py` does this for demouser).

## Known gaps
- No profile/settings page: `changePassword`, `PUT /me`, `DELETE /me` unused by the UI.

## Planned
A settings page (profile, password, delete account).
