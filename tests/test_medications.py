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
