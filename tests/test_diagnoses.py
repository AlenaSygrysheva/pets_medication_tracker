"""Integration tests for the diagnoses endpoints."""
import pytest
from httpx import AsyncClient


async def _create_pet(client: AsyncClient, headers: dict[str, str], name: str = "Барсик") -> int:
    res = await client.post("/api/v1/pets", headers=headers, json={"name": name, "species": "кот"})
    id_: int = res.json()["id"]
    return id_


@pytest.mark.asyncio
async def test_create_diagnosis_unconfirmed(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ПитомецДиагноз1")
    res = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Отит",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Отит"
    assert data["confirmed_by_vet"] is False
    assert data["doctor_name"] is None


@pytest.mark.asyncio
async def test_create_confirmed_diagnosis_requires_doctor_name(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "ПитомецДиагноз2")
    res = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Артрит", "confirmed_by_vet": True,
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_confirmed_diagnosis_with_doctor_name(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "ПитомецДиагноз3")
    res = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Артрит", "confirmed_by_vet": True, "doctor_name": "Иванов И.И.",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["confirmed_by_vet"] is True
    assert data["doctor_name"] == "Иванов И.И."


@pytest.mark.asyncio
async def test_create_diagnosis_with_comments(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ПитомецДиагноз4")
    res = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Дерматит", "comments": "Обострение весной",
    })
    assert res.status_code == 201
    assert res.json()["comments"] == "Обострение весной"


@pytest.mark.asyncio
async def test_create_diagnosis_unknown_pet_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": 999999, "name": "Неизвестно",
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_diagnoses_filters_by_pet(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet1 = await _create_pet(client, auth_headers, "ФильтрДиагноз1")
    pet2 = await _create_pet(client, auth_headers, "ФильтрДиагноз2")
    await client.post("/api/v1/diagnoses", headers=auth_headers, json={"pet_id": pet1, "name": "Д1"})
    await client.post("/api/v1/diagnoses", headers=auth_headers, json={"pet_id": pet2, "name": "Д2"})

    res = await client.get(f"/api/v1/diagnoses?pet_id={pet1}", headers=auth_headers)
    assert res.status_code == 200
    assert all(d["pet_id"] == pet1 for d in res.json())
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_update_diagnosis_name(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ОбновлениеДиагноз")
    created = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Старое название",
    })
    diagnosis_id = created.json()["id"]

    res = await client.patch(f"/api/v1/diagnoses/{diagnosis_id}", headers=auth_headers, json={
        "name": "Новое название",
    })
    assert res.status_code == 200
    assert res.json()["name"] == "Новое название"


@pytest.mark.asyncio
async def test_update_to_confirmed_without_doctor_name_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "ОбновлениеВалидацияДиагноз")
    created = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Диагноз",
    })
    diagnosis_id = created.json()["id"]

    res = await client.patch(f"/api/v1/diagnoses/{diagnosis_id}", headers=auth_headers, json={
        "confirmed_by_vet": True,
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_update_to_confirmed_with_doctor_name_succeeds(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "ОбновлениеУспехДиагноз")
    created = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Диагноз",
    })
    diagnosis_id = created.json()["id"]

    res = await client.patch(f"/api/v1/diagnoses/{diagnosis_id}", headers=auth_headers, json={
        "confirmed_by_vet": True, "doctor_name": "Петров П.П.",
    })
    assert res.status_code == 200
    assert res.json()["confirmed_by_vet"] is True
    assert res.json()["doctor_name"] == "Петров П.П."


@pytest.mark.asyncio
async def test_delete_diagnosis(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "УдалениеДиагноз")
    created = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Диагноз",
    })
    diagnosis_id = created.json()["id"]

    res = await client.delete(f"/api/v1/diagnoses/{diagnosis_id}", headers=auth_headers)
    assert res.status_code == 204

    get_res = await client.get(f"/api/v1/diagnoses/{diagnosis_id}", headers=auth_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_diagnoses_deleted_when_pet_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "КаскадДиагноз")
    created = await client.post("/api/v1/diagnoses", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Диагноз",
    })
    diagnosis_id = created.json()["id"]

    del_res = await client.delete(f"/api/v1/pets/{pet_id}", headers=auth_headers)
    assert del_res.status_code in (200, 204)

    get_res = await client.get(f"/api/v1/diagnoses/{diagnosis_id}", headers=auth_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_diagnoses_are_scoped_per_owner(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "diag_owner1@example.com", "username": "diag_owner1", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet_id = await _create_pet(client, h1, "ЧужойПитомецДиагноз")
    created = await client.post("/api/v1/diagnoses", headers=h1, json={"pet_id": pet_id, "name": "Д"})
    diagnosis_id = created.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "diag_owner2@example.com", "username": "diag_owner2", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.get(f"/api/v1/diagnoses/{diagnosis_id}", headers=h2)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_diagnoses_require_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/diagnoses")
    assert res.status_code == 403
