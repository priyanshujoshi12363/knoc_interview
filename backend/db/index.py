from pymongo import AsyncMongoClient

from core.config import MONGODB_URL


client = AsyncMongoClient(MONGODB_URL)
db = client["knoc_interview"]

users_collection = db["users"]
refresh_sessions_collection = db["refresh_sessions"]
interviews_collection = db["interviews"]
interview_turns_collection = db["interview_turns"]
evaluations_collection = db["evaluations"]


async def connect_db():
    await client.admin.command("ping")

    await users_collection.create_index(
        "email",
        unique=True,
        name="unique_user_email",
    )

    await refresh_sessions_collection.create_index(
        "token_hash",
        unique=True,
        name="unique_refresh_token_hash",
    )

    await refresh_sessions_collection.create_index(
        "expires_at",
        expireAfterSeconds=0,
        name="refresh_session_ttl",
    )

    await refresh_sessions_collection.create_index(
        "user_id",
        name="refresh_sessions_by_user",
    )

    # No custom names — let Mongo auto-name these (matches existing indexes)
    await interviews_collection.create_index(
        [("user_id", 1), ("created_at", -1)],
    )

    await interview_turns_collection.create_index(
        [("interview_id", 1), ("sequence_number", 1)],
        unique=True,
    )

    await evaluations_collection.create_index(
        [("user_id", 1), ("interview_id", 1)],
        unique=True,
    )

    print("MongoDB connected; indexes verified")


async def close_db():
    await client.close()