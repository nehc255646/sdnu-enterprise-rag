"""Health checks for app + dependencies (graceful degrade)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine
from app.schemas.health import DependencyStatus, HealthResponse
from app.services.cache import get_redis

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

    # DB
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        deps.append(DependencyStatus(name="database", ok=True))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="database", ok=False, detail=str(exc)))

    # Redis
    try:
        client = get_redis()
        if client is None:
            deps.append(DependencyStatus(name="redis", ok=False, detail="unreachable"))
        else:
            client.ping()
            deps.append(DependencyStatus(name="redis", ok=True))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="redis", ok=False, detail=str(exc)))

    # Qdrant (optional when retrieval_backend=backend1)
    try:
        from qdrant_client import QdrantClient

        if settings.qdrant_path:
            qc = QdrantClient(path=settings.qdrant_path)
            qc.get_collections()
            deps.append(DependencyStatus(name="qdrant", ok=True))
        elif settings.qdrant_url:
            qc = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=2)
            qc.get_collections()
            deps.append(DependencyStatus(name="qdrant", ok=True))
        else:
            deps.append(DependencyStatus(name="qdrant", ok=False, detail="no QDRANT_URL/PATH"))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="qdrant", ok=False, detail=str(exc)))

    # backend1 retrieve (when configured)
    if (settings.retrieval_backend or "").lower() == "backend1":
        try:
            import httpx

            base = (settings.backend1_base_url or "").rstrip("/")
            r = httpx.get(f"{base}{settings.api_prefix}/health", timeout=2.0)
            deps.append(
                DependencyStatus(
                    name="backend1",
                    ok=r.status_code < 500,
                    detail=None if r.status_code < 500 else f"status={r.status_code}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            deps.append(DependencyStatus(name="backend1", ok=False, detail=str(exc)))

    # LLM config (empty key OK for local sk-no-auth)
    deps.append(
        DependencyStatus(
            name="llm_config",
            ok=True,
            detail=f"base={settings.openai_base_url} model={settings.openai_model}",
        )
    )

    db_ok = any(d.ok for d in deps if d.name == "database")
    if not db_ok:
        overall = "error"
    elif all(d.ok for d in deps):
        overall = "ok"
    else:
        overall = "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        dependencies=deps,
        embedding_provider=settings.embedding_provider,
        embedding_model=_embedding_model_label(settings),
        llm_base_url=settings.openai_base_url,
        llm_model=settings.openai_model,
        retrieval_backend=settings.retrieval_backend,
    )
