import logging

from functools import lru_cache
from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from .models.common import UserInfo
from .internal.database import async_engine, database


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/auth/token')
InvalidCredentialsExc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def get_session():
    async with AsyncSession(async_engine) as session:
        yield session


@lru_cache
def get_logger():
    return logging.getLogger('password_manager')


async def get_current_user(session: 'SessionDep', token: str = Depends(oauth2_scheme)) -> UserInfo:
    if not token:
        raise InvalidCredentialsExc

    session_valid: bool = await database.sessions.check_session_validity(session, token)
    if not session_valid:
        raise InvalidCredentialsExc

    user_info: UserInfo = await database.sessions.get_token_info(session, token)
    return user_info


async def check_group_is_valid(
    session: 'SessionDep', user: 'UserAuthDep', 
    group_id: Annotated[uuid.UUID, Path()]
) -> str:
    group_exists: bool = await database.groups.check_group_exists(
        session, user.username, group_id
    )
    if not group_exists:
        raise HTTPException(status_code=400, detail="Provided group_id is invalid")

    return group_id


UserAuthDep = Annotated[UserInfo, Depends(get_current_user)]

LoggerDep = Annotated[logging.Logger, Depends(get_logger)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]

CheckGroupValidDep = Annotated[uuid.UUID, Depends(check_group_is_valid)]
