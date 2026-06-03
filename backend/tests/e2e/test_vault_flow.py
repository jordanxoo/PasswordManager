
VAULT_PAYLOAD = {
    "encrypted":"e2e_enc",
    "iv": "dGVzdF9pdl9kYXRh"
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
    assert resp.json()["items"] == []


    resp = await e2e_client.post("/vault/", json=VAULT_PAYLOAD, headers=headers)
    assert resp.status_code == 200
    vault_id = resp.json()["id"]

    resp = await e2e_client.get("/vault/", headers=headers)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["items"][0]["encrypted"] == "e2e_enc"



    updated = {**VAULT_PAYLOAD, "encrypted": "e2e_enc_updated"}
    resp = await e2e_client.put(f"/vault/{vault_id}", json=updated, headers=headers)
    resp = await e2e_client.get("/vault/", headers=headers)
    assert resp.json()["items"][0]["encrypted"] == "e2e_enc_updated"

    resp = await e2e_client.delete(f"/vault/{vault_id}", headers=headers)
    resp = await e2e_client.get("/vault/", headers=headers)
    assert resp.json()["items"] == []
