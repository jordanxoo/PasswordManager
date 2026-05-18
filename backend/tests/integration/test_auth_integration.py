import pytest
from sqlalchemy import select
from app.models.models import User,RefreshToken


async def test_register_success(client):
    response = await client.post("/auth/register",json = {
        "email": "newuser@test.com",
        "password": "newuserpassword",
        "salt":"salt123"
    })

    assert response.status_code == 200
    assert response.json() == {"message":"registered successfully"}


async def test_register_duplicate_email(client):

    payload = {"email":"dup@test.com","password":"testpassword","salt":"salt123"}

    await client.post("/auth/register",json=payload)

    response = await client.post("/auth/register",json=payload)

    assert response.status_code == 400


async def test_login_success(client):
    await client.post("/auth/register",json = {
        "email": "login@test.com",
        "password": "loginpass",
        "salt":"salt123"
    })

    response = await client.post("/auth/login",json={
        "email": "login@test.com",
        "password": "loginpass"
    })

    assert response.status_code == 200
    assert "access_token" in response.json()

async def test_login_wrong_email(client):
    
    await client.post("/auth/register", json={
        "email":"mail@test.com",
        "password":"testpass",
        "salt":"salt123"
    })

    response = await client.post("/auth/login",json = {
        "email":"wrong@test.com",
        "password":"testpass"
    })

    assert response.status_code == 401

async def test_login_wrong_password(client):

    await client.post("/auth/register",json={
        "email":"test@test.com",
        "password":"testpass",
        "salt":"salt123"
    })

    response = await client.post("/auth/login",json={
        "email":"test@test.com",
        "password":"wrongpassword"
    })

    assert response.status_code == 401


async def test_logout_success(client,db):
    await client.post("/auth/register",json=
                      {
                          "email":"test@test.com",
                          "password":"testpass",
                          "salt":"salt123"
                      })
    
    login_resp = await client.post("/auth/login",json={
        "email":"test@test.com",
        "password":"testpass"
    })
    token = login_resp.json()["access_token"]
    refresh_token_cookie = login_resp.cookies.get("refresh_token")
    response = await client.post(
        "/auth/logout",
        headers = {"Authorization":f"Bearer {token}"},
        cookies = {"refresh_token":refresh_token_cookie}
    )

    assert response.status_code == 200

    tokens_in_db = await db.execute(select(RefreshToken))

    assert tokens_in_db.scalars().all() == []
