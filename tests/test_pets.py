import pytest


@pytest.mark.asyncio
async def test_create_pet(client, auth_headers):
    res = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "Барсик",
        "species": "кошка",
        "breed": "Мейн-кун",
        "weight_kg": 5.5,
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Барсик"
    assert data["species"] == "кошка"


@pytest.mark.asyncio
async def test_list_pets(client, auth_headers):
    res = await client.get("/api/v1/pets", headers=auth_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_update_pet(client, auth_headers):
    create_res = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "Шарик", "species": "собака"
    })
    pet_id = create_res.json()["id"]
    res = await client.patch(f"/api/v1/pets/{pet_id}", headers=auth_headers, json={"weight_kg": 10.0})
    assert res.status_code == 200
    assert res.json()["weight_kg"] == 10.0


@pytest.mark.asyncio
async def test_delete_pet(client, auth_headers):
    create_res = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "Тузик", "species": "собака"
    })
    pet_id = create_res.json()["id"]
    res = await client.delete(f"/api/v1/pets/{pet_id}", headers=auth_headers)
    assert res.status_code == 204
    get_res = await client.get(f"/api/v1/pets/{pet_id}", headers=auth_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_get_other_user_pet_forbidden(client):
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "user_a@example.com", "username": "user_a", "password": "pass1234"
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet = await client.post("/api/v1/pets", headers=h1, json={"name": "Мурка", "species": "кошка"})
    pet_id = pet.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "user_b@example.com", "username": "user_b", "password": "pass1234"
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    res = await client.get(f"/api/v1/pets/{pet_id}", headers=h2)
    assert res.status_code == 403
