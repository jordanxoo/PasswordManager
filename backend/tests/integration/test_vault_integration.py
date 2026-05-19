import pytest
from sqlalchemy import select
from app.models.models import Vault


VAULT_PAYLOAD = {
    "name" : "test_name",
    "url": "test_url.com",
    "encrypted" : "test_encrypted",
    "iv": "test_iv123"
}

async def test_get_vaults_empty(client,auth_headers):
    response = await client.get("/vault/",headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []

async def test_create_vault(client,auth_headers):
    response = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_name"
    assert "id" in data

async def test_create_vault_persists_in_db(client,auth_headers,db):
    await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    result = await db.execute(select(Vault))
    vaults = result.scalars().all()
    assert len(vaults) == 1
    assert vaults[0].name == "test_name"

async def test_update_vault(client,auth_headers,db):
    create_response = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    vault_id = create_response.json()["id"]
    updated_vault = {**VAULT_PAYLOAD,"name":"updated_name"}
    response = await client.put(f"/vault/{vault_id}",json=updated_vault,headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "updated_name"

async def test_delete_vault(client,auth_headers,db):
    
    create_response = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)
    vault_id = create_response.json()["id"]

    response = await client.delete(f"/vault/{vault_id}",headers=auth_headers)
    assert response.status_code == 200

    result = await db.execute(select(Vault))
    vaults = result.scalars().all()

    assert len(vaults) == 0

async def test_delete_vault_forbidden(client,auth_headers,db):
    
    await client.post("/auth/register",json = {
        "email": "test@email.com",
        "password": "test_password",
        "salt": "test_salt"
    })

    login_b = await client.post("/auth/login",json={
        "email":"test@email.com",
        "password":"test_password"
    })

    headers_b = {"Authorization": f"Bearer {login_b.json()["access_token"]}"}
    create_response = await client.post("/vault/",headers=headers_b,json=VAULT_PAYLOAD)
    vault_id = create_response.json()["id"]

    response = await client.delete(f"/vault/{vault_id}",headers=auth_headers)
    assert response.status_code == 403

async def test_get_vaults_returns_only_own(client,db):

    await client.post("/auth/register",json = {
        "email":"clienta@test.com",
        "password":"clientapass",
        "salt":"clientasalt"
    })

    login_a = await client.post("/auth/login",json={
        "email":"clienta@test.com",
        "password":"clientapass"
    })
    headers_a = {"Authorization": f"Bearer {login_a.json()["access_token"]}"}
    await client.post("/auth/register",json={
        "email":"clientb@test.com",
        "password":"clientbpass",
        "salt":"clientbsalt"
    })

    login_b = await client.post("/auth/login",json={
        "email":"clientb@test.com",
        "password":"clientbpass"
    })
    headers_b = {"Authorization": f"Bearer {login_b.json()["access_token"]}"}

    await client.post("/vault/",json={**VAULT_PAYLOAD,"name":"Client A Vault"},headers=headers_a)
    await client.post("/vault/",json = {**VAULT_PAYLOAD, "name":"Client B Vault"},headers=headers_b)

    resp_a = await client.get("/vault/",headers=headers_a)
    resp_b = await client.get("/vault/",headers=headers_b)

    assert len(resp_a.json()) == 1
    assert resp_a.json()[0]["name"] == "Client A Vault"

    assert len(resp_b.json()) == 1
    assert resp_b.json()[0]["name"] == "Client B Vault"


