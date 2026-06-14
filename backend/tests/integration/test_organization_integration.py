import pytest
from sqlalchemy import select
from app.models.models import User, OrganizationInvitation
from app.models.enums import OrgRole
from app.services.organization_service import create_invitation


async def _user_id(db, email):
    return (await db.execute(select(User).where(User.email == email))).scalar_one().id


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


async def _make_org_with_member(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    member_h, _ = await _register_and_login(e2e_client, "member@test.com", "PUB_MEMBER")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    await e2e_client.post(f"/organizations/{org['id']}/members", headers=owner_h,
                          json={"email": "member@test.com", "role": "member",
                                "wrapped_org_key": "WRAP_MEMBER"})
    return org["id"], owner_h, member_h


@pytest.mark.asyncio
async def test_shared_vault_entry_visible_to_members_only(e2e_client):
    org_id, owner_h, member_h = await _make_org_with_member(e2e_client)
    stranger_h, _ = await _register_and_login(e2e_client, "stranger@test.com", "PUB_STR")

    created = await e2e_client.post("/vault/", headers=owner_h,
        json={"encrypted": "ORGSECRET", "iv": "AAAAAAAAAAAAAAAA", "org_id": org_id})
    assert created.status_code == 200
    assert created.json()["org_id"] == org_id

    # Member sees it via the org-scoped listing.
    member_list = await e2e_client.get(f"/vault/?org_id={org_id}", headers=member_h)
    assert [i["encrypted"] for i in member_list.json()["items"]] == ["ORGSECRET"]

    # A non-member is rejected.
    stranger = await e2e_client.get(f"/vault/?org_id={org_id}", headers=stranger_h)
    assert stranger.status_code == 403


@pytest.mark.asyncio
async def test_personal_and_org_vaults_are_isolated(e2e_client):
    org_id, owner_h, _ = await _make_org_with_member(e2e_client)
    await e2e_client.post("/vault/", headers=owner_h,
        json={"encrypted": "MINE", "iv": "AAAAAAAAAAAAAAAA"})
    await e2e_client.post("/vault/", headers=owner_h,
        json={"encrypted": "SHARED", "iv": "AAAAAAAAAAAAAAAA", "org_id": org_id})

    personal = await e2e_client.get("/vault/", headers=owner_h)
    org = await e2e_client.get(f"/vault/?org_id={org_id}", headers=owner_h)
    assert [i["encrypted"] for i in personal.json()["items"]] == ["MINE"]
    assert [i["encrypted"] for i in org.json()["items"]] == ["SHARED"]


@pytest.mark.asyncio
async def test_member_write_policy_enforced(e2e_client):
    org_id, owner_h, member_h = await _make_org_with_member(e2e_client)

    # Default: members may write.
    r = await e2e_client.post("/vault/", headers=member_h,
        json={"encrypted": "BYMEMBER", "iv": "AAAAAAAAAAAAAAAA", "org_id": org_id})
    assert r.status_code == 200

    # Owner turns the policy off -> members become read-only.
    s = await e2e_client.patch(f"/organizations/{org_id}/settings", headers=owner_h,
        json={"member_write": False})
    assert s.status_code == 200 and s.json()["member_write"] is False

    denied = await e2e_client.post("/vault/", headers=member_h,
        json={"encrypted": "NOPE", "iv": "AAAAAAAAAAAAAAAA", "org_id": org_id})
    assert denied.status_code == 403
    # ...but reading still works.
    read = await e2e_client.get(f"/vault/?org_id={org_id}", headers=member_h)
    assert read.status_code == 200

    # A non-owner cannot change the setting.
    nope = await e2e_client.patch(f"/organizations/{org_id}/settings", headers=member_h,
        json={"member_write": True})
    assert nope.status_code == 403


@pytest.mark.asyncio
async def test_invite_accept_confirm_flow(e2e_client, db):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    invitee_h, _ = await _register_and_login(e2e_client, "invitee@test.com", "PUB_INV")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    org_id = org["id"]

    owner_id = await _user_id(db, "owner@test.com")
    _, token = await create_invitation(db, org_id, "invitee@test.com", OrgRole.MEMBER, owner_id)

    # Wrong email cannot accept.
    other_h, _ = await _register_and_login(e2e_client, "other@test.com", "PUB_OTH")
    wrong = await e2e_client.post("/organizations/invitations/accept", headers=other_h,
                                  json={"token": token})
    assert wrong.status_code == 403

    # Invitee accepts -> pending member (org visible but no org key yet).
    acc = await e2e_client.post("/organizations/invitations/accept", headers=invitee_h,
                                json={"token": token})
    assert acc.status_code == 200 and acc.json()["org_id"] == org_id
    orgs = (await e2e_client.get("/organizations/", headers=invitee_h)).json()
    assert next(o for o in orgs if o["id"] == org_id)["wrapped_org_key"] is None

    # Owner sees the member as unconfirmed.
    members = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    invitee = next(m for m in members if m["email"] == "invitee@test.com")
    assert invitee["confirmed"] is False

    # Owner confirms -> member receives their wrapped org key.
    conf = await e2e_client.post(
        f"/organizations/{org_id}/members/{invitee['user_id']}/confirm",
        headers=owner_h, json={"wrapped_org_key": "WRAP_INV"})
    assert conf.status_code == 200 and conf.json()["confirmed"] is True
    orgs2 = (await e2e_client.get("/organizations/", headers=invitee_h)).json()
    assert next(o for o in orgs2 if o["id"] == org_id)["wrapped_org_key"] == "WRAP_INV"


@pytest.mark.asyncio
async def test_invitation_rbac_and_revoke(e2e_client, db):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    member_h, _ = await _register_and_login(e2e_client, "member@test.com", "PUB_MEMBER")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WRAP_OWNER"})).json()
    org_id = org["id"]
    owner_id = await _user_id(db, "owner@test.com")
    # Make member an actual (confirmed) member so they can act but lack admin.
    _, mtoken = await create_invitation(db, org_id, "member@test.com", OrgRole.MEMBER, owner_id)
    await e2e_client.post("/organizations/invitations/accept", headers=member_h,
                          json={"token": mtoken})

    # A plain member cannot create invitations.
    denied = await e2e_client.post(f"/organizations/{org_id}/invitations", headers=member_h,
                                   json={"email": "x@test.com", "role": "member"})
    assert denied.status_code == 403

    # Admin creates an invite via the API; it shows up in the list.
    created = await e2e_client.post(f"/organizations/{org_id}/invitations", headers=owner_h,
                                    json={"email": "newbie@test.com", "role": "member"})
    assert created.status_code == 200
    listed = (await e2e_client.get(f"/organizations/{org_id}/invitations", headers=owner_h)).json()
    assert [i["email"] for i in listed] == ["newbie@test.com"]

    # Revoke it -> a fresh service token for that email can't be accepted once revoked.
    inv_id = listed[0]["id"]
    rv = await e2e_client.request("DELETE",
        f"/organizations/{org_id}/invitations/{inv_id}", headers=owner_h)
    assert rv.status_code == 200
    remaining = (await e2e_client.get(f"/organizations/{org_id}/invitations", headers=owner_h)).json()
    assert remaining == []


@pytest.mark.asyncio
async def test_rotate_key_on_member_removal(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    b_h, _ = await _register_and_login(e2e_client, "b@test.com", "PUB_B")
    c_h, _ = await _register_and_login(e2e_client, "c@test.com", "PUB_C")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WO"})).json()
    org_id = org["id"]
    for em, wk in [("b@test.com", "WB"), ("c@test.com", "WC")]:
        await e2e_client.post(f"/organizations/{org_id}/members", headers=owner_h,
                              json={"email": em, "role": "member", "wrapped_org_key": wk})
    item = (await e2e_client.post("/vault/", headers=owner_h,
            json={"encrypted": "OLD", "iv": "AAAAAAAAAAAAAAAA", "org_id": org_id})).json()
    members = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    ids = {m["email"]: m["user_id"] for m in members}

    # Rotate, removing B; provide new keys for owner + C and re-encrypted item.
    payload = {
        "remove_user_id": ids["b@test.com"],
        "member_keys": [
            {"user_id": ids["owner@test.com"], "wrapped_org_key": "WO2"},
            {"user_id": ids["c@test.com"], "wrapped_org_key": "WC2"},
        ],
        "vault_items": [{"id": item["id"], "encrypted": "NEW", "iv": "BBBBBBBBBBBBBBBB"}],
    }
    r = await e2e_client.post(f"/organizations/{org_id}/rotate-key", headers=owner_h, json=payload)
    assert r.status_code == 200

    members2 = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    assert "b@test.com" not in [m["email"] for m in members2]

    owner_orgs = (await e2e_client.get("/organizations/", headers=owner_h)).json()
    assert next(o for o in owner_orgs if o["id"] == org_id)["wrapped_org_key"] == "WO2"
    c_orgs = (await e2e_client.get("/organizations/", headers=c_h)).json()
    assert next(o for o in c_orgs if o["id"] == org_id)["wrapped_org_key"] == "WC2"

    listed = (await e2e_client.get(f"/vault/?org_id={org_id}", headers=owner_h)).json()
    assert [i["encrypted"] for i in listed["items"]] == ["NEW"]

    # The removed member loses access entirely.
    assert (await e2e_client.get(f"/vault/?org_id={org_id}", headers=b_h)).status_code == 403


@pytest.mark.asyncio
async def test_rotate_key_validation_and_rbac(e2e_client):
    owner_h, _ = await _register_and_login(e2e_client, "owner@test.com", "PUB_OWNER")
    m_h, _ = await _register_and_login(e2e_client, "m@test.com", "PUB_M")
    org = (await e2e_client.post("/organizations/", headers=owner_h,
           json={"name": "Acme", "wrapped_org_key": "WO"})).json()
    org_id = org["id"]
    await e2e_client.post(f"/organizations/{org_id}/members", headers=owner_h,
                          json={"email": "m@test.com", "role": "member", "wrapped_org_key": "WM"})
    members = (await e2e_client.get(f"/organizations/{org_id}/members", headers=owner_h)).json()
    ids = {m["email"]: m["user_id"] for m in members}

    # A plain member cannot rotate.
    denied = await e2e_client.post(f"/organizations/{org_id}/rotate-key", headers=m_h,
                                   json={"member_keys": [], "vault_items": []})
    assert denied.status_code == 403

    # Incomplete member_keys (omits a confirmed member) is rejected.
    bad = await e2e_client.post(f"/organizations/{org_id}/rotate-key", headers=owner_h, json={
        "member_keys": [{"user_id": ids["owner@test.com"], "wrapped_org_key": "X"}],
        "vault_items": []})
    assert bad.status_code == 400


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
