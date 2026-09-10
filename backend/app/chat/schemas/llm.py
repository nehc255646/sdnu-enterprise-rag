from pydantic import BaseModel, Field


class LLMConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=512, description="OpenAI-compatible base URL")
    api_key: str | None = Field(
        default=None,
        max_length=512,
        description="Optional; omit to keep current; empty string clears to sk-no-auth",
    )
    model: str = Field(..., min_length=1, max_length=192)


class LLMConfigOut(BaseModel):
    base_url: str
    model: str
    api_key_set: bool = Field(description="Whether a non-empty api_key is configured (value never returned)")
