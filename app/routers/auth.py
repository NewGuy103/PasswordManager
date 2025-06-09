from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestFormStrict

from ..deps import UserAuthDep, LoggerDep, SessionDep
from ..models.auth import AccessTokenError, AccessTokenResponse, AccessTokenErrorCodes, UserInfoPublic
from ..internal.database import database

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post(
    '/token', 
    response_model=AccessTokenResponse,
    responses={
        400: {'model': AccessTokenError},
        401: {'model': AccessTokenError}
    }
)
async def token_login(
    form_data: Annotated[OAuth2PasswordRequestFormStrict, Depends()],
    logger: LoggerDep, session: SessionDep
):
    """OAuth2 token login."""
    if len(form_data.username) > 30:
        access_token_error = AccessTokenError(
            error=AccessTokenErrorCodes.invalid_request,
            error_description='Provided username is over 30 characters'
        )
        return JSONResponse(
            access_token_error.model_dump(),
            status_code=400
        )

    if len(form_data.password) > 128:
        access_token_error = AccessTokenError(
            error=AccessTokenErrorCodes.invalid_request,
            error_description='Provided password is over 128 characters'
        )
        return JSONResponse(
            access_token_error.model_dump(),
            status_code=400
        )

    expire_offset: timedelta = timedelta(days=15)
    expiry_date: datetime = datetime.now(timezone.utc) + expire_offset

    verified: bool | str = await database.users.verify_user(session, form_data.username, form_data.password)
    match verified:
        case True:
            pass
        case False:
            access_token_error = AccessTokenError(
                error=AccessTokenErrorCodes.invalid_client,
                error_description='Invalid login credentials'
            )
            return JSONResponse(
                access_token_error.model_dump(),
                status_code=401
            )
        case _:
            logger.error("Invalid data: %s", verified)
            raise HTTPException(status_code=500, detail="Internal Server Error")

    token: str = await database.sessions.create_session_token(session, form_data.username, expiry_date)
    logger.info("User '%s' logged in", form_data.username)

    return AccessTokenResponse(
        access_token=token,
        token_type='bearer',
        expires_in=int(expire_offset.total_seconds())
    )


@router.post('/revoke')
async def revoke_login_token(user: UserAuthDep, token: Annotated[str, Form()], session: SessionDep) -> None:
    """OAuth2 token revocation."""
    token_valid = await database.sessions.check_session_validity(session, token)
    if not token_valid:
        return
    
    token_info = await database.sessions.get_token_info(session, token)
    if token_info.username != user.username:
        return
    
    await database.sessions.revoke_session(session, token)
    return


@router.get('/test_auth')
async def auth_test(user: UserAuthDep) -> UserInfoPublic:
    """Tests OAuth2 authorization."""
    return {'username': user.username}
