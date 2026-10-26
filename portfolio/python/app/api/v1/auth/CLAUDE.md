# Auth & user profile

**Purpose:** accounts with JWT access/refresh tokens, email verification and password reset.

**State (2026-10-26):** ✅ register/login/refresh/logout/verify/reset work. Access tokens are PyJWT. The database stores the SHA-256 of the refresh token, not the token. An unknown username still runs one bcrypt check. ⚠️ no profile/settings UI; tokens in localStorage.

## Backend — `router.py` (prefix `/api/v1/auth`), `core/auth/utils.py`, `core/auth/dependencies.py`
| Endpoint | Behaviour |
|---|---|
| `POST /register` | Creates user + profile, sends verification email (Brevo SMTP). Rate limited |
| `POST /login` | Username/email + password (bcrypt, 72-byte truncation) → access + refresh token. Unknown usernames check a dummy hash. Rate limited |
| `POST /refresh` | Single-use rotation; the session stores the token's SHA-256. Reuse revokes the session |
| `POST /logout` | Revokes the session |
| `GET /me`, `GET /me/profile`, `PUT /me`, `DELETE /me` | Current user / profile |
| `POST /change-password`, `POST /forgot-password`, `GET /validate-reset-token/`, `POST /reset-password` | Reset tokens kept in Redis |
| `POST /verify-email`, `POST /resend-verification` | Many endpoints need `is_verified` (`get_current_verified_user`) |

Tables `users`, `user_profiles`, `user_sessions` (`core/database/models/user.py`). Access token 15 min, refresh 30 min by default (`config.py`). Every other router uses `get_current_active_user` / `get_current_user`; every resource is scoped by `user_id`.

## Frontend
Routes `/login`, `/register`, `/forgot-password`, `/reset-password`, `/validate-reset-token`, `/verify-email` (`App.jsx`); `ProtectedRoute`; `contexts/AuthContext.jsx`; `components/auth/*` (`EmailVerificationPrompt` on Dashboard/Watchlist). `authAPI` + refresh interceptor in `services/api.js`.

## Workflow
Register → email link → `/verify-email` → login (tokens in localStorage) → protected pages; the axios interceptor refreshes on 401. Forgot password → email link → validate → reset. Dev/demo: verification can be set in the DB (`seed_demo_application.py` does this for demouser).

## Known gaps
- Tokens and user in localStorage (XSS exposure); token-clearing code duplicated in `api.js`.
- No profile/settings page: `changePassword`, `PUT /me`, `DELETE /me` unused by the UI.
- `core/database/models/auth.py` is a dead duplicate of the user tables; `generate_two_factor_code` unused (no 2FA).

## Planned
Plan 4.6 (refresh token in an httpOnly cookie, access token in memory), a settings page (profile, password, delete account).
