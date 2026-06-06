import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.db.init_db import init_db
from app.db.session import AsyncSessionLocal
from app.constants import MVP_USER_ID
from app.models.user import User
from app.api.v1.goals import router as goals_router
from app.api.v1.milestones import router as milestones_router
from app.api.v1.reschedule import router as reschedule_router
from app.api.v1.todos import router as todos_router
from app.api.v1.auth import router as auth_router


async def _ensure_default_user() -> None:
    """앱 시작 시 한 번만 실행 — 레이스 컨디션 방지"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == MVP_USER_ID))
        if result.scalar_one_or_none() is None:
            db.add(User(id=MVP_USER_ID, email="default@hierardo.app"))
            await db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _ensure_default_user()
    yield


app = FastAPI(title="Hierar-Do API", version="0.1.0", lifespan=lifespan)

# CORS: 환경변수 ALLOWED_ORIGINS (쉼표 구분) 또는 기본값 localhost:3000
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allow_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(auth_router, prefix="/api/v1")
app.include_router(goals_router, prefix="/api/v1")
app.include_router(todos_router, prefix="/api/v1")
app.include_router(milestones_router, prefix="/api/v1")
app.include_router(reschedule_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
