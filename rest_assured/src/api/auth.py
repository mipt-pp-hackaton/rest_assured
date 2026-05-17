from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select

from rest_assured.src.auth.jwt import create_access_token, get_current_user
from rest_assured.src.auth.passwords import verify_password
from rest_assured.src.models.user import User
from rest_assured.src.repositories.database_session import get_session
from rest_assured.src.schemas.auth import Token

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    session = get_session()
    try:
        result = await session.exec(select(User).where(User.email == form_data.username))
        user = result.one_or_none()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(data={"sub": user.email})
        return Token(access_token=access_token)
    finally:
        await session.close()


@auth_router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "is_admin": current_user.is_admin}
