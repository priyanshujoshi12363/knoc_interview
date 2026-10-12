import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)

from api.deps import get_current_user
from models.interview import (
    AnalyzeChunkResponse,
    HealthResponse,
    LanguageOption,
)
from services.live_copilot import (
    ProviderConfigurationError,
    analyze_interview_chunk,
)

router = APIRouter(
    prefix="/api/v1/interview",
    tags=["Interview Mode"],
)

MAX_CHUNK_BYTES = 640_000

SUPPORTED_LANGUAGES = [
    LanguageOption(code="en", label="English"),
    LanguageOption(code="hi", label="Hindi"),
]

SUPPORTED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


def _validate_difficulty(value: str) -> str:
    value = value.lower().strip()
    if value not in SUPPORTED_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid difficulty '{value}'. "
                f"Allowed: {sorted(SUPPORTED_DIFFICULTIES)}"
            ),
        )
    return value


def _validate_language(value: str) -> str:
    codes = {item.code for item in SUPPORTED_LANGUAGES}
    value = value.lower().strip()
    if value not in codes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{value}'. Allowed: {sorted(codes)}",
        )
    return value


def _parse_recent_context(raw: str | None) -> list[dict[str, str]]:
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="recent_context is not valid JSON.",
        ) from exc

    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="recent_context must be a JSON array.",
        )

    clean: list[dict[str, str]] = []
    for item in parsed[-20:]:
        if (
            isinstance(item, dict)
            and isinstance(item.get("role"), str)
            and isinstance(item.get("content"), str)
        ):
            clean.append(
                {"role": item["role"], "content": item["content"]}
            )

    return clean


@router.get("/languages", response_model=list[LanguageOption])
async def list_languages() -> list[LanguageOption]:
    return SUPPORTED_LANGUAGES


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        stt_provider="cloudflare-whisper",
        llm_provider="ollama",
    )


@router.post(
    "/analyze",
    response_model=AnalyzeChunkResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_chunk(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
    course: str = Form(default="General"),
    target_role: str | None = Form(default=None),
    difficulty: str = Form(default="intermediate"),
    topics: str | None = Form(default=None),
    recent_context: str | None = Form(default=None),
    user: dict = Depends(get_current_user),
) -> AnalyzeChunkResponse:
    pcm = await audio.read()

    if not pcm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio chunk.",
        )

    if len(pcm) > MAX_CHUNK_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Audio chunk too large ({len(pcm)} bytes, "
                f"max {MAX_CHUNK_BYTES}). Send 3-5 second chunks."
            ),
        )

    language = _validate_language(language)
    difficulty = _validate_difficulty(difficulty)

    topic_list: list[str] = []
    if topics:
        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    if not topic_list:
        topic_list = [course]

    context = _parse_recent_context(recent_context)

    try:
        result = await analyze_interview_chunk(
            pcm=pcm,
            language=language,
            course=course,
            target_role=target_role,
            difficulty=difficulty,
            topics=topic_list,
            recent_context=context,
        )
    except ProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Interview co-pilot is not configured on the server.",
        ) from exc

    return AnalyzeChunkResponse(**result)