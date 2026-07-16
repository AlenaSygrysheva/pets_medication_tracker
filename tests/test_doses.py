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
