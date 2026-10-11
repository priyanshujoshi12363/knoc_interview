
from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from api.deps import get_current_user
from api.serializers import serialize_user
from db.index import users_collection
from models.common import utc_now
from models.user import UserProfile, UpdateProfileRequest


router = APIRouter(
    prefix="/api/v1/users",
    tags=["User Profile"],
)


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    user: dict = Depends(get_current_user),
):
    return serialize_user(user)


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(
    request: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    updates = request.model_dump(
        exclude_unset=True,
        mode="json",
    )

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update",
        )

    # These fields must not be explicitly set to null.
    for field in ("name", "skills", "preferences"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    updates["updated_at"] = utc_now()

    updated_user = await users_collection.find_one_and_update(
        {"_id": user["_id"]},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )

    if updated_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return serialize_user(updated_user)
