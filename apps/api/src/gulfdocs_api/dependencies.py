from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from gulfdocs_document_intelligence.repositories import AuthIdentity
from gulfdocs_persistence.repositories import SqlAlchemyIdentityRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .auth import TokenVerifier


@dataclass(slots=True)
class AuthorizedContext:
    identity: AuthIdentity
    session: AsyncSession


async def get_authorized_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AsyncIterator[AuthorizedContext]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer authentication is required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer authentication is required")
    verifier: TokenVerifier = request.app.state.token_verifier
    principal = await verifier.verify(token)
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        try:
            identity = await SqlAlchemyIdentityRepository(session).get_or_create_identity(
                principal.subject,
                email=principal.email,
                display_name=principal.display_name,
            )
            yield AuthorizedContext(identity=identity, session=session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


Authorized = Annotated[AuthorizedContext, Depends(get_authorized_context)]
