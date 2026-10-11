
from datetime import timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from pymongo.errors import DuplicateKeyError

from api.deps import bearer_scheme, get_current_user
from api.serializers import serialize_user
from core.config import JWT_REFRESH_EXPIRE_DAYS
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from db.index import users_collection, refresh_sessions_collection
from models.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    AuthResponse,
    TokenVerificationResponse,
    MessageResponse,
)
from models.common import utc_now
from models.user import UserPreferences


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from core.config import (
    JWT_SECRET_KEY,
    JWT_ACCESS_EXPIRE_MINUTES,
    JWT_REFRESH_EXPIRE_DAYS,
)

password_hasher = PasswordHash.recommended()
JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_in = JWT_ACCESS_EXPIRE_MINUTES * 60

    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": secrets.token_urlsafe(16),
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token, expires_in


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp", "type"]},
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")

    return payload


def create_refresh_token() -> tuple[str, str, datetime]:
    # The raw token is returned to the client only once.
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    expires_at = datetime.now(timezone.utc) + timedelta(
        days=JWT_REFRESH_EXPIRE_DAYS
    )

    return raw_token, token_hash, expires_at


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def issue_token_pair(user: dict) -> AuthResponse:
    access_token, expires_in = create_access_token(str(user["_id"]))

    refresh_token, token_hash, refresh_expires_at = (
        create_refresh_token()
    )

    now = utc_now()

    await refresh_sessions_collection.insert_one({
        "token_hash": token_hash,
        "user_id": user["_id"],
        "created_at": now,
        "expires_at": refresh_expires_at,
    })

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        user=serialize_user(user),
    )
@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(request: RegisterRequest):
    now = utc_now()
    email = str(request.email).lower()

    user = {
        "name": request.name,
        "email": email,
        "password_hash": hash_password(
            request.password.get_secret_value()
        ),
        "avatar_url": None,
        "bio": None,
        "education": None,
        "target_role": None,
        "skills": [],
        "preferences": UserPreferences().model_dump(
            mode="json"
        ),
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = await users_collection.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user["_id"] = result.inserted_id
    return await issue_token_pair(user)


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    email = str(request.email).lower()

    user = await users_collection.find_one({"email": email})

    if user is None or not verify_password(
        request.password.get_secret_value(),
        user["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await issue_token_pair(user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_tokens(request: RefreshRequest):
    now = utc_now()
    raw_token = request.refresh_token.get_secret_value()
    token_hash = hash_refresh_token(raw_token)

    # Atomically consume the old token. Only one concurrent
    # refresh request can successfully consume this session.
    session = await refresh_sessions_collection.find_one_and_delete(
        {
            "token_hash": token_hash,
            "expires_at": {"$gt": now},
        }
    )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already-used refresh token",
        )

    user = await users_collection.find_one(
        {"_id": session["user_id"]}
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account no longer exists",
        )

    return await issue_token_pair(user)


@router.get(
    "/verify",
    response_model=TokenVerificationResponse,
)
async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    user: dict = Depends(get_current_user),
):
    # get_current_user has already validated the token.
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing access token",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    return TokenVerificationResponse(
        valid=True,
        user_id=str(user["_id"]),
        expires_at=int(payload["exp"]),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(request: LogoutRequest):
    token_hash = hash_refresh_token(
        request.refresh_token.get_secret_value()
    )

    await refresh_sessions_collection.delete_one(
        {"token_hash": token_hash}
    )

    return MessageResponse(message="Logged out successfully")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
)
async def logout_all(user: dict = Depends(get_current_user)):
    await refresh_sessions_collection.delete_many(
        {"user_id": user["_id"]}
    )

    return MessageResponse(
        message="Logged out from all devices successfully"
    )
