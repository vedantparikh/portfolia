"""
Authentication schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("username")
    def username_valid(cls, v):
        if not v.isalnum():
            raise ValueError("Username must contain only alphanumeric characters")
        return v.lower()


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str


class UserUpdate(BaseModel):
    """Schema for user profile updates."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    currency_preference: Optional[str] = Field(None, min_length=3, max_length=3)
    language_preference: Optional[str] = Field(None, min_length=2, max_length=10)


class AccountDeletion(BaseModel):
    """The current password, to confirm closing the account."""

    password: str


class PasswordChange(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_new_password: str = Field(..., min_length=8, max_length=128)

    @validator("confirm_new_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_new_password: str = Field(..., min_length=8, max_length=128)

    @validator("confirm_new_password")
    def passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class Token(BaseModel):
    """Access token. The refresh token is only sent as an httpOnly cookie."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Schema for token payload data."""

    user_id: Optional[int] = None
    email: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    exp: Optional[datetime] = None


class UserResponse(BaseModel):
    """Schema for user response data."""

    id: int
    email: str
    username: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    """Schema for user profile response data."""

    id: int
    user_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    date_of_birth: Optional[datetime]
    address: Optional[str]
    country: Optional[str]
    timezone: str
    currency_preference: str
    language_preference: str
    notification_preferences: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailVerification(BaseModel):
    """Schema for email verification."""

    token: str


class TokenValidationResponse(BaseModel):
    """Schema for token validation response."""

    is_valid: bool
    message: str
    redirect_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    user_email: Optional[str] = None


class PasswordResetTokenInfo(BaseModel):
    """Schema for password reset token information."""

    token: str
    user_id: int
    user_email: str
    expires_at: datetime
    is_used: bool = False
