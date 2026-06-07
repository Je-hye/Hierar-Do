import pytest
from httpx import AsyncClient
from app.models.user import User
from sqlalchemy import select

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, setup_db):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@hierardo.app", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@hierardo.app"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_existing_user(client: AsyncClient, setup_db):
    # Setup creates default@hierardo.app (with dummy password, but email exists)
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "default@hierardo.app", "password": "password123"}
    )
    assert response.status_code == 400
    assert "이미 가입되어 있습니다" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_user(client: AsyncClient, setup_db):
    # First register
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@hierardo.app", "password": "password123"}
    )
    
    # Then login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@hierardo.app", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "로그인 성공"
    # Check if access_token cookie is set
    assert "access_token" in response.cookies

@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, setup_db):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@hierardo.app", "password": "password123"}
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@hierardo.app", "password": "wrongpassword"}
    )
    assert response.status_code == 401
