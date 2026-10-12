from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

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
    mode: InterviewMode = InterviewMode.PRACTICE
    topic: str = Field(min_length=2, max_length=150)
    target_role: str | None = Field(default=None, max_length=100)
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    question_count: int = Field(default=10, ge=1, le=50)
    duration_minutes: int = Field(default=15, ge=1, le=120)
    hint_mode: HintMode = HintMode.BOTH
    language: str = Field(default="en", min_length=2, max_length=20)
    resume_text: str | None = Field(default=None, max_length=15000)
    job_description: str | None = Field(default=None, max_length=10000)


class InterviewDocument(TimestampedSchema):
    id: str
    user_id: str
    mode: InterviewMode
    topic: str
    target_role: str | None = None
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    status: InterviewStatus = InterviewStatus.CREATED
    question_count: int = Field(default=10, ge=1, le=50)
    duration_minutes: int = Field(default=15, ge=1, le=120)
    hint_mode: HintMode = HintMode.BOTH
    language: str = "en"
    questions_asked: int = Field(default=0, ge=0)
    score: float | None = Field(default=None, ge=0, le=100)
    final_summary: str | None = Field(default=None, max_length=10000)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class QuestionResponse(Schema):
    question_id: str | None = None
    question_text: str = Field(min_length=1, max_length=5000)
    question_number: int = Field(ge=1, le=50)
    is_follow_up: bool = False
    audio_url: str | None = None


class StartInterviewResponse(Schema):
    interview_id: str
    status: InterviewStatus
    message: str
    first_question: QuestionResponse | None = None
    first_question_audio_b64: str | None = None


class AnswerEvaluation(Schema):
    score: float = Field(ge=0, le=100)
    correctness: str = ""
    completeness: str = ""
    reasoning: str = ""
    feedback: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class SubmitVoiceAnswerResponse(Schema):
    interview_id: str
    transcript: str
    evaluation: AnswerEvaluation | None = None
    next_question: QuestionResponse | None = None
    next_question_audio_b64: str | None = None
    interview_completed: bool = False
    final_summary: str | None = None
    final_score: float | None = None


class AnalyzeChunkResponse(BaseModel):
    transcript: str
    should_respond: bool
    question: str
    answer: str


class HealthResponse(BaseModel):
    status: str
    stt_provider: str
    llm_provider: str


class LanguageOption(BaseModel):
    code: str
    label: str


class InterviewListItem(Schema):
    id: str
    mode: InterviewMode
    topic: str
    target_role: str | None = None
    status: InterviewStatus
    score: float | None = Field(default=None, ge=0, le=100)
    created_at: datetime
    ended_at: datetime | None = None


class InterviewListResponse(Schema):
    items: list[InterviewListItem]
    total: int = Field(ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class NextQuestionResponse(Schema):
    action: str = Field(min_length=1, max_length=40)
    question: QuestionResponse | None = None
    interview_completed: bool = False
    message: str | None = None


class SubmitAnswerRequest(Schema):
    question_id: str = Field(min_length=1, max_length=100)
    answer_text: str = Field(min_length=1, max_length=15000)
    answer_duration_seconds: int | None = Field(default=None, ge=0, le=7200)


class AnswerEvaluationResponse(Schema):
    interview_id: str
    question_id: str
    evaluation: AnswerEvaluation
    next_question: QuestionResponse | None = None
    interview_completed: bool = False


class InterviewEvaluation(Schema):
    overall_score: float = Field(ge=0, le=100)
    summary: str = Field(min_length=1, max_length=10000)
    strengths: list[str] = Field(default_factory=list, max_length=30)
    areas_to_improve: list[str] = Field(default_factory=list, max_length=30)
    recommendations: list[str] = Field(default_factory=list, max_length=30)


class HintRequest(Schema):
    interview_id: str
    question_id: str
    user_requested: bool = True


class HintResponse(Schema):
    hint: str = Field(min_length=1, max_length=3000)
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
    duration_seconds: int | None = Field(default=None, ge=0, le=7200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EndInterviewRequest(Schema):
    reason: str | None = Field(default=None, max_length=200)


class EndInterviewResponse(Schema):
    interview_id: str
    status: InterviewStatus
    message: str
    score: float | None = Field(default=None, ge=0, le=100)
    final_summary: str | None = None
    turn_count: int = Field(default=0, ge=0)


class InterviewDetailResponse(InterviewDocument):
    turns: list[ConversationTurnDocument] = Field(default_factory=list)