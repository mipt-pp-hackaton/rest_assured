from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from rest_assured.src.models.users import User
from rest_assured.src.repositories.database_session import get_session_dependency
from rest_assured.src.schemas.auth import RefreshRequest, TokenPair
from rest_assured.src.schemas.users import UserCreate, UserRead
from rest_assured.src.services.auth import AuthService
from rest_assured.src.services.auth.dependencies import (
    get_current_active_user,
    get_current_superuser,
)
from rest_assured.src.services.auth.jwt import create_access_token, create_refresh_token

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=TokenPair)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session_dependency),
) -> TokenPair:
    service = AuthService(session)
    user = await service.authenticate(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@auth_router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreate,
    _current: User = Depends(get_current_superuser),
    session: AsyncSession = Depends(get_session_dependency),
) -> UserRead:
    service = AuthService(session)
    user = await service.register(data)
    return UserRead.model_validate(user)


@auth_router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session_dependency),
) -> TokenPair:
    service = AuthService(session)
    return await service.refresh(body.refresh_token)


@auth_router.get("/me", response_model=UserRead)
async def me(current: User = Depends(get_current_active_user)) -> UserRead:
    return UserRead.model_validate(current)
