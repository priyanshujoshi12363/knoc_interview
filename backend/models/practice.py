from datetime import datetime
from typing import Any

from pydantic import Field

from models.common import (
    Schema,
    TimestampedSchema,
    Difficulty,
    InterviewStatus,
    Speaker,
)


class CreatePracticeSessionRequest(Schema):
    topic: str = Field(min_length=2, max_length=150)
    target_role: str | None = Field(default=None, max_length=100)
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    question_count: int = Field(default=5, ge=1, le=30)
    language: str = Field(default="en", min_length=2, max_length=5)


class PracticeSessionResponse(Schema):
    id: str
    user_id: str
    topic: str
    target_role: str | None = None
    difficulty: Difficulty
    status: InterviewStatus
    question_count: int
    questions_asked: int = 0
    language: str = "en"
    score: float | None = None
    final_summary: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


class PracticeSessionListResponse(Schema):
    items: list[PracticeSessionResponse]
    total: int = Field(ge=0)


class PracticeQuestion(Schema):
    text: str
    number: int = Field(ge=1)
    is_follow_up: bool = False
    audio_b64: str | None = None


class StartPracticeResponse(Schema):
    session_id: str
    status: InterviewStatus
    message: str
    first_question: PracticeQuestion


class PracticeTurnEvaluation(Schema):
    score: float = Field(ge=0, le=100)
    correctness: str = ""
    completeness: str = ""
    reasoning: str = ""
    feedback: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class SubmitAnswerResponse(Schema):
    session_id: str
    transcript: str
    evaluation: PracticeTurnEvaluation
    next_question: PracticeQuestion | None = None
    interview_completed: bool = False
    final_summary: str | None = None
    final_score: float | None = None
    action: str


class PracticeTurnDocument(TimestampedSchema):
    id: str
    session_id: str
    user_id: str
    sequence_number: int = Field(ge=1)
    speaker: Speaker
    content: str = Field(min_length=1, max_length=15000)
    is_follow_up: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PracticeSessionDetail(PracticeSessionResponse):
    turns: list[PracticeTurnDocument] = Field(default_factory=list)


class EndPracticeRequest(Schema):
    reason: str | None = Field(default=None, max_length=200)


class EndPracticeResponse(Schema):
    session_id: str
    status: InterviewStatus
    message: str
    score: float | None = None
    final_summary: str | None = None
    turn_count: int = Field(default=0, ge=0)