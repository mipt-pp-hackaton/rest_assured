from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from rest_assured.src.services.auth.dependencies import get_current_user
from rest_assured.src.services.auth.jwt import create_access_token
from rest_assured.src.models.users import User
from rest_assured.src.schemas.auth import Token
from rest_assured.src.services.auth import authenticate_user

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = await authenticate_user(
        request.app.state.session_factory,
        form_data.username,
        form_data.password,
    )
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
