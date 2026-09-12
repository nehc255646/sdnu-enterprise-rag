"""Chat endpoints: non-stream JSON + SSE stream."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.chat.rag_chain import citations_to_json, run_rag, stream_rag
from app.chat.schemas.chat import ChatRequest, ChatResponse
from app.core.config import get_settings
from app.core.db import get_db, get_session_factory
from app.core.deps import CurrentUser, get_current_user
from app.core.rate_limit import enforce_chat_rate_limit
from app.models import ChatMessage, ChatSession, MessageRole

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)


def _get_owned_session(db: Session, session_id: str, user: CurrentUser) -> ChatSession:
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
    return session


_DEFAULT_TITLES = {None, "New chat", "新对话"}


def _touch_session(session: ChatSession, message: str) -> None:
    if session.title in _DEFAULT_TITLES and message.strip():
        session.title = message.strip()[:80]
    session.updated_at = datetime.now(timezone.utc)


def _recent_history(db: Session, session_id: str, tenant_id: str) -> list[dict[str, str]]:
    limit = max(0, int(get_settings().rag_history_turns))
    if limit == 0:
        return []
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.tenant_id == tenant_id)
        .order_by(ChatMessage.created_at.desc())
        .offset(1)
        .limit(limit)
        .all()
    )
    rows.reverse()
    return [{"role": m.role.value if hasattr(m.role, "value") else str(m.role), "content": m.content} for m in rows]


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    enforce_chat_rate_limit(user)
    session = _get_owned_session(db, body.session_id, user)

    user_msg = ChatMessage(
        tenant_id=user.tenant_id,
        session_id=session.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    db.commit()
    history = _recent_history(db, session.id, user.tenant_id)

    answer, citations = run_rag(
        question=body.message,
        tenant_id=user.tenant_id,
        top_k=body.top_k,
        history=history,
    )

    assistant_msg = ChatMessage(
        tenant_id=user.tenant_id,
        session_id=session.id,
        role=MessageRole.assistant,
        content=answer,
        citations_json=citations_to_json(citations),
    )
    db.add(assistant_msg)
    _touch_session(session, body.message)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(
        answer=answer,
        citations=citations,
        session_id=session.id,
        message_id=assistant_msg.id,
    )


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    enforce_chat_rate_limit(user)
    session = _get_owned_session(db, body.session_id, user)

    user_msg = ChatMessage(
        tenant_id=user.tenant_id,
        session_id=session.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    db.commit()
    history = _recent_history(db, session.id, user.tenant_id)
    session_id = session.id
    tenant_id = user.tenant_id
    user_text = body.message

    async def event_gen():
        answer_acc: list[str] = []
        citations_acc: list[dict] = []
        try:
            async for ev in stream_rag(
                question=user_text,
                tenant_id=tenant_id,
                top_k=body.top_k,
                history=history,
            ):
                etype = ev["event"]
                data = ev.get("data") or {}
                if etype == "token":
                    answer_acc.append(data.get("token", ""))
                elif etype == "citation":
                    citations_acc.append(data)
                elif etype == "done" and data.get("answer"):
                    if not answer_acc:
                        answer_acc.append(data["answer"])
                payload = json.dumps(data, ensure_ascii=False)
                yield f"event: {etype}\ndata: {payload}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("chat stream failed: %s", exc)
            err = json.dumps({"message": "chat failed"}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"
            yield "event: done\ndata: {}\n\n"
        finally:
            SessionLocal = get_session_factory()
            sdb = SessionLocal()
            try:
                sess = (
                    sdb.query(ChatSession)
                    .filter(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id)
                    .one_or_none()
                )
                final_answer = "".join(answer_acc)
                if sess is not None and final_answer:
                    sdb.add(
                        ChatMessage(
                            tenant_id=tenant_id,
                            session_id=session_id,
                            role=MessageRole.assistant,
                            content=final_answer,
                            citations_json=json.dumps(citations_acc, ensure_ascii=False),
                        )
                    )
                    _touch_session(sess, user_text)
                    sdb.commit()
            finally:
                sdb.close()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
