"""Integration tests for medications endpoints."""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_medication(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "Медтест", "species": "кошка"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today().isoformat()

    res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Витамин C", "dosage": "100мг",
        "frequency_per_day": 2, "start_date": today,
        "end_date": (date.today() + timedelta(days=7)).isoformat(),
    })

    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Витамин C"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_medications(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "МедЛист", "species": "собака"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today().isoformat()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Лекарство А", "dosage": "5мл",
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

    res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Тест", "dosage": "1мг",
        "frequency_per_day": 30, "start_date": date.today().isoformat(),
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_cancel_medication_deactivates_and_returns_200(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ОтменаТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today().isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Курс", "dosage": "10мг",
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

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Омега-3", "dosage": "500мг",
        "frequency_per_day": 1, "start_date": date.today().isoformat(),
    })
    med_id = med_res.json()["id"]

    res = await client.get(f"/api/v1/medications/{med_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Омега-3"


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
    today = date.today().isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Удаляемый", "dosage": "1мг",
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
    today = date.today().isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "СПамять", "dosage": "1мг",
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
    today = date.today()
    end = today + timedelta(days=4)

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "ДлинныйКурс", "dosage": "5мг",
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
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "КурсСегодня", "dosage": "5мг",
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
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "СтатКурс", "dosage": "5мг",
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
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "АктивКурс", "dosage": "5мг",
        "frequency_per_day": 1, "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=10)).isoformat(),
    })
    med_id = med_res.json()["id"]

    stats_res = await client.get(f"/api/v1/medications/pet/{pet_id}/stats", headers=auth_headers)
    assert stats_res.status_code == 200
    assert all(s["medication_id"] != med_id for s in stats_res.json())
