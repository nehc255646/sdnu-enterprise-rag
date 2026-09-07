"""LLM config — Nehchat-style OpenAI-compat hot switch."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import CurrentUser, get_current_user
from app.schemas.llm import LLMConfigOut, LLMConfigUpdate
from app.services.llm_runtime import get_llm_config, set_llm_config

router = APIRouter(prefix="/llm", tags=["llm"])


def _to_out() -> LLMConfigOut:
    cfg = get_llm_config()
    return LLMConfigOut(
        base_url=cfg.base_url,
        model=cfg.model,
        api_key_set=bool((cfg.api_key or "").strip()),
    )


@router.get("/config", response_model=LLMConfigOut)
def read_llm_config(_user: CurrentUser = Depends(get_current_user)) -> LLMConfigOut:
    return _to_out()


@router.put("/config", response_model=LLMConfigOut)
def update_llm_config(
    body: LLMConfigUpdate,
    _user: CurrentUser = Depends(get_current_user),
) -> LLMConfigOut:
    try:
        set_llm_config(base_url=body.base_url, model=body.model, api_key=body.api_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_out()
