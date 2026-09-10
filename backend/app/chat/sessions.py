"""Chat session CRUD — tenant-scoped."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.chat.schemas.sessions import MessageOut, SessionCreate, SessionOut, SessionWithMessages
from app.core.db import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models import ChatMessage, ChatSession

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.tenant_id == user.tenant_id, ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    session = ChatSession(
        tenant_id=user.tenant_id,
        user_id=user.id,
        title=body.title or "New chat",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionWithMessages)
def get_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionWithMessages:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.tenant_id == user.tenant_id,
            ChatSession.user_id == user.id,
        )
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.tenant_id == user.tenant_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return SessionWithMessages(
        id=session.id,
        tenant_id=session.tenant_id,
        user_id=session.user_id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.tenant_id == user.tenant_id,
            ChatSession.user_id == user.id,
        )
        .one_or_none()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    db.delete(session)
    db.commit()
