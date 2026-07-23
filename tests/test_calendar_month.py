"""Integration tests for the calendar month-summary endpoint (mini-calendar)."""
from datetime import date

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_month_summary_lists_pet_initial_on_dose_day(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "Барсик", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Витамин", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })

    res = await client.get(
        f"/api/v1/calendar/month/{today.year}/{today.month}", headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["year"] == today.year
    assert data["month"] == today.month

    day_entry = next(d for d in data["days"] if d["date"] == today.isoformat())
    own_entry = next(p for p in day_entry["pets"] if p["pet_id"] == pet_id)
    assert own_entry["initial"] == "Б"


@pytest.mark.asyncio
async def test_month_summary_combines_multiple_pets_on_same_day(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    today = date.today()

    pet1 = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "Рекс", "species": "собака"}
    )
    pet1_id = pet1.json()["id"]
    pet2 = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "Мурка", "species": "кошка"}
    )
    pet2_id = pet2.json()["id"]

    for pid in (pet1_id, pet2_id):
        await client.post("/api/v1/medications", headers=auth_headers, json={
            "pet_id": pid, "name": "Препарат", "dosage": "1мг",
            "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
        })

    res = await client.get(
        f"/api/v1/calendar/month/{today.year}/{today.month}", headers=auth_headers
    )
    day_entry = next(d for d in res.json()["days"] if d["date"] == today.isoformat())
    own_pets = {p["pet_id"]: p["initial"] for p in day_entry["pets"]}
    assert own_pets[pet1_id] == "Р"
    assert own_pets[pet2_id] == "М"


@pytest.mark.asyncio
async def test_month_summary_omits_days_without_doses(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_res = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "Пустышка", "species": "кот"}
    )
    pet_id = pet_res.json()["id"]
    today = date.today()

    await client.post("/api/v1/medications", headers=auth_headers, json={
        "pet_id": pet_id, "name": "Одноразовый", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })

    res = await client.get(
        f"/api/v1/calendar/month/{today.year}/{today.month}", headers=auth_headers
    )
    # This pet's single one-day course must show up only on `today`, nowhere else
    # in the month — regardless of what other tests' pets contributed to the response.
    dates_with_this_pet = {
        d["date"] for d in res.json()["days"] if any(p["pet_id"] == pet_id for p in d["pets"])
    }
    assert dates_with_this_pet == {today.isoformat()}


@pytest.mark.asyncio
async def test_month_summary_only_includes_own_pets(client: AsyncClient) -> None:
    today = date.today()

    r1 = await client.post("/api/v1/auth/register", json={
        "email": "month_owner@example.com", "username": "month_owner", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet1 = await client.post("/api/v1/pets", headers=h1, json={"name": "Свой", "species": "кот"})
    await client.post("/api/v1/medications", headers=h1, json={
        "pet_id": pet1.json()["id"], "name": "Х", "dosage": "1мг",
        "frequency_per_day": 1, "start_date": today.isoformat(), "end_date": today.isoformat(),
    })

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "month_other@example.com", "username": "month_other", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.get(f"/api/v1/calendar/month/{today.year}/{today.month}", headers=h2)
    assert res.status_code == 200
    assert res.json()["days"] == []


@pytest.mark.asyncio
async def test_month_summary_requires_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/calendar/month/2026/7")
    assert res.status_code == 403
