"""
Authentication utilities for password hashing, JWT tokens, and security.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union

import bcrypt
import jwt
from fastapi import HTTPException, status
from jwt.exceptions import PyJWTError as JWTError
from pytz import utc

from config import settings
from core.database.redis_client import get_redis
from core.logging_config import get_logger

logger = get_logger(__name__)

# Password hashing context

# JWT token configuration
ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_MINUTES = settings.REFRESH_TOKEN_EXPIRE_MINUTES


def _bcrypt_input(password: str) -> bytes:
    # bcrypt only uses the first 72 bytes; passlib truncated silently, bcrypt>=5 raises
    return password.encode("utf-8")[:72]


# Fixed hash so an unknown username still costs one bcrypt check.
DUMMY_PASSWORD_HASH = "$2b$12$ZLY92caJi5WyyoKcQcyI0uLxvOnZ3ecO/cotYxa/Pb9IEO/9kSyYi"


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex of a refresh token. The database stores this, not the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_matches(stored: str, presented: str) -> bool:
    """True when `stored` is the hash of `presented`."""
    digest = hash_refresh_token(presented)
    if len(stored) != len(digest):
        return False
    return hmac.compare_digest(stored, digest)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(
            _bcrypt_input(plain_password), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return bcrypt.hashpw(_bcrypt_input(password), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # jti makes every token unique, even when issued in the same second
    to_encode.update(
        {"exp": expire, "type": "access", "jti": secrets.token_urlsafe(16)}
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=REFRESH_TOKEN_EXPIRE_MINUTES
        )

    # jti makes every token unique, so refresh-token rotation always changes the token
    to_encode.update(
        {"exp": expire, "type": "refresh", "jti": secrets.token_urlsafe(16)}
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type_from_payload = payload.get("type")

        if token_type_from_payload != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )

        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def create_tokens(user_id: int, email: str, username: str, session_id: str) -> dict:
    """
    Create both access and refresh tokens for a user.

    Both tokens carry the session id (`sid`) so they can be revoked server-side by
    deactivating the corresponding UserSession.
    """
    data = {
        "sub": str(user_id),
        "email": email,
        "username": username,
        "sid": session_id,
    }

    access_token = create_access_token(data=data)
    refresh_token = create_refresh_token(data=data)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
    }


def generate_verification_token() -> str:
    """Generate a random verification token."""
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Generate a random password reset token."""
    return secrets.token_urlsafe(32)


def generate_session_id() -> str:
    """Generate a random session ID."""
    return secrets.token_urlsafe(32)


def is_password_strong(password: str) -> bool:
    """Check if password meets security requirements."""
    if len(password) < 8:
        return False

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    return has_upper and has_lower and has_digit and has_special


def sanitize_username(username: str) -> str:
    """Sanitize username for safe storage."""
    return username.lower().strip()


def validate_email_format(email: str) -> bool:
    """Basic email format validation."""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def rate_limit_key(identifier: str, action: str) -> str:
    """Generate rate limiting key."""
    return f"rate_limit:{action}:{identifier}"


def is_rate_limited(
    identifier: str, action: str, max_attempts: int, window_seconds: int
) -> bool:
    """
    Count an attempt for (action, identifier) and report whether the limit is exceeded.

    Uses a fixed window counter in Redis. Fails open if Redis is unavailable so an
    outage does not lock every user out.
    """
    try:
        count = get_redis().incr_with_ttl(
            rate_limit_key(identifier, action), window_seconds
        )
    except Exception as e:
        logger.error(f"Rate limit check failed for {action}: {e}")
        return False
    return count is not None and count > max_attempts


def enforce_rate_limit(
    identifier: str, action: str, max_attempts: int, window_seconds: int
) -> None:
    """Raise HTTP 429 if the action is rate limited for this identifier."""
    if is_rate_limited(identifier, action, max_attempts, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
            headers={"Retry-After": str(window_seconds)},
        )


def validate_token_expiry(token_exp: Union[int, datetime]) -> bool:
    """Validate if token is expired."""
    if isinstance(token_exp, int):
        exp_datetime = datetime.fromtimestamp(token_exp, tz=timezone.utc)
    else:
        exp_datetime = token_exp

    return datetime.now(timezone.utc) < exp_datetime


def get_token_expiry_time(token_type: str = "access") -> datetime:
    """Get expiry time for a token type."""
    if token_type == "access":
        return datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    elif token_type == "refresh":
        return datetime.now(timezone.utc) + timedelta(
            minutes=REFRESH_TOKEN_EXPIRE_MINUTES
        )
    else:
        raise ValueError(f"Unknown token type: {token_type}")


def store_reset_token(
    token: str, user_id: int, user_email: str, expires_in_minutes: int = 60
) -> bool:
    """
    Store password reset token in Redis with expiration.

    Args:
        token: The reset token
        user_id: User ID
        user_email: User email
        expires_in_hours: Token expiration time in hours

    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        redis_client = get_redis()

        if not redis_client:
            return False

        # Create token data
        token_data = {
            "user_id": user_id,
            "user_email": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_used": False,
        }

        # Store in Redis with expiration
        key = f"reset_token:{token}"
        stored = redis_client.set(
            key=key,
            ex_seconds=expires_in_minutes * 60,  # Convert minutes to seconds
            value=token_data,
        )

        return bool(stored)
    except Exception as e:
        logger.error(f"Failed to store reset token: {e}")
        return False


def validate_reset_token(token: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Validate password reset token.

    Args:
        token: The reset token to validate

    Returns:
        Tuple[bool, Optional[dict], Optional[str]]:
        - is_valid: Whether token is valid
        - token_data: Token data if valid
        - error_message: Error message if invalid
    """
    try:
        redis_client = get_redis()

        if not redis_client:
            return False, None, "Redis connection unavailable"

        # Get token from Redis
        key = f"reset_token:{token}"
        token_json = redis_client.get(key)

        if not token_json:
            return False, None, "Token not found or expired"

        # Parse token data
        token_data = token_json

        # Check if token is already used
        if token_data.get("is_used", False):
            return False, None, "Token has already been used"

        # Check if token is expired (additional safety check)
        created_at = datetime.fromisoformat(token_data["created_at"]).replace(
            tzinfo=utc
        )
        if datetime.now(utc) - created_at > timedelta(minutes=60):
            return False, None, "Token has expired"

        return True, token_data, None

    except Exception as e:
        logger.error(f"Failed to validate reset token: {e}")
        return False, None, "Token validation failed"


def consume_reset_token(token: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Atomically validate and invalidate a password reset token.

    The token is removed with GETDEL, so two concurrent requests cannot both use it.

    Returns:
        Tuple[bool, Optional[dict], Optional[str]]: (is_valid, token_data, error_message)
    """
    try:
        token_data = get_redis().getdel(f"reset_token:{token}")

        if not token_data:
            return False, None, "Token not found or expired"

        if token_data.get("is_used", False):
            return False, None, "Token has already been used"

        created_at = datetime.fromisoformat(token_data["created_at"]).replace(
            tzinfo=utc
        )
        if datetime.now(utc) - created_at > timedelta(minutes=60):
            return False, None, "Token has expired"

        return True, token_data, None

    except Exception as e:
        logger.error(f"Failed to consume reset token: {e}")
        return False, None, "Token validation failed"


def store_verification_token(
    token: str, user_id: int, user_email: str, expires_in_hours: int = 24
) -> bool:
    """
    Store email verification token in Redis with expiration.

    Args:
        token: The verification token
        user_id: User ID
        user_email: User email
        expires_in_hours: Token expiration time in hours

    Returns:
        bool: True if stored successfully, False otherwise
    """
    try:
        redis_client = get_redis()

        if not redis_client:
            return False

        # Create token data
        token_data = {
            "user_id": user_id,
            "user_email": user_email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_used": False,
        }

        # Store in Redis with expiration
        key = f"verification_token:{token}"
        stored = redis_client.set(
            key=key,
            ex_seconds=expires_in_hours * 3600,  # Convert hours to seconds
            value=token_data,
        )

        return bool(stored)
    except Exception as e:
        logger.error(f"Failed to store verification token: {e}")
        return False


def validate_verification_token(
    token: str,
) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Validate email verification token.

    Args:
        token: The verification token to validate

    Returns:
        Tuple[bool, Optional[dict], Optional[str]]:
        - is_valid: Whether token is valid
        - token_data: Token data if valid
        - error_message: Error message if invalid
    """
    try:
        redis_client = get_redis()

        if not redis_client:
            return False, None, "Redis connection unavailable"

        # Get token from Redis
        key = f"verification_token:{token}"
        token_json = redis_client.get(key)

        if not token_json:
            return False, None, "Token not found or expired"

        # Parse token data
        token_data = token_json

        # Check if token is already used
        if token_data.get("is_used", False):
            return False, None, "Token has already been used"

        # Check if token is expired (additional safety check)
        created_at = datetime.fromisoformat(token_data["created_at"]).replace(
            tzinfo=utc
        )
        if datetime.now(utc) - created_at > timedelta(hours=24):
            return False, None, "Token has expired"

        return True, token_data, None

    except Exception as e:
        logger.error(f"Failed to validate verification token: {e}")
        return False, None, "Token validation failed"


def mark_verification_token_used(token: str) -> bool:
    """
    Mark a verification token as used.

    Args:
        token: The verification token to mark as used

    Returns:
        bool: True if marked successfully, False otherwise
    """
    try:
        redis_client = get_redis()

        if not redis_client:
            return False

        key = f"verification_token:{token}"
        token_json = redis_client.get(key)

        if not token_json:
            return False

        # Update token data
        token_data = token_json
        token_data["is_used"] = True

        # Store updated data
        redis_client.set(
            key=key, ex_seconds=86400, value=token_data
        )  # Keep for 24 hours after use

        return True
    except Exception as e:
        logger.error(f"Failed to mark verification token as used: {e}")
        return False
