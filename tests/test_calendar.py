"""Integration tests for the calendar endpoint."""
from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_calendar_day_no_medications(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers,
        json={"name": "КалТест", "species": "кошка"},
    )
    pet_id = pet_res.json()["id"]
    today = date.today().isoformat()

    res = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["doses"] == []
    assert data["pet_id"] == pet_id


@pytest.mark.asyncio
async def test_calendar_day_with_twice_daily_medication(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers,
        json={"name": "КалТест2", "species": "собака"},
    )
    pet_id = pet_res.json()["id"]
    today = date.today().isoformat()
    end = (date.today() + timedelta(days=1)).isoformat()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Антибиотик", "dosage": "100мг",
        "frequency_per_day": 2, "start_date": today, "end_date": end,
    })

    res = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert data["pending"] == 2
    assert data["taken"] == 0
    assert data["missed"] == 0
    assert len(data["doses"]) == 2


@pytest.mark.asyncio
async def test_calendar_dose_slots_have_required_fields(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers,
        json={"name": "ФилдТест", "species": "кот"},
    )
    pet_id = pet_res.json()["id"]
    today = date.today().isoformat()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Витамин", "dosage": "50мг",
        "frequency_per_day": 1, "start_date": today,
    })

    res = await client.get(f"/api/v1/calendar/pet/{pet_id}/{today}", headers=auth_headers)
    slots = res.json()["doses"]

    assert len(slots) == 1
    slot = slots[0]
    assert "dose_id" in slot
    assert "medication_name" in slot
    assert "dosage" in slot
    assert "scheduled_at" in slot
    assert "status" in slot
    assert slot["status"] == "pending"


@pytest.mark.asyncio
async def test_calendar_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/calendar/pet/1/2026-07-08")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_calendar_other_user_pet_returns_404(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "cal_owner@example.com", "username": "cal_owner", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet = await client.post("/api/v1/pets", headers=h1, json={"name": "Чужой", "species": "кот"})
    pet_id = pet.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "cal_other@example.com", "username": "cal_other", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.get(f"/api/v1/calendar/pet/{pet_id}/2026-07-08", headers=h2)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_calendar_pet_not_found_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.get("/api/v1/calendar/pet/999999/2026-07-08", headers=auth_headers)
    assert res.status_code == 404
