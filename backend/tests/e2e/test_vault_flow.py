
VAULT_PAYLOAD = {
    "name" :"e2e_vault",
    "url": "e2e_url.com",
    "encrypted":"encrypted_data",
    "iv": "unique_e2e_iv"
}


async def test_full_vault_flow(e2e_client):
    await e2e_client.post("/auth/register", json={
        "email": "vaultuser@test.com",
        "password": "VaultPass123!",
        "salt": "vaultsalt"
    })
    resp = await e2e_client.post("/auth/login", json={
        "email": "vaultuser@test.com",
        "password": "VaultPass123!"
    })
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    resp = await e2e_client.get("/vault/", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    resp = await e2e_client.post("/vault/", json=VAULT_PAYLOAD, headers=headers)
    assert resp.status_code == 200
    vault_id = resp.json()["id"]

    resp = await e2e_client.get("/vault/", headers=headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "e2e_vault"

    updated = {**VAULT_PAYLOAD, "name": "e2e_vault_updated"}
    resp = await e2e_client.put(f"/vault/{vault_id}", json=updated,headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "e2e_vault_updated"

    resp = await e2e_client.get("/vault/", headers=headers)
    assert resp.json()[0]["name"] == "e2e_vault_updated"

    resp = await e2e_client.delete(f"/vault/{vault_id}", headers=headers)
    assert resp.status_code == 200

    resp = await e2e_client.get("/vault/", headers=headers)
    assert resp.json() == []

