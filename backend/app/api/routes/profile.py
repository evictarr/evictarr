import base64
from io import BytesIO

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.dependencies import get_current_user
from app.api.schemas.auth import (
    ChangePasswordRequest,
    MfaDisableRequest,
    MfaEnrollConfirmRequest,
    MfaEnrollResponse,
)
from app.db.base import get_db
from app.db.models import User

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.change_password(db, user, payload.current_password, payload.new_password)
    except service.AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return {"ok": True}


@router.post("/mfa/enroll", response_model=MfaEnrollResponse)
async def enroll_mfa(user: User = Depends(get_current_user)):
    secret, uri = await service.start_mfa_enrollment(user)
    img = qrcode.make(uri)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()
    return MfaEnrollResponse(secret=secret, otpauth_uri=uri, qr_png_base64=qr_b64)


@router.post("/mfa/enroll/confirm")
async def confirm_mfa(
    payload: MfaEnrollConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.confirm_mfa_enrollment(db, user, payload.secret, payload.code)
    except service.AuthError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"ok": True}


@router.post("/mfa/disable")
async def disable_mfa(
    payload: MfaDisableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.disable_mfa(db, user, payload.current_password, payload.code)
    except service.AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return {"ok": True}
