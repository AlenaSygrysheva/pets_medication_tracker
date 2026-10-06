"""Tests for the pet PDF card: what data goes in (service) and the endpoint itself."""
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import update

from app.models.dose import Dose, DoseStatus
from app.models.pet import Pet
from app.schemas.pet_report import PetReportRequest
from app.services.pet_report_service import PetReportService
from tests.conftest import TestSessionLocal

PERIOD = {"date_from": "2025-03-01", "date_to": "2025-03-31"}


async def _register(client: AsyncClient, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/register", json={
        "email": f"{name}@example.com", "username": name, "password": "pass1234",
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _post(client: AsyncClient, h: dict[str, str], path: str, body: dict) -> dict:
    res = await client.post(f"/api/v1{path}", headers=h, json=body)
    assert res.status_code in (200, 201), res.text
    data: dict = res.json()
    return data


async def _course(
    client: AsyncClient, h: dict[str, str], pet_id: int, drug_id: int, start: str, end: str
) -> int:
    med = await _post(client, h, "/medications", {
        "pet_id": pet_id, "drug_id": drug_id, "dosage": "1 таблетка",
        "frequency_per_day": 2, "start_date": start, "end_date": end,
    })
    return int(med["id"])


async def _appointment(client: AsyncClient, h: dict[str, str], pet_id: int, clinic_id: int, at: str) -> int:
    a = await _post(client, h, "/vet-appointments", {
        "pet_id": pet_id, "clinic_id": clinic_id, "doctor_name": "Иванова",
        "appointment_at": at, "reminder_at": at, "comments": f"приём {at[:10]}",
    })
    return int(a["id"])


@pytest_asyncio.fixture
async def report_setup(client: AsyncClient) -> dict:
    h = await _register(client, f"report_owner_{uuid4().hex[:8]}")
    pet = await _post(client, h, "/pets", {
        "name": "Фрикуша", "species": "кошка", "weight_kg": 4.2,
        "sex": "female", "reproductive_status": "sterilized",
    })
    pet_id = pet["id"]
    drug = await _post(client, h, "/drugs", {"name": "Энроксил", "purpose": "антибиотик", "strength": "15 мг"})
    clinic = await _post(client, h, "/clinics", {
        "name": "Зоозащита", "address": "Коминтерна 29а", "phone": "78312343603",
    })

    completed = await _course(client, h, pet_id, drug["id"], "2025-03-10", "2025-03-12")
    async with TestSessionLocal() as s:
        await s.execute(update(Dose).where(Dose.medication_id == completed).values(status=DoseStatus.TAKEN))
        await s.commit()
    await _course(client, h, pet_id, drug["id"], "2025-01-01", "2025-01-05")  # before the period
    active = await _course(client, h, pet_id, drug["id"], "2025-03-20", "2025-04-10")
    cancelled = await _course(client, h, pet_id, drug["id"], "2025-02-25", "2025-03-05")
    res = await client.post(f"/api/v1/medications/{cancelled}/cancel?as_of_date=2025-03-02", headers=h)
    assert res.status_code == 200

    planned = await _appointment(client, h, pet_id, clinic["id"], "2025-03-15T10:00:00Z")
    done = await _appointment(client, h, pet_id, clinic["id"], "2025-03-16T09:30:00Z")
    await _post(client, h, f"/vet-appointments/{done}/complete", {})
    await _appointment(client, h, pet_id, clinic["id"], "2025-05-01T10:00:00Z")  # after the period

    d1 = await _post(client, h, "/diagnoses", {"pet_id": pet_id, "name": "Цистит"})
    await _post(client, h, "/diagnoses", {"pet_id": pet_id, "name": "Не в отчёт"})
    e1 = await _post(client, h, "/diary-entries", {"pet_id": pet_id, "text": "первая"})
    await _post(client, h, "/diary-entries", {"pet_id": pet_id, "text": "не в отчёт"})
    e3 = await _post(client, h, "/diary-entries", {"pet_id": pet_id, "text": "третья"})

    return {
        "h": h, "pet_id": pet_id, "diagnosis_ids": [d1["id"]], "diary_ids": [e3["id"], e1["id"]],
        "completed": completed, "active": active, "cancelled": cancelled, "planned": planned,
    }


async def _collect(pet_id: int, **req: object):  # type: ignore[no-untyped-def]
    async with TestSessionLocal() as s:
        owner_id = (await s.get(Pet, pet_id)).owner_id  # type: ignore[union-attr]
        return await PetReportService(s).collect(pet_id, owner_id, PetReportRequest(**{**PERIOD, **req}))


@pytest.mark.asyncio
async def test_courses_in_period_with_status_and_real_end(report_setup: dict) -> None:
    data = await _collect(report_setup["pet_id"])

    got = [(c.start.isoformat(), c.end.isoformat(), c.status) for c in data.courses]
    assert got == [
        ("2025-02-25", "2025-03-02", "cancelled"),  # ends on the cancel day, not end_date
        ("2025-03-10", "2025-03-12", "completed"),
        ("2025-03-20", "2025-04-10", "active"),
    ]  # the January course is outside the period
    assert data.courses[0].drug == "Энроксил 15 мг"
    assert data.courses[0].dosage == "1 таблетка"


@pytest.mark.asyncio
async def test_vet_visits_in_period_planned_and_completed(report_setup: dict) -> None:
    data = await _collect(report_setup["pet_id"])

    got = [(v.appointment_at.date(), v.completed) for v in data.vet_visits]
    assert got == [(date(2025, 3, 15), False), (date(2025, 3, 16), True)]
    visit = data.vet_visits[1]
    assert (visit.clinic_name, visit.clinic_address, visit.clinic_phone) == (
        "Зоозащита", "Коминтерна 29а", "78312343603",
    )
    assert (visit.doctor_name, visit.comments) == ("Иванова", "приём 2025-03-16")


@pytest.mark.asyncio
async def test_only_selected_diagnoses_and_diary_entries(report_setup: dict) -> None:
    data = await _collect(
        report_setup["pet_id"],
        diagnosis_ids=report_setup["diagnosis_ids"], diary_entry_ids=report_setup["diary_ids"],
    )
    assert [d.name for d in data.diagnoses] == ["Цистит"]
    assert [e.text for e in data.diary_entries] == ["первая", "третья"]  # chronological

    empty = await _collect(report_setup["pet_id"])
    assert empty.diagnoses == [] and empty.diary_entries == []


@pytest.mark.asyncio
async def test_endpoint_returns_pdf(client: AsyncClient, report_setup: dict) -> None:
    res = await client.post(
        f"/api/v1/pets/{report_setup['pet_id']}/report", headers=report_setup["h"],
        json={**PERIOD, "diagnosis_ids": report_setup["diagnosis_ids"],
              "diary_entry_ids": report_setup["diary_ids"], "time_format": "12", "tz_offset_minutes": -180},
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "filename*=UTF-8''" in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_reversed_period_rejected(client: AsyncClient, report_setup: dict) -> None:
    res = await client.post(
        f"/api/v1/pets/{report_setup['pet_id']}/report", headers=report_setup["h"],
        json={"date_from": "2025-04-01", "date_to": "2025-03-01"},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_foreign_ids_and_pets_are_404(client: AsyncClient, report_setup: dict) -> None:
    other = await _register(client, f"report_stranger_{uuid4().hex[:8]}")
    other_pet = await _post(client, other, "/pets", {"name": "Чужой", "species": "кот"})
    other_diag = await _post(client, other, "/diagnoses", {"pet_id": other_pet["id"], "name": "x"})
    url = f"/api/v1/pets/{report_setup['pet_id']}/report"

    res = await client.post(url, headers=report_setup["h"], json={**PERIOD, "diagnosis_ids": [other_diag["id"]]})
    assert res.status_code == 404
    res = await client.post(url, headers=report_setup["h"], json={**PERIOD, "diary_entry_ids": [999999]})
    assert res.status_code == 404
    res = await client.post(url, headers=other, json=PERIOD)
    assert res.status_code == 404
