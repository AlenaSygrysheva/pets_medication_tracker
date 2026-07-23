"""Integration tests for dose status updates and medication cancellation."""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


async def _create_pet_and_medication(
    client: AsyncClient, auth_headers: dict[str, str], freq: int = 1
) -> tuple[int, int, list[dict[str, object]]]:
    """Helper: create a pet + medication and return (pet_id, med_id, today's doses)."""
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers,
        json={"name": "ДозаТест", "species": "кошка"},
    )
    pet_id: int = pet_res.json()["id"]
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=2)).isoformat()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Витамин D", "dosage": "500МЕ",
        "frequency_per_day": freq, "start_date": today, "end_date": end,
    })
    med_id: int = med_res.json()["id"]

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers
    )
    doses: list[dict[str, object]] = cal_res.json()["doses"]
    return pet_id, med_id, doses


@pytest.mark.asyncio
async def test_mark_dose_taken(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    _, _, doses = await _create_pet_and_medication(client, auth_headers)
    dose_id = doses[0]["dose_id"]

    res = await client.patch(
        f"/api/v1/doses/{dose_id}",
        headers=auth_headers,
        json={"status": "taken"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "taken"
    assert res.json()["taken_at"] is not None


@pytest.mark.asyncio
async def test_mark_dose_skipped_with_notes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    _, _, doses = await _create_pet_and_medication(client, auth_headers)
    dose_id = doses[0]["dose_id"]

    res = await client.patch(
        f"/api/v1/doses/{dose_id}",
        headers=auth_headers,
        json={"status": "skipped", "notes": "Питомец отказался"},
    )

    assert res.status_code == 200
    assert res.json()["status"] == "skipped"
    assert res.json()["notes"] == "Питомец отказался"


@pytest.mark.asyncio
async def test_dose_not_found_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.patch(
        "/api/v1/doses/999999", headers=auth_headers, json={"status": "taken"}
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_dose_requires_auth(client: AsyncClient) -> None:
    res = await client.patch("/api/v1/doses/1", json={"status": "taken"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_dose_invalid_status_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    _, _, doses = await _create_pet_and_medication(client, auth_headers)
    dose_id = doses[0]["dose_id"]

    res = await client.patch(
        f"/api/v1/doses/{dose_id}",
        headers=auth_headers,
        json={"status": "flying"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_cancel_medication_deactivates_course(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    _, med_id, _ = await _create_pet_and_medication(client, auth_headers)

    res = await client.post(f"/api/v1/medications/{med_id}/cancel", headers=auth_headers)

    assert res.status_code == 200
    assert res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_cancel_medication_not_found_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.post("/api/v1/medications/999999/cancel", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_missed_dose_is_replaced_by_new_pending_dose(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """A missed dose must not shrink the course — a fresh pending dose should
    appear right after the last one, keeping the taken-dose target reachable."""
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ПродлениеТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "ОднаДоза", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })
    med_id = med_res.json()["id"]

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    dose_id = cal_res.json()["doses"][0]["dose_id"]

    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "missed"})

    tomorrow = (today + timedelta(days=1)).isoformat()
    cal_tomorrow = await client.get(f"/api/v1/calendar/pet/{pet_id}/{tomorrow}", headers=auth_headers)
    doses_tomorrow = cal_tomorrow.json()["doses"]
    assert len(doses_tomorrow) == 1
    assert doses_tomorrow[0]["status"] == "pending"
    assert doses_tomorrow[0]["medication_id"] == med_id


@pytest.mark.asyncio
async def test_skipped_dose_is_replaced_by_new_pending_dose(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "СкипТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "ОднаДоза2", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    dose_id = cal_res.json()["doses"][0]["dose_id"]

    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "skipped"})

    tomorrow = (today + timedelta(days=1)).isoformat()
    cal_tomorrow = await client.get(f"/api/v1/calendar/pet/{pet_id}/{tomorrow}", headers=auth_headers)
    assert len(cal_tomorrow.json()["doses"]) == 1


@pytest.mark.asyncio
async def test_taken_dose_is_not_replaced(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ТейкенТест", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "ОднаДоза3", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    dose_id = cal_res.json()["doses"][0]["dose_id"]

    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "taken"})

    tomorrow = (today + timedelta(days=1)).isoformat()
    cal_tomorrow = await client.get(f"/api/v1/calendar/pet/{pet_id}/{tomorrow}", headers=auth_headers)
    assert len(cal_tomorrow.json()["doses"]) == 0


@pytest.mark.asyncio
async def test_cancelled_course_does_not_get_extended(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ОтменаПродление", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()
    end = today + timedelta(days=3)

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "ДолгийКурс", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": end.isoformat(),
    })
    med_id = med_res.json()["id"]

    await client.post(
        f"/api/v1/medications/{med_id}/cancel",
        headers=auth_headers,
        params={"as_of_date": today.isoformat()},
    )

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    dose_id = cal_res.json()["doses"][0]["dose_id"]
    assert cal_res.json()["doses"][0]["status"] == "cancelled"

    res = await client.patch(
        f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "missed"}
    )
    assert res.status_code == 200

    day_after_end = (end + timedelta(days=1)).isoformat()
    cal_after = await client.get(f"/api/v1/calendar/pet/{pet_id}/{day_after_end}", headers=auth_headers)
    assert cal_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_stats_reflect_course_still_pending_after_miss_then_completes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "СтатПродление", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()

    med_res = await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "КурсСПродлением", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })
    med_id = med_res.json()["id"]

    cal_res = await client.get(
        f"/api/v1/calendar/pet/{pet_id}/{today.isoformat()}", headers=auth_headers
    )
    dose_id = cal_res.json()["doses"][0]["dose_id"]
    await client.patch(f"/api/v1/doses/{dose_id}", headers=auth_headers, json={"status": "missed"})

    stats_res = await client.get(f"/api/v1/medications/pet/{pet_id}/stats", headers=auth_headers)
    assert all(s["medication_id"] != med_id for s in stats_res.json())

    tomorrow = (today + timedelta(days=1)).isoformat()
    cal_tomorrow = await client.get(f"/api/v1/calendar/pet/{pet_id}/{tomorrow}", headers=auth_headers)
    replacement_id = cal_tomorrow.json()["doses"][0]["dose_id"]
    await client.patch(
        f"/api/v1/doses/{replacement_id}", headers=auth_headers, json={"status": "taken"}
    )

    stats_res2 = await client.get(f"/api/v1/medications/pet/{pet_id}/stats", headers=auth_headers)
    entries = [s for s in stats_res2.json() if s["medication_id"] == med_id]
    assert len(entries) == 1
    assert entries[0]["ended_reason"] == "completed"
    assert entries[0]["taken"] == 1
    assert entries[0]["missed"] == 1


@pytest.mark.asyncio
async def test_cancel_medication_wrong_user_returns_403(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "dose_owner@example.com", "username": "dose_owner", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet = await client.post("/api/v1/pets", headers=h1, json={"name": "Д", "species": "кот"})
    pet_id = pet.json()["id"]
    med = await client.post("/api/v1/medications", headers=h1, json={
        "pet_id": pet_id, "name": "X", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": date.today().isoformat(),
    })
    med_id = med.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "dose_intruder@example.com", "username": "dose_intruder", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.post(f"/api/v1/medications/{med_id}/cancel", headers=h2)
    assert res.status_code in (403, 404)
