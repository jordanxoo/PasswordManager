import pytest
from uuid import uuid4
from datetime import datetime,timedelta
from sqlalchemy import update
from app.models.models import ApiKey


VAULT_PAYLOAD = {
    "name": "test_vault",
    "url": "http://test.com",
    "encrypted": "encrypted_data",
    "iv": "dGVzdF9pdl9kYXRh"
}

async def test_create_key_success(client,auth_headers):

    response = await client.post("/api-keys/",json = {"name": "My Key","scope":"read"},headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Key"
    assert data["scope"] == "read"
    assert data["key"].startswith("pm_")
    assert len(data["key"]) == 67
    assert "key_hash" not in data    


async def test_list_keys_empty(client,auth_headers):
    response = await client.get("/api-keys/",headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

async def test_list_keys_return_two(client,auth_headers):
    await client.post("/api-keys/", json = {"name": "Key 1", "scope":"read"},headers=auth_headers)
    await client.post("/api-keys/",json = {"name":"Key 2","scope":"write"},headers=auth_headers)

    response = await client.get("/api-keys/",headers=auth_headers)

    assert response.status_code == 200
    assert len(response.json()) == 2

async def test_list_keys_no_plaintext(client,auth_headers):
    await client.post("/api-keys/", json = {"name":"key 1","scope":"read"},headers=auth_headers)

    result = await client.get("/api-keys/",headers=auth_headers)
    for item in result.json():
        assert "key" not in item
        assert "key_hash" not in item


async def test_revoke_key_success(client,auth_headers):
    create_r = await client.post("/api-keys/",json = {
        "name":"To Revoke", "scope": "read"
    }, headers= auth_headers)

    key_id = create_r.json()["id"]

    r = await client.delete(f"/api-keys/{key_id}",headers=auth_headers)
    assert r.status_code == 200

    list_r = await client.get("/api-keys/",headers=auth_headers)
    assert all(item["id"] != key_id for item in list_r.json())


async def test_revoke_key_not_found(client,auth_headers):
    r = await client.delete(f"/api-keys/{uuid4()}",headers=auth_headers)
    assert r.status_code == 404


async def test_revoke_other_users_key(client):
    await client.post("/auth/register", json={"email": "usera@test.com", "password":"PassA123!", "salt": "salta"})
    login_a = await client.post("/auth/login", json={"email": "usera@test.com","password": "PassA123!"})
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    await client.post("/auth/register", json={"email": "userb@test.com", "password":"PassB123!", "salt": "saltb"})
    login_b = await client.post("/auth/login", json={"email": "userb@test.com","password": "PassB123!"})
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    create_r = await client.post("/api-keys/", json={"name": "B Key", "scope": "read"},
headers=headers_b)
    b_key_id = create_r.json()["id"]

    r = await client.delete(f"/api-keys/{b_key_id}", headers=headers_a)
    assert r.status_code == 404



async def test_vault_read_with_read_key(client, auth_headers):
    create_r = await client.post("/api-keys/", json={"name": "Read Key", "scope":"read"}, headers=auth_headers)
    api_key = create_r.json()["key"]

    r = await client.get("/vault/", headers={"X-API-Key": api_key})
    assert r.status_code == 200


async def test_vault_write_blocked_with_read_key(client, auth_headers):
    create_r = await client.post("/api-keys/", json={"name": "Read Key", "scope":"read"}, headers=auth_headers)
    api_key = create_r.json()["key"]

    r = await client.post("/vault/", json=VAULT_PAYLOAD, headers={"X-API-Key": api_key})
    assert r.status_code == 403


async def test_vault_write_with_write_key(client, auth_headers):
    create_r = await client.post("/api-keys/", json={"name": "Write Key", "scope":"write"}, headers=auth_headers)
    api_key = create_r.json()["key"]

    r = await client.post("/vault/", json=VAULT_PAYLOAD, headers={"X-API-Key": api_key})
    assert r.status_code == 200


async def test_invalid_key_returns_401(client):
    r = await client.get("/vault/", headers={"X-API-Key": "pm_totallyinvalidkey"})
    assert r.status_code == 401


async def test_expired_key_returns_401(client, auth_headers, db):
    create_r = await client.post("/api-keys/", json={"name": "Expiring", "scope":"read"}, headers=auth_headers)
    api_key = create_r.json()["key"]
    key_id = create_r.json()["id"]

    await db.execute(
        update(ApiKey).where(ApiKey.id == key_id)
        .values(expires_at=datetime.now() - timedelta(days=1))
    )
    await db.commit()

    r = await client.get("/vault/", headers={"X-API-Key": api_key})
    assert r.status_code == 401

