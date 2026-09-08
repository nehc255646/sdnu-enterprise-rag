"""FastAPI entrypoint — chat & auth service (JWT, sessions, RAG orchestration)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, chat, health, llm, sessions
from app.core.config import get_settings
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.qdrant_path:
        Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
    try:
        init_db()
        logger.info("DB initialized")
    except Exception as exc:  # noqa: BLE001
        logger.error("DB init failed (service will start degraded): %s", exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="山师大知识库问答 — Chat & Auth",
        version="0.1.0",
        description=(
            "Chat & auth service: JWT auth + tenant isolation, "
            "chat sessions, LangChain LCEL orchestration, Redis cache, Qdrant retrieval "
            "on collection sdnu_chunks (ingest/upload via ingest service, default :8001). "
            "Protected routes require Authorization Bearer and X-Tenant-Id."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(sessions.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(llm.router, prefix=prefix)

    @app.get("/")
    def root():
        return {
            "service": settings.app_name,
            "role": "chat-auth",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": f"{prefix}/health",
        }

    return app


app = create_app()
