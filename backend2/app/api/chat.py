"""Chat endpoints: non-stream JSON + SSE stream."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user
from app.core.rate_limit import enforce_chat_rate_limit
from app.db.models import ChatMessage, ChatSession, MessageRole
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_chain import citations_to_json, run_rag, stream_rag

router = APIRouter(prefix="/chat", tags=["chat"])
_bearer = HTTPBearer(auto_error=False)


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


def _auth_header(
    request: Request,
    creds: HTTPAuthorizationCredentials | None,
) -> str | None:
    """Prefer raw Authorization header; fall back to parsed Bearer credentials."""
    raw = request.headers.get("Authorization")
    if raw:
        return raw
    if creds and creds.credentials:
        return f"Bearer {creds.credentials}"
    return None


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> ChatResponse:
    enforce_chat_rate_limit(user)
    session = _get_owned_session(db, body.session_id, user)
    authorization = _auth_header(request, creds)

    user_msg = ChatMessage(
        tenant_id=user.tenant_id,
        session_id=session.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    db.commit()

    answer, citations = run_rag(
        question=body.message,
        tenant_id=user.tenant_id,
        top_k=body.top_k,
        authorization=authorization,
    )

    assistant_msg = ChatMessage(
        tenant_id=user.tenant_id,
        session_id=session.id,
        role=MessageRole.assistant,
        content=answer,
        citations_json=citations_to_json(citations),
    )
    db.add(assistant_msg)
    if session.title in (None, "New chat") and body.message.strip():
        session.title = body.message.strip()[:80]
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
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> StreamingResponse:
    enforce_chat_rate_limit(user)
    session = _get_owned_session(db, body.session_id, user)
    authorization = _auth_header(request, creds)

    user_msg = ChatMessage(
        tenant_id=user.tenant_id,
        session_id=session.id,
        role=MessageRole.user,
        content=body.message,
    )
    db.add(user_msg)
    db.commit()

    async def event_gen():
        answer_acc: list[str] = []
        citations_acc: list[dict] = []
        try:
            async for ev in stream_rag(
                question=body.message,
                tenant_id=user.tenant_id,
                top_k=body.top_k,
                authorization=authorization,
            ):
                etype = ev["event"]
                data = ev.get("data") or {}
                if etype == "token":
                    answer_acc.append(data.get("token", ""))
                elif etype == "citation":
                    citations_acc.append(data)
                elif etype == "done" and data.get("answer"):
                    # prefer full answer from done if present
                    if not answer_acc:
                        answer_acc.append(data["answer"])
                payload = json.dumps(data, ensure_ascii=False)
                yield f"event: {etype}\ndata: {payload}\n\n"
        except Exception as exc:  # noqa: BLE001
            err = json.dumps({"message": str(exc)}, ensure_ascii=False)
            yield f"event: error\ndata: {err}\n\n"
            yield "event: done\ndata: {}\n\n"
            return

        final_answer = "".join(answer_acc)
        assistant_msg = ChatMessage(
            tenant_id=user.tenant_id,
            session_id=session.id,
            role=MessageRole.assistant,
            content=final_answer,
            citations_json=json.dumps(citations_acc, ensure_ascii=False),
        )
        db.add(assistant_msg)
        if session.title in (None, "New chat") and body.message.strip():
            session.title = body.message.strip()[:80]
        db.commit()

    return StreamingResponse(event_gen(), media_type="text/event-stream")
