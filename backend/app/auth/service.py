from datetime import datetime, timedelta, timezone

import pyotp
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.db.models import AppSettings
from app.db.models import Session as SessionModel
from app.db.models import User


class AuthError(Exception):
    pass


async def get_user(db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == 1))
    return result.scalar_one_or_none()


async def get_auth_method(db: AsyncSession) -> str:
    result = await db.execute(select(AppSettings.auth_method).where(AppSettings.id == 1))
    return result.scalar_one()


async def invalidate_all_sessions(db: AsyncSession) -> None:
    await db.execute(delete(SessionModel))


async def authenticate(db: AsyncSession, username: str, password: str) -> User:
    user = await get_user(db)
    if user is None or user.username != username or not verify_password(password, user.password_hash):
        raise AuthError("Invalid username or password")
    return user


async def create_session(
    db: AsyncSession, user: User, mfa_verified: bool, ip_address: str | None, user_agent: str | None
) -> str:
    token = generate_session_token()
    settings = get_settings()
    session = SessionModel(
        id=hash_session_token(token),
        user_id=user.id,
        mfa_verified=mfa_verified,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.session_max_age_hours),
    )
    db.add(session)
    await db.commit()
    return token


async def get_session(db: AsyncSession, token: str) -> SessionModel | None:
    token_hash = hash_session_token(token)
    result = await db.execute(select(SessionModel).where(SessionModel.id == token_hash))
    session = result.scalar_one_or_none()
    if session is None:
        return None
    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return session


async def mark_mfa_verified(db: AsyncSession, session: SessionModel) -> None:
    session.mfa_verified = True
    await db.commit()


async def delete_session(db: AsyncSession, token: str) -> None:
    token_hash = hash_session_token(token)
    await db.execute(delete(SessionModel).where(SessionModel.id == token_hash))
    await db.commit()


async def change_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    await db.commit()


async def start_mfa_enrollment(user: User) -> tuple[str, str]:
    """Returns (secret, otpauth_uri). Secret is NOT persisted until confirmed."""
    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.username, issuer_name="Evictarr")
    return secret, uri


async def confirm_mfa_enrollment(db: AsyncSession, user: User, secret: str, code: str) -> None:
    if not pyotp.totp.TOTP(secret).verify(code, valid_window=1):
        raise AuthError("Invalid verification code")
    user.totp_secret_encrypted = encrypt_secret(secret)
    user.mfa_enabled = True
    user.mfa_enrolled_at = datetime.now(timezone.utc)
    await db.commit()


def verify_totp_code(user: User, code: str) -> bool:
    if not user.totp_secret_encrypted:
        return False
    secret = decrypt_secret(user.totp_secret_encrypted)
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)


async def disable_mfa(db: AsyncSession, user: User, current_password: str, code: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect")
    if not verify_totp_code(user, code):
        raise AuthError("Invalid verification code")
    user.mfa_enabled = False
    user.totp_secret_encrypted = None
    user.mfa_enrolled_at = None
    await db.commit()
