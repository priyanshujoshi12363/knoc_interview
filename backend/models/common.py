
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Schema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class PyObjectId(str):
    pass


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class InterviewMode(str, Enum):
    PRACTICE = "practice"
    LIVE = "live"


class InterviewStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Speaker(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class HintMode(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    BOTH = "both"


class TimestampedSchema(Schema):
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
