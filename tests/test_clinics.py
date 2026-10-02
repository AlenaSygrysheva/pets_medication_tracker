"""Integration tests for the clinics catalog endpoints."""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


def _clinic_payload(name: str) -> dict[str, str]:
    return {"name": name, "address": "ул. Ленина, 1", "phone": "79991234567"}


@pytest.mark.asyncio
async def test_create_clinic(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.post("/api/v1/clinics", headers=auth_headers, json={
        "name": "ВетСтар", "address": "ул. Ленина, 1", "phone": "79991234567",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "ВетСтар"
    assert data["address"] == "ул. Ленина, 1"
    assert data["phone"] == "79991234567"
    assert data["website"] is None


@pytest.mark.asyncio
async def test_create_clinic_with_website(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.post("/api/v1/clinics", headers=auth_headers, json={
        "name": "КлиникаССайтом", "address": "ул. Ленина, 1", "phone": "79991234567",
        "website": "https://vetstar.example",
    })
    assert res.status_code == 201
    assert res.json()["website"] == "https://vetstar.example"


@pytest.mark.asyncio
async def test_create_clinic_without_address_or_phone_returns_422(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.post("/api/v1/clinics", headers=auth_headers, json={"name": "БезАдреса"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_clinic_phone_with_letters_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.post("/api/v1/clinics", headers=auth_headers, json={
        "name": "КлиникаБукв", "address": "ул. Ленина, 1", "phone": "79991234abc",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_clinic_phone_with_symbols_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.post("/api/v1/clinics", headers=auth_headers, json={
        "name": "КлиникаСимволы", "address": "ул. Ленина, 1", "phone": "+7 999 123-45-67",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_clinic_phone_too_short_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.post("/api/v1/clinics", headers=auth_headers, json={
        "name": "КлиникаКороткийТелефон", "address": "ул. Ленина, 1", "phone": "12345",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_clinic_phone_validates(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    created = await client.post(
        "/api/v1/clinics", headers=auth_headers, json=_clinic_payload("КлиникаОбновлениеТелефона")
    )
    clinic_id = created.json()["id"]

    res = await client.patch(f"/api/v1/clinics/{clinic_id}", headers=auth_headers, json={
        "phone": "not-a-phone",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_409(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    payload = _clinic_payload("ДубликатКлиника")
    first = await client.post("/api/v1/clinics", headers=auth_headers, json=payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/clinics", headers=auth_headers, json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_list_clinics_excludes_deleted(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post(
        "/api/v1/clinics", headers=auth_headers, json=_clinic_payload("СписокУдаление")
    )
    clinic_id = created.json()["id"]

    await client.delete(f"/api/v1/clinics/{clinic_id}", headers=auth_headers)

    res = await client.get("/api/v1/clinics", headers=auth_headers)
    assert res.status_code == 200
    assert all(c["id"] != clinic_id for c in res.json())


@pytest.mark.asyncio
async def test_update_clinic(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    created = await client.post(
        "/api/v1/clinics", headers=auth_headers, json=_clinic_payload("ОбновляемаяКлиника")
    )
    clinic_id = created.json()["id"]

    res = await client.patch(f"/api/v1/clinics/{clinic_id}", headers=auth_headers, json={
        "address": "новый адрес",
    })
    assert res.status_code == 200
    assert res.json()["address"] == "новый адрес"
    assert res.json()["name"] == "ОбновляемаяКлиника"


@pytest.mark.asyncio
async def test_delete_clinic_not_in_use_succeeds(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    created = await client.post(
        "/api/v1/clinics", headers=auth_headers, json=_clinic_payload("НеиспользуемаяКлиника")
    )
    clinic_id = created.json()["id"]

    res = await client.delete(f"/api/v1/clinics/{clinic_id}", headers=auth_headers)
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_delete_clinic_blocked_with_upcoming_appointment(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    clinic = await client.post(
        "/api/v1/clinics", headers=auth_headers, json=_clinic_payload("КлиникаСПриёмом")
    )
    clinic_id = clinic.json()["id"]
    pet = await client.post(
        "/api/v1/pets", headers=auth_headers, json={"name": "ПитомецПриём", "species": "кот"}
    )
    pet_id = pet.json()["id"]

    appointment_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    reminder_at = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    await client.post("/api/v1/vet-appointments", headers=auth_headers, json={
        "pet_id": pet_id, "clinic_id": clinic_id,
        "appointment_at": appointment_at, "reminder_at": reminder_at,
    })

    res = await client.delete(f"/api/v1/clinics/{clinic_id}", headers=auth_headers)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_delete_clinic_not_found_returns_404(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    res = await client.delete("/api/v1/clinics/999999", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_clinics_are_scoped_per_owner(client: AsyncClient) -> None:
    r1 = await client.post("/api/v1/auth/register", json={
        "email": "clinic_owner1@example.com", "username": "clinic_owner1", "password": "pass1234",
    })
    h1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
    created = await client.post("/api/v1/clinics", headers=h1, json=_clinic_payload("ЧужаяКлиника"))
    clinic_id = created.json()["id"]

    r2 = await client.post("/api/v1/auth/register", json={
        "email": "clinic_owner2@example.com", "username": "clinic_owner2", "password": "pass1234",
    })
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

    res = await client.post("/api/v1/clinics", headers=h2, json=_clinic_payload("ЧужаяКлиника"))
    assert res.status_code == 201

    get_res = await client.get(f"/api/v1/clinics/{clinic_id}", headers=h2)
    assert get_res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_clinics_require_auth(client: AsyncClient) -> None:
    res = await client.get("/api/v1/clinics")
    assert res.status_code == 403
