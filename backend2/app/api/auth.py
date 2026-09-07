"""Register / login → JWT."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    tenant_id = (body.tenant_id or str(uuid.uuid4())).strip()
    existing = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.email == body.email.lower())
        .one_or_none()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered for tenant")

    user = User(
        tenant_id=tenant_id,
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, extra={"email": user.email})
    return TokenResponse(access_token=token, tenant_id=user.tenant_id, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = (
        db.query(User)
        .filter(User.tenant_id == body.tenant_id.strip(), User.email == body.email.lower())
        .one_or_none()
    )
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    token = create_access_token(subject=user.id, tenant_id=user.tenant_id, extra={"email": user.email})
    return TokenResponse(access_token=token, tenant_id=user.tenant_id, user_id=user.id)


@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, tenant_id=user.tenant_id)
