
from bson import ObjectId
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from core.security import decode_access_token
from db.index import users_collection


bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized_error() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    if credentials is None:
        raise unauthorized_error()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")

        if not isinstance(user_id, str) or not ObjectId.is_valid(user_id):
            raise unauthorized_error()

    except InvalidTokenError:
        raise unauthorized_error()

    user = await users_collection.find_one(
        {"_id": ObjectId(user_id)}
    )

    if user is None:
        raise unauthorized_error()

    return user
