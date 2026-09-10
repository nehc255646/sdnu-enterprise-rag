"""FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat import auth, chat, health, llm, sessions
from app.core.config import get_settings
from app.core.db import init_db
from app.core.security import assert_jwt_secret
from app.ingest.routes import router as ingest_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    assert_jwt_secret()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    if settings.qdrant_path:
        Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("DB initialized")
    if settings.embedding_provider == "ollama":
        try:
            r = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2.0)
            if r.status_code >= 400:
                logger.warning("Ollama probe status=%s at %s", r.status_code, settings.ollama_base_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Ollama unreachable at %s (%s); bind 0.0.0.0:11434 for Docker",
                settings.ollama_base_url,
                exc,
            )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="山师大知识库问答",
        version="0.1.0",
        description=(
            "Document ingest, tenant-scoped retrieval, JWT auth, sessions, "
            "and LangChain LCEL RAG with SSE citations. "
            "Protected routes require Authorization Bearer and X-Tenant-Id."
        ),
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(ingest_router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(sessions.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(llm.router, prefix=prefix)

    @app.get("/")
    def root():
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": f"{prefix}/health",
        }

    return app


app = create_app()
