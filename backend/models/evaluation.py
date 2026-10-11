
from datetime import datetime

from pydantic import Field

from models.common import Schema, TimestampedSchema


class CategoryScore(Schema):
    category: str
    score: float = Field(ge=0, le=100)
    feedback: str = Field(max_length=2000)


class EvaluationDocument(TimestampedSchema):
    id: str
    user_id: str
    interview_id: str
    overall_score: float = Field(ge=0, le=100)
    communication_score: float = Field(ge=0, le=100)
    technical_score: float = Field(ge=0, le=100)
    relevance_score: float = Field(ge=0, le=100)
    confidence_score: float | None = Field(
        default=None, ge=0, le=100
    )
    category_scores: list[CategoryScore] = Field(
        default_factory=list
    )
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    summary: str = Field(max_length=5000)
    recommended_topics: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class EvaluationResponse(EvaluationDocument):
    pass


class RecentInterviewSummary(Schema):
    interview_id: str
    topic: str
    mode: str
    overall_score: float | None = None
    completed_at: datetime | None = None


class ProgressResponse(Schema):
    total_completed: int
    average_score: float | None = None
    recent_interviews: list[RecentInterviewSummary] = Field(
        default_factory=list
    )
    strongest_topics: list[str] = Field(default_factory=list)
    topics_to_improve: list[str] = Field(default_factory=list)
