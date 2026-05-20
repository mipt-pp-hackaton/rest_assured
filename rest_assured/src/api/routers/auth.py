from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from rest_assured.src.api.dependencies import AuthServiceDep
from rest_assured.src.models.users import User
from rest_assured.src.schemas.auth import Token
from rest_assured.src.services.auth.dependencies import get_current_user
from rest_assured.src.services.auth.jwt import create_access_token

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=Token)
async def login(
    auth: AuthServiceDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    user = await auth.authenticate(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.email))


@auth_router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return {"email": current_user.email, "is_admin": current_user.is_admin}
