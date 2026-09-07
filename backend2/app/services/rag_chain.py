"""LangChain LCEL RAG: retrieve -> prompt -> LLM, with citations."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from app.core.config import get_settings
from app.schemas.chat import Citation
from app.services.retrieval import RetrievalClient, get_retrieval_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an enterprise internship/resume assistant.
Answer using ONLY the provided context snippets. If the context is insufficient, say so.
Cite sources by filename when relevant. Respond in the same language as the user question."""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Context:\n{context}\n\nQuestion: {question}",
        ),
    ]
)


def _format_docs(docs: list[dict[str, Any]]) -> str:
    if not docs:
        return "(no relevant documents found for this tenant)"
    parts = []
    for i, d in enumerate(docs, 1):
        name = d.get("filename") or d.get("document_id") or "unknown"
        parts.append(f"[{i}] ({name}) {d.get('text', '')}")
    return "\n\n".join(parts)


def hits_to_citations(hits: list[dict[str, Any]]) -> list[Citation]:
    return [
        Citation(
            document_id=h.get("document_id"),
            filename=h.get("filename"),
            chunk_index=h.get("chunk_index"),
            score=h.get("score"),
            text=(h.get("text") or "")[:500],
            point_id=h.get("point_id"),
            doc_type=h.get("doc_type"),
        )
        for h in hits
    ]


def _effective_api_key() -> str:
    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    return key if key else "sk-no-auth"


def get_llm():
    """ChatOpenAI against OpenAI-compat endpoint (Ollama /v1, Nehchat, etc.).

    Empty OPENAI_API_KEY → sk-no-auth for local proxies that ignore auth.
    Does not require the chat model to be pulled; callers must degrade on errors.
    """
    settings = get_settings()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=_effective_api_key(),
        base_url=settings.openai_base_url or None,
        temperature=0.2,
        streaming=True,
    )


def build_rag_chain(
    retrieval: RetrievalClient | None = None,
    tenant_id: str | None = None,
    top_k: int = 5,
    authorization: str | None = None,
):
    """Build LCEL chain. tenant_id is baked in via closure for safe retrieval."""
    if not tenant_id:
        raise ValueError("tenant_id required to build RAG chain")
    client = retrieval or get_retrieval_client()

    def retrieve_fn(question: str) -> list[dict[str, Any]]:
        return client.search(
            query=question,
            tenant_id=tenant_id,
            top_k=top_k,
            authorization=authorization,
        )

    try:
        llm = get_llm()
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM init failed: %s", exc)
        llm = None

    if llm is None:
        def fallback(inputs: dict[str, Any]) -> str:
            docs = retrieve_fn(inputs["question"])
            if not docs:
                return "No relevant documents found for your tenant. (LLM not configured)"
            citations = hits_to_citations(docs)
            lines = ["Retrieved context (LLM not configured — showing top snippets):"]
            for c in citations:
                lines.append(f"- {c.filename or c.document_id}: {c.text[:200]}")
            return "\n".join(lines)

        return RunnableLambda(fallback)

    chain = (
        {
            "docs": RunnableLambda(lambda x: retrieve_fn(x["question"])),
            "question": RunnablePassthrough() | RunnableLambda(lambda x: x["question"] if isinstance(x, dict) else x),
        }
        | RunnableLambda(
            lambda x: {
                "context": _format_docs(x["docs"]),
                "question": x["question"] if isinstance(x["question"], str) else x["question"].get("question", ""),
                "docs": x["docs"],
            }
        )
        | {
            "answer": PROMPT | llm | StrOutputParser(),
            "docs": RunnableLambda(lambda x: x["docs"]),
        }
    )
    return chain


def run_rag(
    *,
    question: str,
    tenant_id: str,
    top_k: int | None = None,
    retrieval: RetrievalClient | None = None,
    authorization: str | None = None,
) -> tuple[str, list[Citation]]:
    settings = get_settings()
    k = top_k or settings.rag_top_k
    client = retrieval or get_retrieval_client()
    hits = client.search(query=question, tenant_id=tenant_id, top_k=k, authorization=authorization)
    citations = hits_to_citations(hits)

    try:
        llm = get_llm()
        prompt_value = PROMPT.invoke({"context": _format_docs(hits), "question": question})
        answer = llm.invoke(prompt_value).content
        if not isinstance(answer, str):
            answer = str(answer)
        return answer, citations
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM invoke failed (%s); returning retrieval snippets", exc)
        if not hits:
            answer = f"No relevant documents found for your tenant. (LLM unavailable: {exc})"
        else:
            answer = (
                f"Retrieved context (LLM unavailable: {exc} — showing top snippets):\n"
                + "\n".join(f"- {c.filename or c.document_id}: {c.text[:200]}" for c in citations)
            )
        return answer, citations


async def stream_rag(
    *,
    question: str,
    tenant_id: str,
    top_k: int | None = None,
    retrieval: RetrievalClient | None = None,
    authorization: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield SSE-shaped event dicts: citation / token / error / done."""
    settings = get_settings()
    k = top_k or settings.rag_top_k
    client = retrieval or get_retrieval_client()

    try:
        hits = client.search(query=question, tenant_id=tenant_id, top_k=k, authorization=authorization)
    except Exception as exc:  # noqa: BLE001
        yield {"event": "error", "data": {"message": f"retrieval failed: {exc}"}}
        yield {"event": "done", "data": {}}
        return

    citations = hits_to_citations(hits)
    for c in citations:
        yield {"event": "citation", "data": c.model_dump()}

    try:
        llm = get_llm()
        prompt_value = PROMPT.invoke({"context": _format_docs(hits), "question": question})
        answer_parts: list[str] = []
        async for chunk in llm.astream(prompt_value):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if not token:
                continue
            if isinstance(token, list):
                token = "".join(str(t) for t in token)
            answer_parts.append(str(token))
            yield {"event": "token", "data": {"token": str(token)}}
        yield {"event": "done", "data": {"answer": "".join(answer_parts)}}
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM stream failed (%s); falling back to snippets", exc)
        if not hits:
            text = f"No relevant documents found for your tenant. (LLM unavailable: {exc})"
        else:
            text = (
                f"Retrieved context (LLM unavailable: {exc}):\n"
                + "\n".join(f"- {c.filename or c.document_id}: {c.text[:200]}" for c in citations)
            )
        for ch in text:
            yield {"event": "token", "data": {"token": ch}}
        yield {"event": "done", "data": {"answer": text}}


def citations_to_json(citations: list[Citation]) -> str:
    return json.dumps([c.model_dump() for c in citations], ensure_ascii=False)
