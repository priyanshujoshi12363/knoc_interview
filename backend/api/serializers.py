
from models.user import UserProfile


def serialize_user(document: dict) -> UserProfile:
    return UserProfile.model_validate(
        {
            "id": str(document["_id"]),
            "name": document["name"],
            "email": document["email"],
            "avatar_url": document.get("avatar_url"),
            "bio": document.get("bio"),
            "education": document.get("education"),
            "target_role": document.get("target_role"),
            "skills": document.get("skills", []),
            "preferences": document.get("preferences", {}),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
        }
    )
