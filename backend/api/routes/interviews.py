
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import ReturnDocument

from api.deps import get_current_user
from db.index import interviews_collection, interview_turns_collection
from models.common import InterviewStatus, utc_now
from models.interview import (
    CreateInterviewRequest,
    InterviewDocument,
    InterviewListItem,
    InterviewListResponse,
    StartInterviewResponse,
    ConversationTurnDocument,
    InterviewDetailResponse,
    EndInterviewRequest,
)


router = APIRouter(
    prefix="/api/v1/interviews",
    tags=["Interviews"],
)

def serialize_interview(document: dict) -> InterviewDocument:
    """Convert a MongoDB interview document into your API model."""
    return InterviewDocument.model_validate(
        {
            "id": str(document["_id"]),
            "user_id": str(document["user_id"]),
            "mode": document["mode"],
            "topic": document["topic"],
            "target_role": document.get("target_role"),
            "difficulty": document["difficulty"],
            "status": document["status"],
            "question_count": document.get("question_count", 10),
            "duration_minutes": document.get("duration_minutes", 15),
            "hint_mode": document.get("hint_mode", "both"),
            "language": document.get("language", "en"),
            "questions_asked": document.get("questions_asked", 0),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
            "started_at": document.get("started_at"),
            "ended_at": document.get("ended_at"),
        }
    )


def serialize_turn(document: dict) -> ConversationTurnDocument:
    """Convert a MongoDB conversation turn into your API model."""
    return ConversationTurnDocument.model_validate(
        {
            "id": str(document["_id"]),
            "interview_id": str(document["interview_id"]),
            "user_id": str(document["user_id"]),
            "sequence_number": document["sequence_number"],
            "speaker": document["speaker"],
            "content": document["content"],
            "question_id": document.get("question_id"),
            "is_follow_up": document.get("is_follow_up", False),
            "is_hint": document.get("is_hint", False),
            "duration_seconds": document.get("duration_seconds"),
            "metadata": document.get("metadata", {}),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
        }
    )


def get_owned_interview_query(
    interview_id: str,
    user_id: ObjectId,
) -> dict:
    """Ensure the interview ID is valid and belongs to this user."""
    if not ObjectId.is_valid(interview_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    return {
        "_id": ObjectId(interview_id),
        "user_id": user_id,
    }


async def get_owned_interview(
    interview_id: str,
    user_id: ObjectId,
) -> dict:
    """Fetch an interview only when it belongs to the current user."""
    query = get_owned_interview_query(interview_id, user_id)
    document = await interviews_collection.find_one(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    return document

@router.post(
    "",
    response_model=InterviewDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_interview(
    request: CreateInterviewRequest,
    user: dict = Depends(get_current_user),
):
    now = utc_now()

    document = {
        "user_id": user["_id"],
        "mode": request.mode.value,
        "topic": request.topic,
        "target_role": request.target_role,
        "difficulty": request.difficulty.value,
        "question_count": request.question_count,
        "duration_minutes": request.duration_minutes,
        "hint_mode": request.hint_mode.value,
        "language": request.language,
        "resume_text": request.resume_text,
        "job_description": request.job_description,
        "questions_asked": 0,
        "status": InterviewStatus.CREATED.value,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "ended_at": None,
        "score": None,
    }

    result = await interviews_collection.insert_one(document)
    document["_id"] = result.inserted_id

    return serialize_interview(document)

@router.get(
    "",
    response_model=InterviewListResponse,
)
async def list_interviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    query = {"user_id": user["_id"]}

    total = await interviews_collection.count_documents(query)

    cursor = (
        interviews_collection
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    documents = await cursor.to_list(length=page_size)

    items = [
        InterviewListItem.model_validate(
            {
                "id": str(document["_id"]),
                "mode": document["mode"],
                "topic": document["topic"],
                "target_role": document.get("target_role"),
                "status": document["status"],
                "score": document.get("score"),
                "created_at": document["created_at"],
                "ended_at": document.get("ended_at"),
            }
        )
        for document in documents
    ]

    return InterviewListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{interview_id}",
    response_model=InterviewDetailResponse,
)
async def get_interview(
    interview_id: str,
    user: dict = Depends(get_current_user),
):
    document = await get_owned_interview(
        interview_id,
        user["_id"],
    )

    cursor = (
        interview_turns_collection
        .find(
            {
                "interview_id": document["_id"],
                "user_id": user["_id"],
            }
        )
        .sort("sequence_number", 1)
        .limit(2000)
    )

    turn_documents = await cursor.to_list(length=2000)
    turns = [serialize_turn(turn) for turn in turn_documents]

    interview_data = serialize_interview(document).model_dump()

    return InterviewDetailResponse(
        **interview_data,
        turns=turns,
    )


@router.post(
    "/{interview_id}/start",
    response_model=StartInterviewResponse,
)
async def start_interview(
    interview_id: str,
    user: dict = Depends(get_current_user),
):
    query = get_owned_interview_query(
        interview_id,
        user["_id"],
    )

    now = utc_now()

    document = await interviews_collection.find_one_and_update(
        {
            **query,
            "status": InterviewStatus.CREATED.value,
        },
        {
            "$set": {
                "status": InterviewStatus.IN_PROGRESS.value,
                "started_at": now,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if document is None:
        existing = await interviews_collection.find_one(query)

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Interview cannot be started from status "
                f"'{existing['status']}'."
            ),
        )

    return StartInterviewResponse(
        interview_id=str(document["_id"]),
        status=InterviewStatus.IN_PROGRESS,
        message="Interview started successfully.",
    )


@router.post("/{interview_id}/end")
async def end_interview(
    interview_id: str,
    request: EndInterviewRequest | None = None,
    user: dict = Depends(get_current_user),
):
    query = get_owned_interview_query(
        interview_id,
        user["_id"],
    )

    now = utc_now()

    update_fields = {
        "status": InterviewStatus.COMPLETED.value,
        "ended_at": now,
        "updated_at": now,
    }

    if request and request.reason:
        update_fields["end_reason"] = request.reason

    document = await interviews_collection.find_one_and_update(
        {
            **query,
            "status": InterviewStatus.IN_PROGRESS.value,
        },
        {"$set": update_fields},
        return_document=ReturnDocument.AFTER,
    )

    if document is None:
        existing = await interviews_collection.find_one(query)

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Interview cannot be ended from status "
                f"'{existing['status']}'."
            ),
        )

    turn_count = await interview_turns_collection.count_documents(
        {
            "interview_id": document["_id"],
            "user_id": user["_id"],
        }
    )

    summary = (
        f"Interview completed. {turn_count} conversation turns saved. "
        "AI evaluation has not been generated yet."
    )

    await interviews_collection.update_one(
        {
            "_id": document["_id"],
            "user_id": user["_id"],
        },
        {
            "$set": {
                "final_summary": summary,
                "updated_at": now,
            }
        },
    )

    return {
        "interview": serialize_interview(document).model_dump(mode="json"),
        "message": "Interview ended successfully.",
        "summary": summary,
        "turn_count": turn_count,
    }
