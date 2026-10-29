"""
Authentication router with user registration, login, and management endpoints.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from core.auth.dependencies import (
    get_client_ip,
    get_current_active_user,
    get_current_user,
    get_current_user_profile,
    get_token_data,
    get_user_agent,
    validate_refresh_token,
)
from core.auth.utils import (
    DUMMY_PASSWORD_HASH,
    REFRESH_TOKEN_EXPIRE_MINUTES,
    consume_reset_token,
    create_tokens,
    enforce_rate_limit,
    generate_reset_token,
    generate_session_id,
    generate_verification_token,
    get_password_hash,
    hash_refresh_token,
    is_password_strong,
    mark_verification_token_used,
    refresh_token_matches,
    sanitize_username,
    store_reset_token,
    store_verification_token,
    validate_reset_token,
    validate_verification_token,
    verify_password,
)
from core.database.connection import get_db
from core.database.models import User, UserProfile, UserSession
from core.email_client import send_forgot_password_email, send_verification_email
from core.logging_config import get_logger, log_api_request, log_security_event
from core.schemas.auth import (
    AccountDeletion,
    EmailVerification,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    Token,
    TokenValidationResponse,
    UserCreate,
    UserLogin,
    UserProfileResponse,
    UserResponse,
    UserUpdate,
)
from modules.auth.repository import AuthRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Brute-force protection windows (attempts per window)
LOGIN_MAX_ATTEMPTS = 10
REGISTER_MAX_ATTEMPTS = 5
PASSWORD_RESET_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 15 * 60


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        path=settings.REFRESH_COOKIE_PATH,
        secure=settings.REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        secure=settings.REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )


def _access_token(tokens: dict) -> dict:
    return {key: value for key, value in tokens.items() if key != "refresh_token"}


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user(
    user_data: UserCreate, request: Request, db: Session = Depends(get_db)
):
    """Register a new user."""
    client_ip = get_client_ip(request) if request else "unknown"
    user_agent = get_user_agent(request) if request else "unknown"

    # Log API request
    log_api_request(
        logger,
        "POST",
        "/register",
        None,
        client_ip,
        email=user_data.email,
        username=user_data.username,
        user_agent=user_agent,
    )

    enforce_rate_limit(
        client_ip, "register", REGISTER_MAX_ATTEMPTS, RATE_LIMIT_WINDOW_SECONDS
    )

    logger.info(
        f"👤 User registration initiated | Email: {user_data.email} | Username: {user_data.username} | IP: {client_ip}"
    )

    try:
        # Check if user already exists
        logger.debug(
            f"Checking for existing user | Email: {user_data.email} | Username: {user_data.username}"
        )
        accounts = AuthRepository(db)
        existing_user = accounts.find_by_email_or_username(
            user_data.email.lower(), sanitize_username(user_data.username)
        )

        if existing_user:
            if existing_user.email == user_data.email.lower():
                logger.warning(
                    f"🚫 Registration failed - Email already registered | Email: {user_data.email} | IP: {client_ip}"
                )
                log_security_event(
                    logger,
                    "REGISTRATION_ATTEMPT_DUPLICATE_EMAIL",
                    None,
                    client_ip,
                    f"Email: {user_data.email}",
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            else:
                logger.warning(
                    f"🚫 Registration failed - Username already taken | Username: {user_data.username} | IP: "
                    f"{client_ip}"
                )
                log_security_event(
                    logger,
                    "REGISTRATION_ATTEMPT_DUPLICATE_USERNAME",
                    None,
                    client_ip,
                    f"Username: {user_data.username}",
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        # Validate password strength
        logger.debug(
            f"Validating password strength for user | Username: {user_data.username}"
        )
        if not is_password_strong(user_data.password):
            logger.warning(
                f"🚫 Registration failed - Weak password | Username: {user_data.username} | IP: {client_ip}"
            )
            log_security_event(
                logger,
                "REGISTRATION_ATTEMPT_WEAK_PASSWORD",
                None,
                client_ip,
                f"Username: {user_data.username}",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements",
            )

        # Create user
        logger.debug(
            f"Creating new user | Username: {user_data.username} | Email: {user_data.email}"
        )
        hashed_password = get_password_hash(user_data.password)
        sanitized_username = sanitize_username(user_data.username)

        new_user = User(
            email=user_data.email.lower(),
            username=sanitized_username,
            password_hash=hashed_password,
            is_active=True,
            is_verified=False,  # Email verification required
        )

        accounts.add(new_user)

        user_profile = UserProfile(
            user_id=new_user.id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            timezone="UTC",
            currency_preference="USD",
            language_preference="en",
        )

        accounts.add(user_profile)
        accounts.refresh(new_user)

        # Generate and send verification email
        try:
            verification_token = generate_verification_token()
            store_verification_token(
                token=verification_token,
                user_id=new_user.id,
                user_email=new_user.email,
                expires_in_hours=24,
            )

            # Create verification URL
            verification_url = (
                f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
            )
            send_verification_email(new_user.email, verification_url)

            logger.info(
                f"✅ Verification email sent | User ID: {new_user.id} | Email: {new_user.email}"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to send verification email | User ID: {new_user.id} | Error: {e}"
            )
            # Don't fail registration if email sending fails

        # Log security event
        client_ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        log_security_event(
            logger,
            "user_registration",
            str(new_user.id),
            client_ip,
            f"New user registered from IP: {client_ip}, UA: {user_agent}",
        )

        return new_user

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User registration failed"
        ) from exc


@router.post("/login", response_model=Token)
def login_user(
    user_credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Authenticate the user: access token in the body, refresh token as a cookie."""
    client_ip = get_client_ip(request)
    username = user_credentials.username.lower()

    enforce_rate_limit(
        client_ip, "login_ip", LOGIN_MAX_ATTEMPTS * 3, RATE_LIMIT_WINDOW_SECONDS
    )
    enforce_rate_limit(
        username, "login_user", LOGIN_MAX_ATTEMPTS, RATE_LIMIT_WINDOW_SECONDS
    )

    # Find user by username. An unknown name still runs bcrypt against a fixed hash.
    accounts = AuthRepository(db)
    user = accounts.find_by_username(username)
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    password_ok = verify_password(user_credentials.password, password_hash)

    if user is None or not password_ok:
        # Log failed login attempt
        log_security_event(
            logger,
            "failed_login",
            None,  # No user ID for failed login
            client_ip,
            f"Failed login attempt for username: {user_credentials.username} from IP: {client_ip}",
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated"
        )

    # Create a server-side session; tokens carry its id so they can be revoked
    session_id = generate_session_id()
    tokens = create_tokens(user.id, user.email, user.username, session_id)
    user_session = UserSession(
        user_id=user.id,
        session_id=session_id,
        refresh_token=hash_refresh_token(tokens["refresh_token"]),
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES),
        ip_address=client_ip,
        user_agent=get_user_agent(request),
    )
    user.last_login = datetime.now(timezone.utc)

    accounts.add(user_session)

    # Log successful login
    log_security_event(
        logger,
        "successful_login",
        str(user.id),
        client_ip,
        f"User logged in from IP: {client_ip}",
    )
    _set_refresh_cookie(response, tokens["refresh_token"])
    return _access_token(tokens)


@router.post("/refresh", response_model=Token)
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Exchange the refresh cookie for a new access token and a rotated cookie.

    Refresh tokens are single-use: each refresh rotates the token stored on the
    session, so a replayed (stolen) token is rejected and revokes the session.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    presented = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not presented:
        raise invalid
    payload = validate_refresh_token(presented)
    session_id = payload.get("sid")
    if not session_id:
        raise invalid

    now = datetime.now(timezone.utc)
    accounts = AuthRepository(db)
    user_session = accounts.active_session(session_id, int(payload.get("sub")), now)
    if not user_session:
        raise invalid

    if not refresh_token_matches(user_session.refresh_token, presented):
        # Token reuse: an old refresh token was presented. Assume theft and revoke.
        accounts.revoke_stolen_session(user_session)
        log_security_event(
            logger,
            "refresh_token_reuse",
            str(user_session.user_id),
            user_session.ip_address,
            f"Refresh token reuse detected for session {session_id}; session revoked",
        )
        raise invalid

    user = user_session.user
    if not user or not user.is_active:
        raise invalid

    tokens = create_tokens(user.id, user.email, user.username, session_id)
    user_session.refresh_token = hash_refresh_token(tokens["refresh_token"])
    user_session.expires_at = now + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)

    _set_refresh_cookie(response, tokens["refresh_token"])
    return _access_token(tokens)


@router.post("/logout")
def logout_user(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout user and invalidate the current session."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        session_id = get_token_data(auth_header.split(" ", 1)[1]).session_id
        if session_id:
            AuthRepository(db).deactivate_session(current_user.id, session_id)

    # Log logout event
    client_ip = get_client_ip(request)
    log_security_event(
        logger,
        "user_logout",
        str(current_user.id),
        client_ip,
        f"User logged out from IP: {client_ip}",
    )
    _clear_refresh_cookie(response)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.get("/me/profile", response_model=UserProfileResponse)
def get_current_user_profile_info(
    current_user_profile: UserProfile = Depends(get_current_user_profile),
):
    """Get current user's profile information."""
    return current_user_profile


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    # Update user profile
    accounts = AuthRepository(db)
    profile = accounts.profile(current_user.id)
    if profile:
        for field, value in user_update.dict(exclude_unset=True).items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)

    accounts.refresh(current_user)

    return current_user


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change user password."""
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    if not is_password_strong(password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password does not meet security requirements",
        )

    # Update password and sign out every other session
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    current_session_id = get_token_data(
        request.headers.get("Authorization", "").split(" ", 1)[-1]
    ).session_id
    AuthRepository(db).revoke_sessions(
        current_user.id, keep_session_id=current_session_id
    )

    # Log password change
    log_security_event(
        logger, "password_changed", str(current_user.id), None, "User changed password"
    )

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(
    password_reset: PasswordReset, request: Request, db: Session = Depends(get_db)
):
    """Request password reset."""
    client_ip = get_client_ip(request) if request else "unknown"

    # Log API request
    log_api_request(
        logger, "POST", "/forgot-password", None, client_ip, email=password_reset.email
    )

    enforce_rate_limit(
        client_ip,
        "forgot_password_ip",
        PASSWORD_RESET_MAX_ATTEMPTS * 3,
        RATE_LIMIT_WINDOW_SECONDS,
    )
    enforce_rate_limit(
        password_reset.email.lower(),
        "forgot_password_email",
        PASSWORD_RESET_MAX_ATTEMPTS,
        RATE_LIMIT_WINDOW_SECONDS,
    )

    user = AuthRepository(db).find_by_email(password_reset.email.lower())

    if user and user.is_active:
        # Generate reset token
        reset_token = generate_reset_token()

        # Store token in Redis with expiration
        if store_reset_token(reset_token, user.id, user.email, expires_in_minutes=60):
            # Send email with reset link
            # In production, this would construct the frontend URL
            reset_url = (
                f"{settings.FRONTEND_URL}/validate-reset-token?token={reset_token}"
            )

            # Log password reset request
            log_security_event(
                logger,
                "password_reset_requested",
                str(user.id),
                client_ip,
                f"Password reset requested from IP: {client_ip}",
            )

            send_forgot_password_email(recipient_email=user.email, reset_url=reset_url)

            log_security_event(
                logger,
                "password_reset_sent",
                str(user.id),
                client_ip,
                f"Password reset email sent to {user.email}",
            )

            return {
                "message": "If the email exists, a password reset link has been sent"
            }
        else:
            logger.error(f"Failed to store reset token for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process password reset request",
            )
    else:
        # Log failed password reset request
        log_security_event(
            logger,
            "password_reset_requested",
            None,
            client_ip,
            f"Password reset requested for non-existent email: {password_reset.email}",
        )

        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}


@router.get("/validate-reset-token/")
def validate_reset_token_endpoint(
    token: str, request: Request, db: Session = Depends(get_db)
):
    """Validate password reset token and return information for frontend redirection."""
    client_ip = get_client_ip(request) if request else "unknown"

    # Log API request
    log_api_request(logger, "GET", "/validate-reset-token", None, client_ip)

    enforce_rate_limit(
        client_ip,
        "validate_reset_token",
        PASSWORD_RESET_MAX_ATTEMPTS * 6,
        RATE_LIMIT_WINDOW_SECONDS,
    )

    # Validate the token
    is_valid, token_data, error_message = validate_reset_token(token)

    if is_valid:
        # Log successful token validation
        log_security_event(
            logger,
            "reset_token_validated",
            str(token_data["user_id"]),
            client_ip,
            f"Reset token validated successfully for user {token_data['user_email']}",
        )

        # Return success response with redirect information
        return TokenValidationResponse(
            is_valid=True,
            message="Token is valid. You can now reset your password.",
            redirect_url=f"{settings.API_URL}{settings.API_V1_STR}/reset-password?token={token}",
            expires_at=datetime.fromisoformat(token_data["created_at"])
            + timedelta(minutes=60),
            user_email=token_data["user_email"],
        )
    else:
        # Log failed token validation
        log_security_event(
            logger,
            "reset_token_validation_failed",
            None,
            client_ip,
            f"Reset token validation failed: {error_message}",
        )

        # Return error response
        return TokenValidationResponse(
            is_valid=False,
            message=error_message,
            redirect_url=f"{settings.API_URL}{settings.API_V1_STR}/auth/forgot-password?error=invalid_token",
        )


@router.post("/reset-password")
def reset_password(
    password_reset: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
):
    """Reset password using reset token."""
    client_ip = get_client_ip(request) if request else "unknown"

    # Log API request
    log_api_request(logger, "POST", "/reset-password", None, client_ip)

    enforce_rate_limit(
        client_ip,
        "reset_password",
        PASSWORD_RESET_MAX_ATTEMPTS * 3,
        RATE_LIMIT_WINDOW_SECONDS,
    )

    # Check strength before consuming the token so a weak password doesn't burn it
    if not is_password_strong(password_reset.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password does not meet security requirements",
        )

    # Validate and invalidate the token in one atomic step (prevents reuse races)
    is_valid, token_data, error_message = consume_reset_token(password_reset.token)

    if not is_valid:
        log_security_event(
            logger,
            "password_reset_failed",
            None,
            client_ip,
            f"Password reset failed due to invalid token: {error_message}",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    try:
        # Find user
        accounts = AuthRepository(db)
        user = accounts.find_by_id(token_data["user_id"])

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found or account is deactivated",
            )

        # Update password and sign out every existing session
        user.password_hash = get_password_hash(password_reset.new_password)
        user.updated_at = datetime.now(timezone.utc)
        accounts.revoke_sessions(user.id)

        # Log successful password reset
        log_security_event(
            logger,
            "password_reset_successful",
            str(user.id),
            client_ip,
            f"Password reset successful for user {user.email}",
        )

        return {
            "message": "Password reset successful",
            "redirect_url": f"{settings.API_URL}{settings.API_V1_STR}/auth/login?message=password_reset_successful",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")

        log_security_event(
            logger,
            "password_reset_failed",
            str(token_data["user_id"]) if token_data else None,
            client_ip,
            f"Password reset failed due to system error: {str(e)}",
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password",
        ) from e


@router.post("/verify-email")
def verify_email(verification: EmailVerification, db: Session = Depends(get_db)):
    """Verify user email address."""
    logger.info(f"Email verification attempt | Token: {verification.token[:10]}...")

    is_valid, token_data, error_message = validate_verification_token(
        verification.token
    )

    if not is_valid:
        logger.warning(f"❌ Invalid verification token | Error: {error_message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Invalid or expired verification token",
        )

    # Get user from token data
    user_id = token_data.get("user_id")
    user_email = token_data.get("user_email")

    if not user_id or not user_email:
        logger.error("❌ Invalid token data - missing user information")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Find user in database
    accounts = AuthRepository(db)
    user = accounts.find_by_id(user_id)
    if not user:
        logger.error(f"❌ User not found | User ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check if user is already verified
    if user.is_verified:
        logger.info(f"✅ User already verified | User ID: {user_id}")
        return {"message": "Email already verified"}

    # Verify the email matches
    if user.email != user_email:
        logger.error(
            f"❌ Email mismatch | User ID: {user_id} | Token email: {user_email} | User email: {user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification failed",
        )

    # Mark user as verified
    user.is_verified = True

    # Mark token as used
    mark_verification_token_used(verification.token)

    # Log security event
    log_security_event(
        logger,
        "email_verification_success",
        str(user_id),
        None,
        f"Email verified for user: {user.email}",
    )

    logger.info(
        f"✅ Email verification successful | User ID: {user_id} | Email: {user.email}"
    )
    return {"message": "Email verification successful"}


@router.post("/resend-verification")
def resend_verification(current_user: User = Depends(get_current_user)):
    """Resend email verification."""
    logger.info(
        f"Resend verification request | User ID: {current_user.id} | Email: {current_user.email}"
    )

    if current_user.is_verified:
        logger.info(f"✅ User already verified | User ID: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified"
        )

    verification_token = generate_verification_token()
    store_verification_token(
        token=verification_token,
        user_id=current_user.id,
        user_email=current_user.email,
        expires_in_hours=24,
    )

    # Create verification URL
    verification_url = (
        f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    )
    send_verification_email(current_user.email, verification_url)

    # Log security event
    log_security_event(
        logger,
        "verification_email_resent",
        str(current_user.id),
        None,
        f"Verification email resent for user: {current_user.email}",
    )

    logger.info(
        f"✅ Verification email resent | User ID: {current_user.id} | Email: {current_user.email}"
    )
    return {"message": "Verification email sent"}


@router.delete("/me")
def delete_account(
    confirmation: AccountDeletion,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Close the account (deactivate it and end every session); needs the password."""
    if not verify_password(confirmation.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect"
        )

    # Mark user as inactive
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)

    # Expire all sessions
    AuthRepository(db).expire_sessions(current_user.id, datetime.now(timezone.utc))

    # Log account deletion
    log_security_event(
        logger, "account_deleted", str(current_user.id), None, "User account deleted"
    )
    _clear_refresh_cookie(response)

    return {"message": "Account deleted successfully"}
