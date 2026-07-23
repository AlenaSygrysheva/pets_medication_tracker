"""Integration tests for medications endpoints."""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _create_drug(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "Витамин C",
    strength: str = "100мг",
    purpose: str = "витамин",
) -> int:
    """Get-or-create: several tests reuse the same default name+strength under the
    one shared test user, and duplicates are rejected by the catalog on purpose."""
    res = await client.post("/api/v1/drugs", headers=headers, json={
        "name": name, "purpose": purpose, "strength": strength,
    })
    if res.status_code == 409:
        existing = await client.get("/api/v1/drugs", headers=headers)
        match = next(d for d in existing.json() if d["name"] == name and d["strength"] == strength)
        return int(match["id"])
    id_: int = res.json()["id"]
    return id_


@pytest.mark.asyncio
async def test_create_medication(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "Медтест", "species": "кошка"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="Витамин C", strength="100мг")
    today = date.today().isoformat()

    res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1 таблетка",
        "frequency_per_day": 2, "start_date": today,
        "end_date": (date.today() + timedelta(days=7)).isoformat(),
    })

    assert res.status_code == 201
    data = res.json()
    assert data["drug"]["name"] == "Витамин C"
    assert data["drug"]["strength"] == "100мг"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_medications(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "МедЛист", "species": "собака"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="Лекарство А", strength="5мл")
    today = date.today().isoformat()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "5мл",
        "frequency_per_day": 1, "start_date": today,
    })

    res = await client.get(f"/api/v1/medications/pet/{pet_id}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


@pytest.mark.asyncio
async def test_create_medication_invalid_frequency(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers,
        json={"name": "ЧастотаТест", "species": "кошка"},
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="Тест", strength="1мг")

    res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1мг",
        "frequency_per_day": 30, "start_date": date.today().isoformat(),
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_medication_unknown_drug_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "НетПреп", "species": "кошка"},
    )
    pet_id = pet_res.json()["id"]

    res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": 999999, "dosage": "1мг",
        "frequency_per_day": 1, "start_date": date.today().isoformat(),
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_medication_deactivates_and_returns_200(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ОтменаТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="Курс", strength="10мг")
    today = date.today().isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "10мг",
        "frequency_per_day": 1, "start_date": today,
        "end_date": (date.today() + timedelta(days=5)).isoformat(),
    })
    med_id = med_res.json()["id"]

    cancel_res = await client.post(
        f"/api/v1/medications/{med_id}/cancel", headers=auth_headers
    )

    assert cancel_res.status_code == 200
    assert cancel_res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_get_medication_by_id(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ПолучМед", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="Омега-3", strength="500мг")

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "500мг",
        "frequency_per_day": 1, "start_date": date.today().isoformat(),
    })
    med_id = med_res.json()["id"]

    res = await client.get(f"/api/v1/medications/{med_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["drug"]["name"] == "Омега-3"


@pytest.mark.asyncio
async def test_medication_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/medications/pet/1")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_delete_medication_removes_from_list(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "УдалТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="Удаляемый", strength="1мг")
    today = date.today().isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today,
    })
    med_id = med_res.json()["id"]

    del_res = await client.delete(f"/api/v1/medications/{med_id}", headers=auth_headers)
    assert del_res.status_code == 204

    list_res = await client.get(f"/api/v1/medications/pet/{pet_id}", headers=auth_headers)
    assert all(m["id"] != med_id for m in list_res.json())


@pytest.mark.asyncio
async def test_delete_medication_keeps_taken_dose_in_calendar(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "УдалКал", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="СПамять", strength="1мг")
    today = date.today().isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today,
    })
    med_id = med_res.json()["id"]

    cal_res = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)
    dose_id = cal_res.json()["doses"][0]["dose_id"]
    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "taken"})

    del_res = await client.delete(f"/api/v1/medications/{med_id}", headers=auth_headers)
    assert del_res.status_code == 204

    cal_after = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)
    doses_after = cal_after.json()["doses"]
    assert len(doses_after) == 1
    assert doses_after[0]["status"] == "taken"


@pytest.mark.asyncio
async def test_delete_medication_not_found_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.delete("/api/v1/medications/999999", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_cancel_medication_erases_future_pending_doses(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ОтменаБудущее", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="ДлинныйКурс", strength="5мг")
    today = date.today()
    end = today + timedelta(days=4)

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "5мг",
        "frequency_per_day": 1, "start_date": today.isoformat(),
        "end_date": end.isoformat(),
    })
    med_id = med_res.json()["id"]

    tomorrow = (today + timedelta(days=1)).isoformat()
    cal_before = await client.get(f"/api/v1/calendar/pet/{pet_id}/{tomorrow}", headers=auth_headers)
    assert cal_before.json()["total"] == 1

    cancel_res = await client.post(
        f"/api/v1/medications/{med_id}/cancel",
        headers=auth_headers,
        params={"as_of_date": today.isoformat()},
    )
    assert cancel_res.status_code == 200

    cal_after = await client.get(f"/api/v1/calendar/pet/{pet_id}/{tomorrow}", headers=auth_headers)
    assert cal_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_cancel_medication_marks_cancellation_day_dose_cancelled(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ОтменаСегодня", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="КурсСегодня", strength="5мг")
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "5мг",
        "frequency_per_day": 1, "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=3)).isoformat(),
    })
    med_id = med_res.json()["id"]

    await client.post(
        f"/api/v1/medications/{med_id}/cancel",
        headers=auth_headers,
        params={"as_of_date": today.isoformat()},
    )

    cal_after = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    doses_after = cal_after.json()["doses"]
    assert len(doses_after) == 1
    assert doses_after[0]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_stats_endpoint_returns_cancelled_course_summary(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "СтатТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="СтатКурс", strength="5мг")
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "5мг",
        "frequency_per_day": 1, "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=2)).isoformat(),
    })
    med_id = med_res.json()["id"]

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    dose_id = cal_res.json()["doses"][0]["dose_id"]
    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "taken"})

    await client.post(f"/api/v1/medications/{med_id}/cancel", headers=auth_headers)

    stats_res = await client.get(f"/api/v1/medications/pet/{pet_id}/stats", headers=auth_headers)
    assert stats_res.status_code == 200
    entries = [s for s in stats_res.json() if s["medication_id"] == med_id]
    assert len(entries) == 1
    assert entries[0]["taken"] == 1
    assert entries[0]["ended_reason"] == "cancelled"


@pytest.mark.asyncio
async def test_stats_endpoint_excludes_active_courses(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "СтатАктив", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    drug_id = await _create_drug(client, auth_headers, name="АктивКурс", strength="5мг")
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "5мг",
        "frequency_per_day": 1, "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=10)).isoformat(),
    })
    med_id = med_res.json()["id"]

    stats_res = await client.get(f"/api/v1/medications/pet/{pet_id}/stats", headers=auth_headers)
    assert stats_res.status_code == 200
    assert all(s["medication_id"] != med_id for s in stats_res.json())
