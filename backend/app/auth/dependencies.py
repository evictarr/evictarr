from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import get_auth_method, get_session, get_user
from app.db.base import get_db
from app.db.models import Session as SessionModel
from app.db.models import User

SESSION_COOKIE_NAME = "evictarr_session"

# Returned by get_current_session/get_current_user when the app's
# authentication method is "none" - never persisted to the db, just a
# stand-in so every route depending on these keeps working against the same
# SessionModel/User return-type contract regardless of auth_method, with no
# per-router changes needed.
_ANONYMOUS_SESSION = SessionModel(id="", user_id=0, mfa_verified=True)
_ANONYMOUS_USER = User(id=1, username="anonymous", password_hash="", mfa_enabled=False)


async def get_current_session(
    evictarr_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> SessionModel:
    if await get_auth_method(db) == "none":
        return _ANONYMOUS_SESSION
    if evictarr_session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    session = await get_session(db, evictarr_session)
    if session is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return session


async def get_current_user(
    session: SessionModel = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    if session is _ANONYMOUS_SESSION:
        return _ANONYMOUS_USER
    if not session.mfa_verified:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA verification required")
    user = await get_user(db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    return user
