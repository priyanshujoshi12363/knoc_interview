import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL is missing from .env")

client = AsyncMongoClient(MONGODB_URL)

db = client["knoc_interview"]

users_collection = db["users"]
interviews_collection = db["interviews"]
interview_turns_collection = db["interview_turns"]
evaluations_collection = db["evaluations"]


async def connect_db():
    await client.admin.command("ping")
    print(" MongoDB Atlas connected successfully!")


async def close_db():
    await client.close()