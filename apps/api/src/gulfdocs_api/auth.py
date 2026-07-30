from dataclasses import dataclass
from typing import Protocol

import anyio
import firebase_admin
from fastapi import HTTPException
from firebase_admin import auth

from .config import Settings


@dataclass(frozen=True, slots=True)
class VerifiedPrincipal:
    subject: str
    email: str | None = None
    display_name: str | None = None


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> VerifiedPrincipal: ...


class DevelopmentTokenVerifier:
    async def verify(self, token: str) -> VerifiedPrincipal:
        if not token.startswith("dev:") or len(token) <= 4 or len(token) > 204:
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        subject = token[4:]
        if not subject.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        return VerifiedPrincipal(
            subject=f"development:{subject}",
            email=f"{subject}@local.invalid",
            display_name=subject,
        )


class FirebaseTokenVerifier:
    def __init__(self) -> None:
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app()

    async def verify(self, token: str) -> VerifiedPrincipal:
        try:
            decoded = await anyio.to_thread.run_sync(auth.verify_id_token, token)
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid bearer token") from exc
        subject = decoded.get("uid") or decoded.get("sub")
        if not isinstance(subject, str) or not subject:
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        return VerifiedPrincipal(
            subject=f"firebase:{subject}",
            email=decoded.get("email") if isinstance(decoded.get("email"), str) else None,
            display_name=decoded.get("name") if isinstance(decoded.get("name"), str) else None,
        )


def build_token_verifier(settings: Settings) -> TokenVerifier:
    if settings.auth_provider == "development":
        if settings.app_env not in {"development", "test"}:
            raise RuntimeError("Development authentication is forbidden outside development/test")
        return DevelopmentTokenVerifier()
    if settings.auth_provider == "firebase":
        return FirebaseTokenVerifier()
    raise RuntimeError(f"Unsupported authentication provider: {settings.auth_provider}")
