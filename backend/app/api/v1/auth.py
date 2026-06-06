import httpx
import os
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일이 이미 가입되어 있습니다.",
        )

    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        available_hours={"weekday": 2, "weekend": 4},
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login")
async def login(response: Response, user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,  # Set to True in production (HTTPS)
    )

    return {"message": "로그인 성공", "user_id": user.id}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "로그아웃 성공"}


@router.get("/google")
async def login_google():
    """Redirect to Google OAuth login page."""
    # Use offline access to get a refresh token if needed, but not strictly required here
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "response_type=code&"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "scope=openid%20email%20profile&"
        "access_type=offline"
    )
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def auth_google_callback(code: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback and exchange code for access token."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        # Stub mode if credentials are not set
        email = "test.google@hierardo.app"
    else:
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response_data = response.json()
            if "error" in response_data:
                raise HTTPException(status_code=400, detail=response_data.get("error_description", "Failed to authenticate with Google"))
            
            access_token = response_data["access_token"]
            
            # Get user info
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            user_info_response = await client.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
            user_info = user_info_response.json()
            email = user_info.get("email")
            
            if not email:
                raise HTTPException(status_code=400, detail="Google authentication failed to provide an email")

    # DB 연동 로직
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # 자동 가입
        user = User(
            email=email,
            hashed_password="", # 소셜 가입은 비밀번호가 없음
            available_hours={"weekday": 2, "weekend": 4},
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # JWT 토큰 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    app_access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )

    # 쿠키 굽기 및 프론트엔드로 리다이렉트
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    response = RedirectResponse(url=frontend_url)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {app_access_token}",
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
