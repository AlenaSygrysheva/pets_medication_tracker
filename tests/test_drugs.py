"""Integration tests for the drugs catalog endpoints."""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_drug(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "Энроксил", "purpose": "антибиотик широкого спектра", "strength": "15 мг",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Энроксил"
    assert data["strength"] == "15 мг"
    assert data["purpose"] == "антибиотик широкого спектра"


@pytest.mark.asyncio
async def test_create_duplicate_name_and_strength_returns_409(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    payload = {"name": "Байтрил", "purpose": "антибиотик", "strength": "25 мг"}
    first = await client.post("/api/v1/drugs", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/drugs", headers=auth_headers, json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_same_name_different_strength_is_allowed(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """"Энроксил 15 мг" and "Энроксил 25 мг" must both be creatable."""
    res1 = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "Энроксил15и25", "purpose": "антибиотик", "strength": "15 мг",
    })
    res2 = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "Энроксил15и25", "purpose": "антибиотик", "strength": "25 мг",
    })
    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["id"] != res2.json()["id"]


@pytest.mark.asyncio
async def test_list_drugs_excludes_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "СписокУдаление", "purpose": "тест", "strength": "1 мг",
    })
    drug_id = created.json()["id"]

    await client.delete(f"/api/v1/drugs/{drug_id}", headers=auth_headers)

    res = await client.get("/api/v1/drugs", headers=auth_headers)
    assert res.status_code == 200
    assert all(d["id"] != drug_id for d in res.json())


@pytest.mark.asyncio
async def test_update_drug(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    created = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "ОбновляемыйПреп", "purpose": "старое описание", "strength": "5 мг",
    })
    drug_id = created.json()["id"]

    res = await client.patch(f"/api/v1/drugs/{drug_id}", headers=auth_headers, json={
        "purpose": "новое описание",
    })
    assert res.status_code == 200
    assert res.json()["purpose"] == "новое описание"
    assert res.json()["name"] == "ОбновляемыйПреп"


@pytest.mark.asyncio
async def test_update_to_existing_name_and_strength_returns_409(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "ПрепаратА", "purpose": "т", "strength": "1 мг",
    })
    b = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "ПрепаратБ", "purpose": "т", "strength": "1 мг",
    })
    drug_b_id = b.json()["id"]

    res = await client.patch(f"/api/v1/drugs/{drug_b_id}", headers=auth_headers, json={
        "name": "ПрепаратА",
    })
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_delete_drug_not_in_use_succeeds(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "НеиспользуемыйПреп", "purpose": "т", "strength": "1 мг",
    })
    drug_id = created.json()["id"]

    res = await client.delete(f"/api/v1/drugs/{drug_id}", headers=auth_headers)
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_drug_blocked_while_course_active(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    drug = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "АктивныйКурсПреп", "purpose": "т", "strength": "1 мг",
    })
    drug_id = drug.json()["id"]

    pet = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ПитомецАктив", "species": "кот"}
    )
    pet_id = pet.json()["id"]

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1 таблетка",
        "frequency_per_day": 1, "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=5)).isoformat(),
    })

    res = await client.delete(f"/api/v1/drugs/{drug_id}", headers=auth_headers)
    assert res.status_code == 409
    assert "активном курсе" in res.json()["detail"]


@pytest.mark.asyncio
async def test_delete_drug_allowed_after_course_cancelled(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    drug = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "ОтменённыйКурсПреп", "purpose": "т", "strength": "1 мг",
    })
    drug_id = drug.json()["id"]

    pet = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ПитомецОтмена", "species": "кот"}
    )
    pet_id = pet.json()["id"]

    med = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1 таблетка",
        "frequency_per_day": 1, "start_date": date.today().isoformat(),
        "end_date": (date.today() + timedelta(days=5)).isoformat(),
    })
    med_id = med.json()["id"]

    await client.post(f"/api/v1/medications/{med_id}/cancel", headers=auth_headers)

    res = await client.delete(f"/api/v1/drugs/{drug_id}", headers=auth_headers)
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_deleted_drug_dose_history_stays_in_calendar(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Deleting a drug from the catalog must not erase past doses from the calendar."""
    drug = await client.post("/api/v1/drugs", headers=auth_headers, json={
        "name": "ИсторияПреп", "purpose": "т", "strength": "1 мг",
    })
    drug_id = drug.json()["id"]

    pet = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ПитомецИстория", "species": "кот"}
    )
    pet_id = pet.json()["id"]
    today = date.today().isoformat()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1 таблетка",
        "frequency_per_day": 1, "start_date": today, "end_date": today,
    })

    cal_res = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)
    dose_id = cal_res.json()["doses"][0]["dose_id"]
    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "taken"})

    del_res = await client.delete(f"/api/v1/drugs/{drug_id}", headers=auth_headers)
    assert del_res.status_code == 204

    cal_after = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)
    doses_after = cal_after.json()["doses"]
    assert len(doses_after) == 1
    assert doses_after[0]["status"] == "taken"
    assert doses_after[0]["medication_name"] == "ИсторияПреп 1 мг"


@pytest.mark.asyncio
async def test_delete_drug_not_found_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.delete("/api/v1/drugs/999999", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_drugs_are_scoped_per_owner(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "drug_owner1@example.com", "username": "drug_owner1", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    created = await client.post("/api/v1/drugs", headers=h1, json={
        "name": "ЧужойПреп", "purpose": "т", "strength": "1 мг",
    })
    drug_id = created.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "drug_owner2@example.com", "username": "drug_owner2", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    # Same name+strength must be creatable by a different owner (no cross-user conflict).
    res = await client.post("/api/v1/drugs", headers=h2, json={
        "name": "ЧужойПреп", "purpose": "т", "strength": "1 мг",
    })
    assert res.status_code == 201

    get_res = await client.get(f"/api/v1/drugs/{drug_id}", headers=h2)
    assert get_res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_drugs_require_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/drugs")
    assert res.status_code == 403
