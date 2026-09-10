from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations_json: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    tenant_id: str
    user_id: str
    title: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SessionWithMessages(SessionOut):
    messages: list[MessageOut] = []
