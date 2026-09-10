from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str | None = None
    filename: str | None = None
    chunk_index: int | None = None
    score: float | None = None
    text: str = ""
    point_id: str | None = None
    doc_type: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=16000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    session_id: str
    message_id: str | None = None
