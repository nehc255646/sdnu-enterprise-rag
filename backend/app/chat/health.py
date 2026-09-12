"""Health checks for app + dependencies (graceful degrade)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.chat.schemas.health import DependencyStatus, HealthResponse
from app.core.cache import get_redis
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.rate_limit import rate_limit_status

router = APIRouter(tags=["health"])


def _embedding_model_label(settings) -> str:
    if settings.embedding_provider == "ollama":
        return settings.ollama_embedding_model or settings.embedding_model
    if settings.embedding_provider == "openai":
        return settings.openai_embedding_model
    return settings.embedding_model


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    deps: list[DependencyStatus] = []

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        deps.append(DependencyStatus(name="database", ok=True))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="database", ok=False, detail=str(exc)))

    try:
        client = get_redis()
        if client is None:
            deps.append(
                DependencyStatus(
                    name="redis",
                    ok=False,
                    detail="optional: unreachable",
                    optional=True,
                )
            )
        else:
            client.ping()
            deps.append(DependencyStatus(name="redis", ok=True, optional=True))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="redis", ok=False, detail=f"optional: {exc}", optional=True))

    rl = rate_limit_status()
    deps.append(
        DependencyStatus(
            name="rate_limit",
            ok=bool(rl.get("ok")),
            detail=f"enabled={rl.get('enabled')} backend={rl.get('backend')}"
            + (f" | {rl['detail']}" if rl.get("detail") else ""),
            optional=True,
        )
    )

    try:
        from app.ingest.qdrant_store import get_qdrant

        if settings.qdrant_path or (settings.qdrant_url or "").strip():
            get_qdrant().get_collections()
            deps.append(DependencyStatus(name="qdrant", ok=True))
        else:
            deps.append(DependencyStatus(name="qdrant", ok=False, detail="no QDRANT_URL/PATH"))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="qdrant", ok=False, detail=str(exc)))

    deps.append(DependencyStatus(name="llm_config", ok=True, detail="see GET /api/v1/llm/config"))

    db_ok = any(d.ok for d in deps if d.name == "database")
    required = [d for d in deps if not d.optional]
    if not db_ok:
        overall = "error"
    elif all(d.ok for d in required):
        overall = "ok"
    else:
        overall = "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        dependencies=deps,
        embedding_provider=settings.embedding_provider,
        embedding_model=_embedding_model_label(settings),
        retrieval_backend="local",
    )
