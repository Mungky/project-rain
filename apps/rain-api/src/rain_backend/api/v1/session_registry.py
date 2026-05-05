"""Session Registry API endpoints — cross-AI handoff and state management."""

import logging
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from rain_backend.api.deps import get_db
from rain_brain.services.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SessionStateResponse(BaseModel):
    id: str
    session_key: str
    source_ai: str
    context_summary: str
    active_task: str | None
    key_decisions: list | None
    next_steps: list | None
    artifacts: dict | None
    hand_off_to: str | None
    is_active: bool
    expires_at: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class HandoffBody(BaseModel):
    source_ai: str = Field(..., description="Which AI is handing off: rain, claude, claude_code, etc.")
    context_summary: str = Field(..., min_length=10, description="Dense summary of work done.")
    active_task: str | None = Field(None, description="In-progress task, if any.")
    key_decisions: list[dict] | None = Field(None, description="Key decisions: [{decision, rationale}].")
    next_steps: list[str] | None = Field(None, description="Ordered next steps for receiving AI.")
    artifacts: dict | None = Field(None, description="Files, URLs, code snippets produced.")
    hand_off_to: str | None = Field(None, description="Target AI for the handoff.")
    session_key: str | None = Field(None, description="Optional custom session key.")
    expires_at: datetime | None = Field(None, description="Optional TTL for the session state.")


class UpdateSessionBody(BaseModel):
    context_summary: str | None = None
    active_task: str | None = None
    key_decisions: list[dict] | None = None
    next_steps: list[str] | None = None
    artifacts: dict | None = None
    hand_off_to: str | None = None
    is_active: bool | None = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/active", response_model=SessionStateResponse | None)
async def get_active_session(
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse | None:
    """Return the current active session state. Returns null if none exists."""
    service = SessionService(db)
    state = await service.get_active_session()
    if state is None:
        return None
    return _to_response(state)


@router.get("", response_model=list[SessionStateResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
) -> list[SessionStateResponse]:
    service = SessionService(db)
    sessions = await service.list_sessions()
    return [_to_response(s) for s in sessions]


@router.post("/handoff", response_model=SessionStateResponse, status_code=status.HTTP_201_CREATED)
async def create_handoff(
    body: HandoffBody,
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    """Create a new session state for handoff to another AI.

    Automatically deactivates the previous active session.
    """
    service = SessionService(db)
    state = await service.handoff(
        source_ai=body.source_ai,
        context_summary=body.context_summary,
        active_task=body.active_task,
        key_decisions=body.key_decisions,
        next_steps=body.next_steps,
        artifacts=body.artifacts,
        hand_off_to=body.hand_off_to,
        session_key=body.session_key,
        expires_at=body.expires_at,
    )
    return _to_response(state)


@router.put("/{session_id}", response_model=SessionStateResponse)
async def update_session(
    session_id: UUID,
    body: UpdateSessionBody,
    db: AsyncSession = Depends(get_db),
) -> SessionStateResponse:
    service = SessionService(db)
    state = await service.update_session(
        session_id=session_id,
        context_summary=body.context_summary,
        active_task=body.active_task,
        key_decisions=body.key_decisions,
        next_steps=body.next_steps,
        artifacts=body.artifacts,
        hand_off_to=body.hand_off_to,
        is_active=body.is_active,
    )
    if state is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Session not found."},
        )
    return _to_response(state)


@router.post("/{session_id}/close", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = SessionService(db)
    success = await service.close_session(session_id=session_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Session not found."},
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = SessionService(db)
    success = await service.delete_session(session_id=session_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Session not found."},
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(state) -> SessionStateResponse:
    return SessionStateResponse(
        id=str(state.id),
        session_key=state.session_key,
        source_ai=state.source_ai,
        context_summary=state.context_summary,
        active_task=state.active_task,
        key_decisions=state.key_decisions,
        next_steps=state.next_steps,
        artifacts=state.artifacts,
        hand_off_to=state.hand_off_to,
        is_active=state.is_active,
        expires_at=state.expires_at.isoformat() if state.expires_at else None,
        created_at=state.created_at.isoformat(),
        updated_at=state.updated_at.isoformat(),
    )
