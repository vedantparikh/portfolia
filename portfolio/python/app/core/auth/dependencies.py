"""
Authentication dependencies for FastAPI routes.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.auth.utils import ALGORITHM, SECRET_KEY, verify_token
from core.database.connection import get_db
from core.database.models import Portfolio, User, UserProfile, UserSession
from core.errors import NotFoundError
from core.schemas.auth import TokenData

# Security scheme for Bearer token authentication
security = HTTPBearer()


def is_session_active(db: Session, user_id: int, session_id: Optional[str]) -> bool:
    """Check that the token's server-side session exists and has not been revoked."""
    if not session_id:
        return False
    return (
        db.query(UserSession.id)
        .filter(
            UserSession.session_id == session_id,
            UserSession.user_id == user_id,
            UserSession.is_active.is_(True),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .first()
        is not None
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify the token
        payload = verify_token(credentials.credentials, "access")
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        # Reject tokens whose session was revoked (logout, password change/reset)
        if not is_session_active(db, int(user_id), payload.get("sid")):
            raise credentials_exception

        # Get user from database
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )

        return user

    except JWTError:
        raise credentials_exception


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def get_current_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current verified user."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not verified"
        )
    return current_user


def get_current_user_profile(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserProfile:
    """Get current user's profile."""
    profile = (
        db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
        )
    return profile


def get_optional_current_user(
    request: Request, db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]
        payload = verify_token(token, "access")
        user_id: str = payload.get("sub")

        if user_id is None:
            return None

        if not is_session_active(db, int(user_id), payload.get("sid")):
            return None

        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None or not user.is_active:
            return None

        return user

    except (JWTError, HTTPException):
        return None


def get_owned_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Portfolio:
    """The portfolio `portfolio_id` when it belongs to the current user and is active."""
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id,
            Portfolio.is_active.is_(True),
        )
        .first()
    )
    if portfolio is None:
        raise NotFoundError(f"Portfolio {portfolio_id} not found")
    return portfolio


def require_permission(permission: str):
    """Decorator to require specific permission."""

    def permission_checker(current_user: User = Depends(get_current_user)):
        # For now, we'll implement basic role checking
        # In a full RBAC system, this would check user permissions
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
            )
        return current_user

    return permission_checker


def require_admin():
    """Require admin privileges."""

    def admin_checker(current_user: User = Depends(get_current_user)):
        # For now, we'll implement basic admin checking
        # In a full RBAC system, this would check admin role
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user"
            )
        # Add admin role check here when implemented
        return current_user

    return admin_checker


def get_token_data(token: str) -> TokenData:
    """Extract token data without database dependency."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        username: str = payload.get("username")
        exp: int = payload.get("exp")

        return TokenData(
            user_id=int(user_id) if user_id else None,
            email=email,
            username=username,
            session_id=payload.get("sid"),
            exp=exp,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


def validate_refresh_token(refresh_token: str) -> dict:
    """Decode a refresh token, raising 401 if it is invalid or not a refresh token."""
    try:
        return verify_token(refresh_token, "refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent from request."""
    return request.headers.get("User-Agent", "unknown")
