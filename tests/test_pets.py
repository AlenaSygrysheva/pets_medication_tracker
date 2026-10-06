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


@pytest.mark.asyncio
async def test_reproductive_status_defaults_to_unknown(client, auth_headers):
    res = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "БезСтатуса", "species": "кошка",
    })
    assert res.status_code == 201
    assert res.json()["reproductive_status"] == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["intact", "sterilized", "unknown"])
async def test_create_pet_with_reproductive_status(client, auth_headers, status):
    res = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": f"Статус-{status}", "species": "собака", "reproductive_status": status,
    })
    assert res.status_code == 201
    assert res.json()["reproductive_status"] == status


@pytest.mark.asyncio
async def test_update_reproductive_status(client, auth_headers):
    created = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "СменаСтатуса", "species": "кошка", "reproductive_status": "intact",
    })
    pet_id = created.json()["id"]

    res = await client.patch(f"/api/v1/pets/{pet_id}", headers=auth_headers, json={
        "reproductive_status": "sterilized",
    })
    assert res.status_code == 200
    assert res.json()["reproductive_status"] == "sterilized"
    # Other edits leave it alone.
    res = await client.patch(f"/api/v1/pets/{pet_id}", headers=auth_headers, json={"notes": "x"})
    assert res.json()["reproductive_status"] == "sterilized"
    got = await client.get(f"/api/v1/pets/{pet_id}", headers=auth_headers)
    assert got.json()["reproductive_status"] == "sterilized"


@pytest.mark.asyncio
async def test_invalid_reproductive_status_rejected(client, auth_headers):
    res = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "ПлохойСтатус", "species": "кошка", "reproductive_status": "maybe",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_sex_defaults_to_unknown_and_can_be_set(client, auth_headers):
    created = await client.post("/api/v1/pets", headers=auth_headers, json={
        "name": "ПолПитомца", "species": "кошка",
    })
    assert created.json()["sex"] == "unknown"
    pet_id = created.json()["id"]

    res = await client.patch(f"/api/v1/pets/{pet_id}", headers=auth_headers, json={"sex": "female"})
    assert res.status_code == 200
    assert res.json()["sex"] == "female"

    bad = await client.patch(f"/api/v1/pets/{pet_id}", headers=auth_headers, json={"sex": "x"})
    assert bad.status_code == 422
