"""Integration tests for the vet appointments endpoints."""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


async def _create_pet(client: AsyncClient, headers: dict[str, str], name: str = "Барсик") -> int:
    res = await client.post("/api/v1/pets", headers=headers, json={"name": name, "species": "кот"})
    id_: int = res.json()["id"]
    return id_


async def _create_clinic(client: AsyncClient, headers: dict[str, str], name: str = "ВетКлиника") -> int:
    res = await client.post("/api/v1/clinics", headers=headers, json={
        "name": name, "address": "ул. Ленина, 1", "phone": "79991234567",
    })
    id_: int = res.json()["id"]
    return id_


@pytest.mark.asyncio
async def test_create_vet_appointment(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers)
    clinic_id = await _create_clinic(client, auth_headers)
    appointment_at = datetime.now(UTC) + timedelta(days=1)
    reminder_at = appointment_at - timedelta(hours=1)

    res = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id, "doctor_name": "Иванов И.И.",
        "appointment_at": appointment_at.isoformat(), "reminder_at": reminder_at.isoformat(),
    })
    assert res.status_code == 201
    data = res.json()
    assert data["pet_id"] == pet_id
    assert data["clinic"]["id"] == clinic_id
    assert data["doctor_name"] == "Иванов И.И."


@pytest.mark.asyncio
async def test_doctor_name_is_optional(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "БезВрача")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаБезВрача")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    res = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    assert res.status_code == 201
    assert res.json()["doctor_name"] is None


@pytest.mark.asyncio
async def test_reminder_after_appointment_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "РеминдерПозже")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаРеминдер")
    appointment_at = datetime.now(UTC) + timedelta(days=1)
    reminder_at = appointment_at + timedelta(hours=1)

    res = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": reminder_at.isoformat(),
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reminder_equal_to_appointment_is_allowed(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "РеминдерРавен")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаРавен")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    res = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_create_with_unknown_clinic_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "НеизвестнаяКлиника")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    res = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": 999999,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_create_with_unknown_pet_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаБезПитомца")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    res = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": 999999, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_filters_by_pet(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet1 = await _create_pet(client, auth_headers, "ФильтрПитомец1")
    pet2 = await _create_pet(client, auth_headers, "ФильтрПитомец2")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаФильтр")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet1, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet2, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })

    res = await client.get(f"/api/v1/vet-appointments?pet_id={pet1}", headers=auth_headers)
    assert res.status_code == 200
    assert all(a["pet_id"] == pet1 for a in res.json())
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_update_appointment(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ОбновлениеПитомец")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаОбновление")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    created = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    appt_id = created.json()["id"]

    res = await client.patch(f"/api/v1/vet-appointments/{appt_id}", headers=auth_headers, json={
        "doctor_name": "Петров П.П.",
    })
    assert res.status_code == 200
    assert res.json()["doctor_name"] == "Петров П.П."


@pytest.mark.asyncio
async def test_update_reminder_after_appointment_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "ОбновлениеВалидация")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаВалидация")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    created = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    appt_id = created.json()["id"]

    res = await client.patch(f"/api/v1/vet-appointments/{appt_id}", headers=auth_headers, json={
        "reminder_at": (appointment_at + timedelta(hours=2)).isoformat(),
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_delete_appointment(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "УдалениеПитомец")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаУдаление")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    created = await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    appt_id = created.json()["id"]

    res = await client.delete(f"/api/v1/vet-appointments/{appt_id}", headers=auth_headers)
    assert res.status_code == 204

    get_res = await client.get(f"/api/v1/vet-appointments/{appt_id}", headers=auth_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_vet_appointments_are_scoped_per_owner(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "vet_owner1@example.com", "username": "vet_owner1", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet_id = await _create_pet(client, h1, "ЧужойПитомецВет")
    clinic_id = await _create_clinic(client, h1, "ЧужаяКлиникаВет")
    appointment_at = datetime.now(UTC) + timedelta(days=1)

    created = await client.post("/api/v1/vet-appointments", headers=h1, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
    })
    appt_id = created.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "vet_owner2@example.com", "username": "vet_owner2", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.get(f"/api/v1/vet-appointments/{appt_id}", headers=h2)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_vet_appointments_require_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/vet-appointments")
    assert res.status_code == 403


async def _create_appointment(
    client: AsyncClient, headers: dict[str, str], pet_id: int, clinic_id: int, **extra: str
) -> dict:
    appointment_at = datetime(2026, 10, 7, 13, 0, tzinfo=UTC)
    res = await client.post("/api/v1/vet-appointments", headers=headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at.isoformat(), "reminder_at": appointment_at.isoformat(),
        **extra,
    })
    assert res.status_code == 201
    data: dict = res.json()
    return data


@pytest.mark.asyncio
async def test_list_survives_legacy_clinic_phone(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Regression: a clinic saved before the digits-only phone rule used to make
    every response that embeds it fail with 500, so the pet's appointments list
    looked empty in the UI."""
    from sqlalchemy import update

    from app.models.clinic import Clinic
    from tests.conftest import TestSessionLocal

    pet_id = await _create_pet(client, auth_headers, "СтарыйТелефон")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаСтарыйТелефон")
    await _create_appointment(client, auth_headers, pet_id, clinic_id)
    async with TestSessionLocal() as session:
        await session.execute(
            update(Clinic).where(Clinic.id == clinic_id).values(phone="+7 (831) 234-36-03")
        )
        await session.commit()

    res = await client.get(f"/api/v1/vet-appointments?pet_id={pet_id}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["clinic"]["phone"] == "+7 (831) 234-36-03"


@pytest.mark.asyncio
async def test_complete_moves_appointment_to_history(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "ПриёмСостоялся")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаСостоялся")
    appt = await _create_appointment(
        client, auth_headers, pet_id, clinic_id, doctor_name="Петров", comments="Взять анализы"
    )

    res = await client.post(f"/api/v1/vet-appointments/{appt['id']}/complete", headers=auth_headers)
    assert res.status_code == 200
    visit = res.json()
    assert visit["pet_id"] == pet_id
    assert visit["clinic_name"] == "КлиникаСостоялся"
    assert visit["clinic_address"] == "ул. Ленина, 1"
    assert visit["clinic_phone"] == "79991234567"
    assert visit["doctor_name"] == "Петров"
    assert visit["comments"] == "Взять анализы"
    assert visit["appointment_at"].startswith("2026-10-07T13:00")

    # The appointment itself is gone: no longer listed and closed for editing.
    assert (await client.get(f"/api/v1/vet-appointments/{appt['id']}", headers=auth_headers)).status_code == 404
    listed = await client.get(f"/api/v1/vet-appointments?pet_id={pet_id}", headers=auth_headers)
    assert listed.json() == []
    patch_res = await client.patch(
        f"/api/v1/vet-appointments/{appt['id']}", headers=auth_headers, json={"comments": "x"}
    )
    assert patch_res.status_code == 404
    again = await client.post(f"/api/v1/vet-appointments/{appt['id']}/complete", headers=auth_headers)
    assert again.status_code == 404

    history = await client.get(f"/api/v1/vet-appointments/completed?pet_id={pet_id}", headers=auth_headers)
    assert history.status_code == 200
    assert [v["id"] for v in history.json()] == [visit["id"]]


@pytest.mark.asyncio
async def test_completed_visit_survives_clinic_deletion(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet_id = await _create_pet(client, auth_headers, "КлиникаУдаленаПосле")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаВременная")
    appt = await _create_appointment(client, auth_headers, pet_id, clinic_id)
    await client.post(f"/api/v1/vet-appointments/{appt['id']}/complete", headers=auth_headers)

    await client.delete(f"/api/v1/clinics/{clinic_id}", headers=auth_headers)

    history = await client.get(f"/api/v1/vet-appointments/completed?pet_id={pet_id}", headers=auth_headers)
    assert history.json()[0]["clinic_name"] == "КлиникаВременная"


@pytest.mark.asyncio
async def test_completed_visits_filter_by_pet(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    pet1 = await _create_pet(client, auth_headers, "ИсторияПитомец1")
    pet2 = await _create_pet(client, auth_headers, "ИсторияПитомец2")
    clinic_id = await _create_clinic(client, auth_headers, "КлиникаИстория")
    a1 = await _create_appointment(client, auth_headers, pet1, clinic_id)
    a2 = await _create_appointment(client, auth_headers, pet2, clinic_id)
    await client.post(f"/api/v1/vet-appointments/{a1['id']}/complete", headers=auth_headers)
    await client.post(f"/api/v1/vet-appointments/{a2['id']}/complete", headers=auth_headers)

    res = await client.get(f"/api/v1/vet-appointments/completed?pet_id={pet1}", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["pet_id"] == pet1


@pytest.mark.asyncio
async def test_complete_is_scoped_per_owner(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "complete_owner1@example.com", "username": "complete_owner1", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    pet_id = await _create_pet(client, h1, "ЧужойЗавершённый")
    clinic_id = await _create_clinic(client, h1, "ЧужаяКлиникаЗавершённый")
    appt = await _create_appointment(client, h1, pet_id, clinic_id)

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "complete_owner2@example.com", "username": "complete_owner2", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.post(f"/api/v1/vet-appointments/{appt['id']}/complete", headers=h2)
    assert res.status_code == 404
    history = await client.get(f"/api/v1/vet-appointments/completed?pet_id={pet_id}", headers=h2)
    assert history.status_code == 404
    # The owner's appointment is untouched.
    assert (await client.get(f"/api/v1/vet-appointments/{appt['id']}", headers=h1)).status_code == 200
