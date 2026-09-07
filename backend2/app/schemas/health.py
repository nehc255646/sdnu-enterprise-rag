from pydantic import BaseModel


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    detail: str | None = None
    optional: bool = False


class HealthResponse(BaseModel):
    status: str
    service: str
    dependencies: list[DependencyStatus] = []
    # Config exposure (aligned with 后端1 / Nehchat-style ops)
    embedding_provider: str | None = None
    embedding_model: str | None = None
    llm_base_url: str | None = None
    llm_model: str | None = None
    retrieval_backend: str | None = None
