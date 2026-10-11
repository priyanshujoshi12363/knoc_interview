
from pydantic import EmailStr, Field, SecretStr

from models.common import Schema
from models.user import UserProfile


class RegisterRequest(Schema):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: SecretStr = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(Schema):
    email: EmailStr
    password: SecretStr = Field(
        min_length=1,
        max_length=128,
    )


class RefreshRequest(Schema):
    refresh_token: SecretStr = Field(
        min_length=20,
        max_length=200,
    )


class LogoutRequest(Schema):
    refresh_token: SecretStr = Field(
        min_length=20,
        max_length=200,
    )


class AuthResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(gt=0)
    user: UserProfile


class TokenVerificationResponse(Schema):
    valid: bool = True
    user_id: str
    expires_at: int = Field(gt=0)


class MessageResponse(Schema):
    message: str
