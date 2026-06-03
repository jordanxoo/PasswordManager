import pytest
from sqlalchemy import select
from app.models.models import Vault
import base64,json

VAULT_PAYLOAD = {
    "encrypted" : "test_encrypted",
    "iv": "dGVzdF9pdl9kYXRh"
}

async def test_get_vaults_empty(client, auth_headers):
    response = await client.get("/vault/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []

async def test_create_vault(client,auth_headers):
    response = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["encrypted"] == "test_encrypted"
    assert "id" in data

async def test_create_vault_persists_in_db(client,auth_headers,db):
    await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    result = await db.execute(select(Vault))
    vaults = result.scalars().all()
    assert len(vaults) == 1
    assert vaults[0].encrypted == "test_encrypted"

async def test_update_vault(client,auth_headers,db):
    create_response = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    vault_id = create_response.json()["id"]
    updated_vault = {**VAULT_PAYLOAD,"encrypted":"updated_enc"}
    response = await client.put(f"/vault/{vault_id}",json=updated_vault,headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["encrypted"] == "updated_enc"

async def test_delete_vault(client,auth_headers,db):

    create_response = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)
    vault_id = create_response.json()["id"]

    response = await client.delete(f"/vault/{vault_id}",headers=auth_headers)
    assert response.status_code == 200

    result = await db.execute(select(Vault).where(Vault.is_deleted == False))
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

async def test_get_vaults_returns_only_own(client, db):
    await client.post("/auth/register", json={
        "email": "clienta@test.com",
        "password": "clientapass",
        "salt": "clientasalt"
    })
    login_a = await client.post("/auth/login", json={
        "email": "clienta@test.com",
        "password": "clientapass"
    })
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    await client.post("/auth/register", json={
        "email": "clientb@test.com",
        "password": "clientbpass",
        "salt": "clientbsalt"
    })
    login_b = await client.post("/auth/login", json={
        "email": "clientb@test.com",
        "password": "clientbpass"
    })
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    await client.post("/vault/", json={**VAULT_PAYLOAD, "encrypted": "ClientAEnc"},
headers=headers_a)
    await client.post("/vault/", json={**VAULT_PAYLOAD, "encrypted": "ClientBEnc"},
headers=headers_b)

    resp_a = await client.get("/vault/", headers=headers_a)
    resp_b = await client.get("/vault/", headers=headers_b)

    assert len(resp_a.json()["items"]) == 1
    assert resp_a.json()["items"][0]["encrypted"] == "ClientAEnc"

    assert len(resp_b.json()["items"]) == 1
    assert resp_b.json()["items"][0]["encrypted"] == "ClientBEnc"


async def test_create_vault_invalid_iv_too_short(client, auth_headers):
    payload = {**VAULT_PAYLOAD, "iv": "tooshort"}
    response = await client.post("/vault/", json=payload, headers=auth_headers)
    assert response.status_code == 422

async def test_create_vault_invalid_iv_not_base64(client, auth_headers):
    payload = {**VAULT_PAYLOAD, "iv": "!!!!invalid!!!!!"}
    response = await client.post("/vault/", json=payload, headers=auth_headers)
    assert response.status_code == 422

async def test_create_vault_valid_iv(client, auth_headers):
    payload = {**VAULT_PAYLOAD, "iv": "dGVzdF9pdl9kYXRh"}
    response = await client.post("/vault/", json=payload, headers=auth_headers)
    assert response.status_code == 200

async def test_import_exceeds_item_limit(client, auth_headers):
    import_payload = {
        "items": [{**VAULT_PAYLOAD} for _ in range(1001)]
    }
    response = await client.post("/vault/import", json=import_payload,
headers=auth_headers)
    assert response.status_code == 422

async def test_create_vault_exceeds_user_limit(client, auth_headers, db):
    from app.models.models import Vault
    from sqlalchemy import insert

    login_resp = await client.post("/auth/login", json={
        "email": "testuser@test.com",
        "password": "TestPass123!"
    })
    token = login_resp.json()["access_token"]
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (4 - len(payload_b64) % 4)
    user_id = json.loads(base64.b64decode(payload_b64))["sub"]


    await db.execute(insert(Vault).values([
        {
            "user_id": user_id,
            "encrypted": "enc",
            "iv": "dGVzdF9pdl9kYXRh"
        }
        for i in range(1000)
    ]))
    await db.commit()

    response = await client.post("/vault/", json=VAULT_PAYLOAD, headers=auth_headers)
    assert response.status_code == 400
    assert "limit" in response.json()["detail"].lower()

async def test_vault_history_created_on_update(client,auth_headers):
    create_resp = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)
    vault_id = create_resp.json()["id"]

    await client.put(f"/vault/{vault_id}",json={**VAULT_PAYLOAD,"encrypted":"v2"},headers=auth_headers)

    history_resp = await client.get(f"/vault/{vault_id}/history",headers=auth_headers)
    assert history_resp.status_code == 200
    assert len(history_resp.json()) == 1
    assert history_resp.json()[0]["encrypted"] == VAULT_PAYLOAD["encrypted"]


async def test_vault_history_keeps_all_versions(client,auth_headers):
    create_resp = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    vault_id = create_resp.json()["id"]

    for i in range(4):
        await client.put(f"/vault/{vault_id}", json={**VAULT_PAYLOAD,"encrypted":f"v{i}"},
                         headers=auth_headers)


    history_resp = await client.get(f"/vault/{vault_id}/history",headers=auth_headers)

    assert len(history_resp.json()) == 4


async def test_vault_restore(client,auth_headers):
    create_resp = await client.post("/vault/",json=VAULT_PAYLOAD,
                                    headers=auth_headers)
    vault_id = create_resp.json()["id"]

    await client.put(f"/vault/{vault_id}",json={**VAULT_PAYLOAD,"encrypted":"new_enc"},headers=auth_headers)

    history_resp = await client.get(f"/vault/{vault_id}/history",
    headers=auth_headers)
    history_id = history_resp.json()[0]["id"]

    restore_resp = await client.post(f"/vault/{vault_id}/restore/{history_id}",headers=auth_headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["encrypted"] == VAULT_PAYLOAD["encrypted"]


async def test_vault_history_requires_auth(client):
    response = await client.get("/vault/uuid/history")
    assert response.status_code == 401

async def test_soft_deleted_vault_not_in_list(client,auth_headers):
    create_resp = await client.post("/vault/",json=VAULT_PAYLOAD,headers=auth_headers)

    vault_id = create_resp.json()["id"]

    await client.delete(f"/vault/{vault_id}",headers=auth_headers)

    list_resp = await client.get("/vault/",headers=auth_headers)
    assert list_resp.json()["items"] == []
