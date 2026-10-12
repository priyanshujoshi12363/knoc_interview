import base64

from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pymongo import ReturnDocument

from api.deps import get_current_user
from db.index import interviews_collection, interview_turns_collection
from models.common import (
    InterviewMode,
    InterviewStatus,
    Speaker,
    utc_now,
)
from models.practice import (
    CreatePracticeSessionRequest,
    PracticeSessionResponse,
    PracticeSessionListResponse,
    PracticeSessionDetail,
    PracticeQuestion,
    PracticeTurnEvaluation,
    PracticeTurnDocument,
    StartPracticeResponse,
    SubmitAnswerResponse,
    EndPracticeRequest,
    EndPracticeResponse,
)
from services.live_copilot import (
    ProviderConfigurationError,
    conduct_interview_turn,
    synthesize_speech,
    transcribe_pcm,
)


router = APIRouter(
    prefix="/api/v1/practice",
    tags=["Practice Mode"],
)

MAX_ANSWER_BYTES = 5_000_000
SUPPORTED_LANGUAGES = {"en", "hi"}


def _validate_language(lang: str) -> str:
    lang = lang.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{lang}'. Allowed: {sorted(SUPPORTED_LANGUAGES)}",
        )
    return lang


def _session_query(session_id: str, user_id: ObjectId) -> dict:
    if not ObjectId.is_valid(session_id):
        raise HTTPException(404, "Practice session not found")
    return {
        "_id": ObjectId(session_id),
        "user_id": user_id,
        "mode": InterviewMode.PRACTICE.value,
    }


async def _get_owned_session(session_id: str, user_id: ObjectId) -> dict:
    query = _session_query(session_id, user_id)
    doc = await interviews_collection.find_one(query)
    if doc is None:
        raise HTTPException(404, "Practice session not found")
    return doc


def _serialize_session(doc: dict) -> PracticeSessionResponse:
    return PracticeSessionResponse(
        id=str(doc["_id"]),
        user_id=str(doc["user_id"]),
        topic=doc["topic"],
        target_role=doc.get("target_role"),
        difficulty=doc["difficulty"],
        status=doc["status"],
        question_count=doc.get("question_count", 5),
        questions_asked=doc.get("questions_asked", 0),
        language=doc.get("language", "en"),
        score=doc.get("score"),
        final_summary=doc.get("final_summary"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        started_at=doc.get("started_at"),
        ended_at=doc.get("ended_at"),
    )


def _serialize_turn(doc: dict) -> PracticeTurnDocument:
    return PracticeTurnDocument(
        id=str(doc["_id"]),
        session_id=str(doc["interview_id"]),
        user_id=str(doc["user_id"]),
        sequence_number=doc["sequence_number"],
        speaker=doc["speaker"],
        content=doc["content"],
        is_follow_up=doc.get("is_follow_up", False),
        metadata=doc.get("metadata", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _load_conversation(session_id: ObjectId, user_id: ObjectId) -> list[dict]:
    cursor = (
        interview_turns_collection
        .find({"interview_id": session_id, "user_id": user_id})
        .sort("sequence_number", 1)
        .limit(500)
    )
    turns = await cursor.to_list(length=500)
    return [
        {
            "role": "interviewer" if t["speaker"] == Speaker.AI.value else "candidate",
            "content": t["content"],
        }
        for t in turns
    ]


async def _save_turn(
    *,
    session_id: ObjectId,
    user_id: ObjectId,
    sequence_number: int,
    speaker: str,
    content: str,
    is_follow_up: bool = False,
    metadata: dict | None = None,
) -> ObjectId:
    now = utc_now()
    doc = {
        "interview_id": session_id,
        "user_id": user_id,
        "sequence_number": sequence_number,
        "speaker": speaker,
        "content": content,
        "question_id": None,
        "is_follow_up": is_follow_up,
        "is_hint": False,
        "duration_seconds": None,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    result = await interview_turns_collection.insert_one(doc)
    return result.inserted_id


async def _tts_b64(text: str, language: str) -> str | None:
    try:
        audio = await synthesize_speech(text, language=language)
        return base64.b64encode(audio).decode("ascii")
    except ProviderConfigurationError:
        return None
    except Exception:
        return None


@router.post(
    "/sessions",
    response_model=PracticeSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_practice_session(
    request: CreatePracticeSessionRequest,
    user: dict = Depends(get_current_user),
):
    language = _validate_language(request.language)
    now = utc_now()

    doc = {
        "user_id": user["_id"],
        "mode": InterviewMode.PRACTICE.value,
        "topic": request.topic,
        "target_role": request.target_role,
        "difficulty": request.difficulty.value,
        "question_count": request.question_count,
        "duration_minutes": 15,
        "hint_mode": "both",
        "language": language,
        "resume_text": None,
        "job_description": None,
        "questions_asked": 0,
        "status": InterviewStatus.CREATED.value,
        "score": None,
        "final_summary": None,
        "evaluations": [],
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "ended_at": None,
    }

    result = await interviews_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_session(doc)


@router.get(
    "/sessions",
    response_model=PracticeSessionListResponse,
)
async def list_practice_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {
        "user_id": user["_id"],
        "mode": InterviewMode.PRACTICE.value,
    }
    total = await interviews_collection.count_documents(query)
    cursor = (
        interviews_collection
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    return PracticeSessionListResponse(
        items=[_serialize_session(d) for d in docs],
        total=total,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=PracticeSessionDetail,
)
async def get_practice_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    doc = await _get_owned_session(session_id, user["_id"])

    cursor = (
        interview_turns_collection
        .find({"interview_id": doc["_id"], "user_id": user["_id"]})
        .sort("sequence_number", 1)
        .limit(2000)
    )
    turn_docs = await cursor.to_list(length=2000)

    session = _serialize_session(doc)
    return PracticeSessionDetail(
        **session.model_dump(),
        turns=[_serialize_turn(t) for t in turn_docs],
    )


@router.post(
    "/sessions/{session_id}/start",
    response_model=StartPracticeResponse,
)
async def start_practice_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    query = _session_query(session_id, user["_id"])
    now = utc_now()

    doc = await interviews_collection.find_one_and_update(
        {**query, "status": InterviewStatus.CREATED.value},
        {
            "$set": {
                "status": InterviewStatus.IN_PROGRESS.value,
                "started_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if doc is None:
        existing = await interviews_collection.find_one(query)
        if existing is None:
            raise HTTPException(404, "Practice session not found")
        raise HTTPException(
            409,
            f"Cannot start from status '{existing['status']}'.",
        )

    language = doc.get("language", "en")
    target_role = doc.get("target_role") or "Candidate"
    topic = doc["topic"]
    difficulty = doc["difficulty"]
    question_limit = doc.get("question_count", 5)

    try:
        turn_data = await conduct_interview_turn(
            target_role=target_role,
            topic=topic,
            difficulty=difficulty,
            language=language,
            question_number=1,
            question_limit=question_limit,
            conversation=[],
            candidate_answer=None,
        )
    except ProviderConfigurationError as exc:
        raise HTTPException(503, "Interview AI is not configured.") from exc

    q_text = turn_data["question"]

    await _save_turn(
        session_id=doc["_id"],
        user_id=user["_id"],
        sequence_number=1,
        speaker=Speaker.AI.value,
        content=q_text,
        metadata={"action": turn_data["action"], "topic": turn_data["topic"]},
    )

    audio_b64 = await _tts_b64(q_text, language)

    await interviews_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {"questions_asked": 1, "updated_at": utc_now()}},
    )

    return StartPracticeResponse(
        session_id=str(doc["_id"]),
        status=InterviewStatus.IN_PROGRESS,
        message="Practice session started.",
        first_question=PracticeQuestion(
            text=q_text,
            number=1,
            is_follow_up=False,
            audio_b64=audio_b64,
        ),
    )


@router.post(
    "/sessions/{session_id}/answer",
    response_model=SubmitAnswerResponse,
)
async def submit_practice_answer(
    session_id: str,
    audio: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    doc = await _get_owned_session(session_id, user["_id"])

    if doc["status"] != InterviewStatus.IN_PROGRESS.value:
        raise HTTPException(409, "Practice session is not in progress.")

    pcm = await audio.read()
    if not pcm:
        raise HTTPException(400, "Empty audio.")
    if len(pcm) > MAX_ANSWER_BYTES:
        raise HTTPException(
            413,
            f"Audio too large ({len(pcm)} bytes, max {MAX_ANSWER_BYTES}).",
        )

    language = doc.get("language", "en")

    try:
        transcript = await transcribe_pcm(pcm, language=language)
    except ProviderConfigurationError as exc:
        raise HTTPException(503, "STT is not configured.") from exc

    if not transcript.strip():
        raise HTTPException(400, "Could not detect speech in your answer.")

    conversation = await _load_conversation(doc["_id"], user["_id"])

    turns_before = await interview_turns_collection.count_documents(
        {"interview_id": doc["_id"], "user_id": user["_id"]}
    )
    candidate_seq = turns_before + 1

    await _save_turn(
        session_id=doc["_id"],
        user_id=user["_id"],
        sequence_number=candidate_seq,
        speaker=Speaker.USER.value,
        content=transcript,
    )

    target_role = doc.get("target_role") or "Candidate"
    topic = doc["topic"]
    difficulty = doc["difficulty"]
    question_limit = doc.get("question_count", 5)
    questions_asked = doc.get("questions_asked", 0)

    try:
        turn_data = await conduct_interview_turn(
            target_role=target_role,
            topic=topic,
            difficulty=difficulty,
            language=language,
            question_number=questions_asked,
            question_limit=question_limit,
            conversation=conversation,
            candidate_answer=transcript,
        )
    except ProviderConfigurationError as exc:
        raise HTTPException(503, "Interview AI is not configured.") from exc

    evaluations = doc.get("evaluations", [])
    evaluations.append(turn_data["evaluation"])
    new_questions_asked = questions_asked + 1

    await interviews_collection.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "evaluations": evaluations,
                "questions_asked": new_questions_asked,
                "difficulty": turn_data["difficulty"],
                "topic": turn_data["topic"],
                "updated_at": utc_now(),
            }
        },
    )

    evaluation = PracticeTurnEvaluation(**turn_data["evaluation"])

    if turn_data["action"] == "finish":
        scores = [e.get("score", 0) for e in evaluations]
        avg = int(sum(scores) / len(scores)) if scores else 0
        final_summary = turn_data["final_summary"] or "Interview completed."

        await interviews_collection.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": InterviewStatus.COMPLETED.value,
                    "score": avg,
                    "final_summary": final_summary,
                    "ended_at": utc_now(),
                    "updated_at": utc_now(),
                }
            },
        )

        return SubmitAnswerResponse(
            session_id=str(doc["_id"]),
            transcript=transcript,
            evaluation=evaluation,
            next_question=None,
            interview_completed=True,
            final_summary=final_summary,
            final_score=float(avg),
            action=turn_data["action"],
        )

    next_q_text = turn_data["question"]
    next_q_number = new_questions_asked + 1

    await _save_turn(
        session_id=doc["_id"],
        user_id=user["_id"],
        sequence_number=candidate_seq + 1,
        speaker=Speaker.AI.value,
        content=next_q_text,
        is_follow_up=(turn_data["action"] == "follow_up"),
        metadata={"action": turn_data["action"], "topic": turn_data["topic"]},
    )

    audio_b64 = await _tts_b64(next_q_text, language)

    return SubmitAnswerResponse(
        session_id=str(doc["_id"]),
        transcript=transcript,
        evaluation=evaluation,
        next_question=PracticeQuestion(
            text=next_q_text,
            number=next_q_number,
            is_follow_up=(turn_data["action"] == "follow_up"),
            audio_b64=audio_b64,
        ),
        interview_completed=False,
        final_summary=None,
        final_score=None,
        action=turn_data["action"],
    )


@router.post(
    "/sessions/{session_id}/end",
    response_model=EndPracticeResponse,
)
async def end_practice_session(
    session_id: str,
    request: EndPracticeRequest | None = None,
    user: dict = Depends(get_current_user),
):
    query = _session_query(session_id, user["_id"])
    now = utc_now()

    update_fields = {
        "status": InterviewStatus.COMPLETED.value,
        "ended_at": now,
        "updated_at": now,
    }
    if request and request.reason:
        update_fields["end_reason"] = request.reason

    doc = await interviews_collection.find_one_and_update(
        {**query, "status": InterviewStatus.IN_PROGRESS.value},
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )

    if doc is None:
        existing = await interviews_collection.find_one(query)
        if existing is None:
            raise HTTPException(404, "Practice session not found")
        raise HTTPException(
            409,
            f"Cannot end from status '{existing['status']}'.",
        )

    turn_count = await interview_turns_collection.count_documents(
        {"interview_id": doc["_id"], "user_id": user["_id"]}
    )

    evaluations = doc.get("evaluations", [])
    computed_score = None
    if evaluations:
        scores = [e.get("score", 0) for e in evaluations]
        computed_score = int(sum(scores) / len(scores))

    summary = doc.get("final_summary")
    if not summary:
        summary = f"Practice ended with {turn_count} turns."
        if computed_score is not None:
            summary += f" Average score: {computed_score}/100."

    await interviews_collection.update_one(
        {"_id": doc["_id"], "user_id": user["_id"]},
        {
            "$set": {
                "final_summary": summary,
                "score": computed_score if computed_score is not None else doc.get("score"),
                "updated_at": now,
            }
        },
    )

    return EndPracticeResponse(
        session_id=str(doc["_id"]),
        status=InterviewStatus.COMPLETED,
        message="Practice session ended.",
        score=computed_score if computed_score is not None else doc.get("score"),
        final_summary=summary,
        turn_count=turn_count,
    )