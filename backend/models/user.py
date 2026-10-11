
from datetime import date

from pydantic import EmailStr, Field, HttpUrl

from models.common import (
    Schema,
    TimestampedSchema,
    Difficulty,
    HintMode,
)


class UserPreferences(Schema):
    preferred_topics: list[str] = Field(
        default_factory=list,
        max_length=30,
    )
    preferred_role: str | None = Field(
        default=None,
        max_length=100,
    )
    default_difficulty: Difficulty = Difficulty.INTERMEDIATE
    hint_mode: HintMode = HintMode.BOTH
    target_questions: int = Field(
        default=10,
        ge=1,
        le=50,
    )


class UserProfile(TimestampedSchema):
    id: str
    name: str = Field(
        min_length=2,
        max_length=80,
    )
    email: EmailStr
    avatar_url: HttpUrl | None = None
    bio: str | None = Field(
        default=None,
        max_length=300,
    )
    education: str | None = Field(
        default=None,
        max_length=150,
    )
    target_role: str | None = Field(
        default=None,
        max_length=100,
    )
    skills: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
    preferences: UserPreferences = Field(
        default_factory=UserPreferences,
    )


class UpdateProfileRequest(Schema):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=80,
    )
    avatar_url: HttpUrl | None = None
    bio: str | None = Field(
        default=None,
        max_length=300,
    )
    education: str | None = Field(
        default=None,
        max_length=150,
    )
    target_role: str | None = Field(
        default=None,
        max_length=100,
    )
    skills: list[str] | None = Field(
        default=None,
        max_length=50,
    )
    preferences: UserPreferences | None = None


class PracticeStreak(Schema):
    current_streak: int = Field(
        default=0,
        ge=0,
    )
    longest_streak: int = Field(
        default=0,
        ge=0,
    )
    last_practice_date: date | None = None


class DashboardStats(Schema):
    total_interviews: int = Field(default=0, ge=0)
    completed_interviews: int = Field(default=0, ge=0)
    practice_sessions: int = Field(default=0, ge=0)
    live_interviews: int = Field(default=0, ge=0)
    average_score: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    streak: PracticeStreak = Field(
        default_factory=PracticeStreak,
    )


class DashboardResponse(Schema):
    profile: UserProfile
    stats: DashboardStats
