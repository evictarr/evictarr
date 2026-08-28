"""Emergency access recovery commands, run inside the container:

    docker compose exec evictarr python -m app.cli reset-password --username admin --new-password ...
    docker compose exec evictarr python -m app.cli disable-mfa --username admin
    docker compose exec evictarr python -m app.cli disable-auth

These exist because Evictarr intentionally has no email-based password
recovery (see plan: self-service change-password only, no SMTP dependency
for auth).
"""

import argparse
import asyncio

from sqlalchemy import select

from app.auth.service import invalidate_all_sessions
from app.core.security import hash_password
from app.db.base import async_session_factory
from app.db.models import AppSettings, User


async def reset_password(username: str, new_password: str) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user exists yet - it will be created with username '{username}'.")
            user = User(id=1, username=username, password_hash=hash_password(new_password))
            db.add(user)
        else:
            user.username = username
            user.password_hash = hash_password(new_password)
        await db.commit()
    print("Password reset.")


async def disable_mfa(username: str) -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.id == 1, User.username == username))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with username '{username}'.")
            return
        user.mfa_enabled = False
        user.totp_secret_encrypted = None
        user.mfa_enrolled_at = None
        await db.commit()
    print("MFA disabled.")


async def disable_auth() -> None:
    async with async_session_factory() as db:
        result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
        settings = result.scalar_one_or_none()
        if settings is None or settings.auth_method == "none":
            print("Authentication is already set to 'none'.")
            return
        settings.auth_method = "none"
        await invalidate_all_sessions(db)
        await db.commit()
    print("Authentication method set to 'none'. The user's credentials are untouched.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    reset_parser = subparsers.add_parser("reset-password", help="Reset the login password (creates the user if none exists yet)")
    reset_parser.add_argument("--username", required=True)
    reset_parser.add_argument("--new-password", required=True)

    disable_parser = subparsers.add_parser("disable-mfa", help="Disable MFA for the user, e.g. if the authenticator device is lost")
    disable_parser.add_argument("--username", required=True)

    subparsers.add_parser(
        "disable-auth", help="Force the authentication method back to 'none' - turns off the login wall entirely"
    )

    args = parser.parse_args()

    if args.command == "reset-password":
        asyncio.run(reset_password(args.username, args.new_password))
    elif args.command == "disable-mfa":
        asyncio.run(disable_mfa(args.username))
    elif args.command == "disable-auth":
        asyncio.run(disable_auth())


if __name__ == "__main__":
    main()
