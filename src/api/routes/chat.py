from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_chat_service, get_current_user_id
from schemas.chat_api import (
    ChatQueryRequest,
    ChatQueryResponse,
    ChatSessionDetail,
    ChatSessionListResponse,
)
from services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/query", response_model=ChatQueryResponse)
def query_chat(
    request: ChatQueryRequest,
    owner_id: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service),  # noqa: B008
) -> ChatQueryResponse:
    return ChatQueryResponse.model_validate(
        chat_service.query(
            owner_id=owner_id,
            question=request.question,
            session_id=request.session_id,
            retrieval_mode=request.retrieval_mode,
            top_k=request.top_k,
        )
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions(
    owner_id: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service),  # noqa: B008
) -> ChatSessionListResponse:
    return ChatSessionListResponse(sessions=chat_service.list_sessions(owner_id))


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
def get_session(
    session_id: str,
    owner_id: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service),  # noqa: B008
) -> ChatSessionDetail:
    try:
        return ChatSessionDetail.model_validate(chat_service.get_session(session_id, owner_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    owner_id: str = Depends(get_current_user_id),
    chat_service: ChatService = Depends(get_chat_service),  # noqa: B008
) -> dict[str, bool]:
    deleted = chat_service.delete_session(session_id, owner_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": True}
