from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.dependencies import SESSION_COOKIE_NAME, get_current_session, get_current_user
from app.api.schemas.auth import (
    AuthConfigOut,
    DisableAuthRequest,
    EnableAuthRequest,
    LoginRequest,
    LoginResponse,
    MfaVerifyRequest,
    SessionInfo,
)
from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.base import get_db
from app.db.models import AppSettings, User
from app.db.models import Session as SessionModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=settings.session_max_age_hours * 3600,
        path="/",
    )


@router.get("/config", response_model=AuthConfigOut)
async def auth_config(db: AsyncSession = Depends(get_db)):
    return AuthConfigOut(auth_method=await service.get_auth_method(db))


@router.post("/enable")
async def enable_auth(payload: EnableAuthRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one()
    if settings.auth_method == "basic":
        raise HTTPException(status.HTTP_409_CONFLICT, "Basic auth is already enabled")

    user = await service.get_user(db)
    if user is None:
        db.add(User(id=1, username=payload.username, password_hash=hash_password(payload.password)))
    # else: a user row already exists from a previous Basic period - leave
    # its username/password untouched, the submitted credentials are only
    # used to create a brand new row.

    settings.auth_method = "basic"
    await service.invalidate_all_sessions(db)
    await db.commit()
    return {"ok": True}


@router.post("/disable")
async def disable_auth(
    payload: DisableAuthRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    settings = result.scalar_one()
    if settings.auth_method == "none":
        raise HTTPException(status.HTTP_409_CONFLICT, "Basic auth is not enabled")

    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Current password is incorrect")

    settings.auth_method = "none"
    await service.invalidate_all_sessions(db)
    await db.commit()
    return {"ok": True}


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        user = await service.authenticate(db, payload.username, payload.password)
    except service.AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    mfa_required = user.mfa_enabled
    token = await service.create_session(
        db,
        user,
        mfa_verified=not mfa_required,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, token)
    return LoginResponse(mfa_required=mfa_required)


@router.post("/mfa/verify")
async def verify_mfa(
    payload: MfaVerifyRequest,
    session: SessionModel = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    user = await service.get_user(db)
    if user is None or not service.verify_totp_code(user, payload.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid verification code")
    await service.mark_mfa_verified(db, session)
    return {"ok": True}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        await service.delete_session(db, token)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/session", response_model=SessionInfo)
async def session_info(user: User = Depends(get_current_user)):
    return SessionInfo(username=user.username, mfa_enabled=user.mfa_enabled)
