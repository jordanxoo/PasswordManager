
async def test_full_auth_flow(e2e_client):
    
    response = await e2e_client.post("/auth/register",json ={
        "email":"e2e@test.com",
        "password":"e2epass",
        "salt":"e2esalt"
    })
    assert response.status_code == 200

    response_l = await e2e_client.post("/auth/login",json = {
        "email":"e2e@test.com",
        "password":"e2epass"
    })

    assert response_l.status_code == 200

    access_token = response_l.json()["access_token"]
    headers = {"Authorization" : f"Bearer {access_token}"}

    response = await e2e_client.get("/vault/",headers=headers)
    assert response.status_code == 200

    response = await e2e_client.post("/auth/logout",headers=headers)
    assert response.status_code == 200

    response = await e2e_client.get("/vault/",headers=headers)
    assert response.status_code == 401


