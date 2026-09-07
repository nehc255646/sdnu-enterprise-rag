"""Health checks for app + dependencies (graceful degrade)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_engine
from app.schemas.health import DependencyStatus, HealthResponse
from app.services.cache import get_redis

router = APIRouter(tags=["health"])


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

    # Qdrant
    try:
        from qdrant_client import QdrantClient

        if settings.qdrant_path:
            qc = QdrantClient(path=settings.qdrant_path)
        elif settings.qdrant_url:
            qc = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=2)
        else:
            raise RuntimeError("no QDRANT_URL/PATH")
        qc.get_collections()
        deps.append(DependencyStatus(name="qdrant", ok=True))
    except Exception as exc:  # noqa: BLE001
        deps.append(DependencyStatus(name="qdrant", ok=False, detail=str(exc)))

    # LLM config present?
    deps.append(
        DependencyStatus(
            name="llm_config",
            ok=bool(settings.openai_api_key),
            detail=None if settings.openai_api_key else "OPENAI_API_KEY not set",
        )
    )

    db_ok = any(d.ok for d in deps if d.name == "database")
    if not db_ok:
        overall = "error"
    elif all(d.ok for d in deps):
        overall = "ok"
    else:
        overall = "degraded"
    return HealthResponse(status=overall, service=settings.app_name, dependencies=deps)
