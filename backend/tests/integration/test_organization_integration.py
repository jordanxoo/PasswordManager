import pytest


async def _register_and_login(client, email, public_key):
    """Register a user with a keypair, then log in. Returns auth headers."""
    await client.post("/auth/register", json={
        "email": email,
        "password": "TestPass123!",
        "salt": f"salt-{email}",
        "public_key": public_key,
        "encrypted_private_key": f"enc-{email}",
        "private_key_iv": f"iv-{email}",
    })
    resp = await client.post("/auth/login", json={
        "email": email,
        "password": "TestPass123!",
    })
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body


@pytest.mark.asyncio
async def test_login_returns_wrapped_keypair(e2e_client):
    _, body = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    assert body["public_key"] == "PUB_OWNER"
    assert body["encrypted_private_key"] == "enc-owner@test.com"
    assert body["private_key_iv"] == "iv-owner@test.com"


@pytest.mark.asyncio
async def test_create_org_makes_caller_owner(e2e_client):
    headers, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    resp = await e2e_client.post("/organizations/", headers=headers,
                                 json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})
    assert resp.status_code == 200
    org = resp.json()
    assert org["name"] == "Acme"
    assert org["role"] == "owner"
    assert org["wrapped_org_key"] == "WRAP_OWNER"


@pytest.mark.asyncio
async def test_add_member_and_member_sees_their_wrapped_key(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    member_h, _ = await _register_and_login(e2e_client, "member@test.com", "PUB_MEMBER")

    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    org_id = org["id"]

    # Owner can read the member's public key to wrap the org key for them.
    pk = await e2e_client.get("/profile/public-key?email=member@test.com", headers=owner_h)
    assert pk.json()["public_key"] == "PUB_MEMBER"

    added = await e2e_client.post(f"/organizations/{org_id}/members", headers=owner_h,
                                  json={"email": "member@test.com", "role": "member",
                                        "wrapped_org_key": "WRAP_MEMBER"})
    assert added.status_code == 200

    # The member sees the org with THEIR wrapped copy of the org key.
    orgs = (await e2e_client.get("/organizations/", headers=member_h)).json()
    assert len(orgs) == 1
    assert orgs[0]["wrapped_org_key"] == "WRAP_MEMBER"
    assert orgs[0]["role"] == "member"


@pytest.mark.asyncio
async def test_member_cannot_manage(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    member_h, _ = await _register_and_login(e2e_client, "member@test.com", "PUB_MEMBER")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    org_id = org["id"]
    await e2e_client.post(f"/organizations/{org_id}/members", headers=owner_h,
                          json={"email": "member@test.com", "role": "member",
                                "wrapped_org_key": "WRAP_MEMBER"})
    members = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    member_id = next(m["user_id"] for m in members if m["email"] == "member@test.com")

    # A plain member may neither add members nor change roles.
    add = await e2e_client.post(f"/organizations/{org_id}/members", headers=member_h,
                                json={"email": "owner@test.com", "role": "member",
                                      "wrapped_org_key": "X"})
    assert add.status_code == 403
    role = await e2e_client.patch(f"/organizations/{org_id}/members/{member_id}",
                                  headers=member_h, json={"role": "admin"})
    assert role.status_code == 403


@pytest.mark.asyncio
async def test_owner_cannot_be_removed_but_member_can_leave(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    member_h, _ = await _register_and_login(e2e_client, "member@test.com", "PUB_MEMBER")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    org_id = org["id"]
    await e2e_client.post(f"/organizations/{org_id}/members", headers=owner_h,
                          json={"email": "member@test.com", "role": "member",
                                "wrapped_org_key": "WRAP_MEMBER"})
    members = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    by_email = {m["email"]: m["user_id"] for m in members}

    # The owner cannot be removed (would orphan the org).
    rm_owner = await e2e_client.request("DELETE",
        f"/organizations/{org_id}/members/{by_email['owner@test.com']}", headers=owner_h)
    assert rm_owner.status_code == 400

    # A member can remove themselves (leave).
    leave = await e2e_client.request("DELETE",
        f"/organizations/{org_id}/members/{by_email['member@test.com']}", headers=member_h)
    assert leave.status_code == 200
    remaining = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    assert [m["email"] for m in remaining] == ["owner@test.com"]


@pytest.mark.asyncio
async def test_add_member_without_keys_fails(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    # A user registered without a keypair (legacy) cannot be wrapped for.
    await e2e_client.post("/auth/register", json={
        "email": "legacy@test.com", "password": "TestPass123!", "salt": "salt-legacy"})
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    resp = await e2e_client.post(f"/organizations/{org['id']}/members", headers=owner_h,
                                 json={"email": "legacy@test.com", "role": "member",
                                       "wrapped_org_key": "X"})
    assert resp.status_code == 400
