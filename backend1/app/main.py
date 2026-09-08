import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import httpx

from app.api.routes import router
from app.core.config import get_settings
from app.core.db import init_db
from app.core.security import assert_jwt_secret

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
    if settings.embedding_provider == "ollama":
        try:
            r = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2.0)
            if r.status_code >= 400:
                logger.warning("Ollama probe status=%s at %s", r.status_code, settings.ollama_base_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama unreachable at %s (%s); bind 0.0.0.0:11434 for Docker", settings.ollama_base_url, exc)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ingest & Retrieval API",
        version="0.1.0",
        description=(
            "Document ingest and tenant-scoped vector retrieval "
            "(LangChain + Qdrant + SQLAlchemy). Protected routes require "
            "`Authorization: Bearer` and `X-Tenant-Id`."
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
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
