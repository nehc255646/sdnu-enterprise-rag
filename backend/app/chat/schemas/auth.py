from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


def _password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("password must be at most 72 bytes")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    tenant_id: str | None = Field(
        default=None,
        description="Optional; defaults to a new UUID tenant for the user",
        min_length=1,
        max_length=64,
    )

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, value: str) -> str:
        return _password_bytes(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)
    tenant_id: str = Field(..., min_length=1, max_length=64)

    @field_validator("password")
    @classmethod
    def password_byte_limit(cls, value: str) -> str:
        return _password_bytes(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str


class UserOut(BaseModel):
    id: str
    email: str
    tenant_id: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
