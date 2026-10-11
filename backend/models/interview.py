
from datetime import datetime

from pydantic import Field, model_validator

from models.common import (
    Schema,
    TimestampedSchema,
    Difficulty,
    InterviewMode,
    InterviewStatus,
    Speaker,
    HintMode,
)


class CreateInterviewRequest(Schema):
    mode: InterviewMode
    topic: str = Field(min_length=2, max_length=150)
    target_role: str | None = Field(default=None, max_length=100)
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    question_count: int = Field(default=10, ge=1, le=50)
    duration_minutes: int = Field(default=15, ge=1, le=120)
    hint_mode: HintMode = HintMode.BOTH
    language: str = Field(default="en", max_length=20)
    resume_text: str | None = Field(default=None, max_length=15000)
    job_description: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_live_interview(self):
        if self.mode == InterviewMode.LIVE:
            # Live interview must use voice interaction.
            # The API service will enforce the voice session.
            pass
        return self


class InterviewDocument(TimestampedSchema):
    id: str
    user_id: str
    mode: InterviewMode
    topic: str
    target_role: str | None = None
    difficulty: Difficulty
    status: InterviewStatus = InterviewStatus.CREATED
    question_count: int = 10
    duration_minutes: int = 15
    hint_mode: HintMode = HintMode.BOTH
    language: str = "en"
    questions_asked: int = 0
    started_at: datetime | None = None
    ended_at: datetime | None = None


class StartInterviewResponse(Schema):
    interview_id: str
    status: InterviewStatus
    message: str


class InterviewListItem(Schema):
    id: str
    mode: InterviewMode
    topic: str
    target_role: str | None = None
    status: InterviewStatus
    score: float | None = None
    created_at: datetime
    ended_at: datetime | None = None


class InterviewListResponse(Schema):
    items: list[InterviewListItem]
    total: int
    page: int = 1
    page_size: int = 20


class SubmitAnswerRequest(Schema):
    interview_id: str
    question_id: str
    answer_text: str = Field(min_length=1, max_length=15000)
    answer_duration_seconds: int | None = Field(
        default=None, ge=0, le=7200
    )


class QuestionResponse(Schema):
    question_id: str
    question_text: str
    question_number: int
    is_follow_up: bool = False


class HintRequest(Schema):
    interview_id: str
    question_id: str
    user_requested: bool = True


class HintResponse(Schema):
    hint: str
    hint_level: int = Field(ge=1, le=3)


class ConversationTurnDocument(TimestampedSchema):
    id: str
    interview_id: str
    user_id: str
    sequence_number: int = Field(ge=1)
    speaker: Speaker
    content: str = Field(min_length=1, max_length=15000)
    question_id: str | None = None
    is_follow_up: bool = False
    is_hint: bool = False
    duration_seconds: int | None = Field(default=None, ge=0)
    metadata: dict = Field(default_factory=dict)


class EndInterviewRequest(Schema):
    reason: str | None = Field(default=None, max_length=200)


class InterviewDetailResponse(InterviewDocument):
    turns: list[ConversationTurnDocument] = Field(
        default_factory=list
    )
