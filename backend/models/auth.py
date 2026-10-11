
from pydantic import EmailStr, Field, SecretStr

from models.common import Schema


class RegisterRequest(Schema):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: SecretStr = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(Schema):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class TokenResponse(Schema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(Schema):
    message: str
