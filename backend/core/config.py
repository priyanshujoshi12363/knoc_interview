import os

from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

JWT_ACCESS_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30")
)
JWT_REFRESH_EXPIRE_DAYS = int(
    os.getenv("JWT_REFRESH_EXPIRE_DAYS", "30")
)

if not MONGODB_URL:
    raise RuntimeError("MONGODB_URL is missing from .env")

if not JWT_SECRET_KEY or len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a secret of at least 32 characters"
    )

if JWT_ACCESS_EXPIRE_MINUTES < 1 or JWT_REFRESH_EXPIRE_DAYS < 1:
    raise RuntimeError("Token expiry settings must be positive")