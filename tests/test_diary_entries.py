"""Integration tests for the pet condition diary endpoints."""
import pytest
from httpx import AsyncClient

URL = "/api/v1/diary-entries"


async def _create_pet(client: AsyncClient, headers: dict[str, str], name: str = "Барсик") -> int:
    res = await client.post("/api/v1/pets", headers=headers, json={"name": name, "species": "кот"})
    id_: int = res.json()["id"]
    return id_


async def _create_entry(client: AsyncClient, headers: dict[str, str], pet_id: int, text: str) -> dict:
    res = await client.post(URL, headers=headers, json={"pet_id": pet_id, "text": text})
    assert res.status_code == 201
    data: dict = res.json()
    return data


async def _register(client: AsyncClient, name: str) -> dict[str, str]:
    res = await client.post("/api/v1/auth/register", json={
        "email": f"{name}@example.com", "username": name, "password": "pass1234",
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_entry_sets_created_at(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникСоздание")
    entry = await _create_entry(client, auth_headers, pet_id, "  Вялый, плохо ел  ")
    assert entry["pet_id"] == pet_id
    assert entry["text"] == "Вялый, плохо ел"
    assert entry["created_at"]
    assert entry["updated_at"]


@pytest.mark.asyncio
async def test_text_up_to_500_chars(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникДлина")
    await _create_entry(client, auth_headers, pet_id, "я" * 500)

    res = await client.post(URL, headers=auth_headers, json={"pet_id": pet_id, "text": "я" * 501})
    assert res.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "   "])
async def test_blank_text_rejected(client: AsyncClient, auth_headers: dict[str, str], text: str) -> None:
    pet_id = await _create_pet(client, auth_headers, f"ДневникПусто{text!r}")
    res = await client.post(URL, headers=auth_headers, json={"pet_id": pet_id, "text": text})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_create_for_unknown_pet_returns_404(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.post(URL, headers=auth_headers, json={"pet_id": 999999, "text": "x"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_by_pet_newest_first(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet1 = await _create_pet(client, auth_headers, "ДневникСписок1")
    pet2 = await _create_pet(client, auth_headers, "ДневникСписок2")
    first = await _create_entry(client, auth_headers, pet1, "первая")
    second = await _create_entry(client, auth_headers, pet1, "вторая")
    await _create_entry(client, auth_headers, pet2, "чужой питомец")

    res = await client.get(f"{URL}?pet_id={pet1}", headers=auth_headers)
    assert res.status_code == 200
    assert [e["id"] for e in res.json()] == [second["id"], first["id"]]


@pytest.mark.asyncio
async def test_update_entry_keeps_created_at(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникПравка")
    entry = await _create_entry(client, auth_headers, pet_id, "до")

    res = await client.patch(f"{URL}/{entry['id']}", headers=auth_headers, json={"text": "после"})
    assert res.status_code == 200
    assert res.json()["text"] == "после"
    assert res.json()["created_at"] == entry["created_at"]

    too_long = await client.patch(f"{URL}/{entry['id']}", headers=auth_headers, json={"text": "я" * 501})
    assert too_long.status_code == 422
    blank = await client.patch(f"{URL}/{entry['id']}", headers=auth_headers, json={"text": " "})
    assert blank.status_code == 422


@pytest.mark.asyncio
async def test_delete_entry(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникУдаление")
    entry = await _create_entry(client, auth_headers, pet_id, "удалить")

    res = await client.delete(f"{URL}/{entry['id']}", headers=auth_headers)
    assert res.status_code == 204
    assert (await client.get(f"{URL}/{entry['id']}", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникМассово")
    e1 = await _create_entry(client, auth_headers, pet_id, "1")
    e2 = await _create_entry(client, auth_headers, pet_id, "2")
    e3 = await _create_entry(client, auth_headers, pet_id, "3")

    res = await client.post(f"{URL}/bulk-delete", headers=auth_headers, json={"ids": [e1["id"], e3["id"]]})
    assert res.status_code == 204
    listed = await client.get(f"{URL}?pet_id={pet_id}", headers=auth_headers)
    assert [e["id"] for e in listed.json()] == [e2["id"]]


@pytest.mark.asyncio
async def test_bulk_delete_is_all_or_nothing(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникВсёИлиНичего")
    entry = await _create_entry(client, auth_headers, pet_id, "останется")

    res = await client.post(f"{URL}/bulk-delete", headers=auth_headers, json={"ids": [entry["id"], 999999]})
    assert res.status_code == 404
    assert (await client.get(f"{URL}/{entry['id']}", headers=auth_headers)).status_code == 200


@pytest.mark.asyncio
async def test_bulk_delete_empty_list_rejected(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    res = await client.post(f"{URL}/bulk-delete", headers=auth_headers, json={"ids": []})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_entries_are_scoped_per_owner(client: AsyncClient) -> None:
    h1 = await _register(client, "diary_owner1")
    h2 = await _register(client, "diary_owner2")
    pet_id = await _create_pet(client, h1, "ДневникЧужой")
    entry = await _create_entry(client, h1, pet_id, "секрет")

    assert (await client.get(f"{URL}/{entry['id']}", headers=h2)).status_code == 404
    assert (await client.get(f"{URL}?pet_id={pet_id}", headers=h2)).status_code == 404
    assert (await client.patch(f"{URL}/{entry['id']}", headers=h2, json={"text": "x"})).status_code == 404
    assert (await client.delete(f"{URL}/{entry['id']}", headers=h2)).status_code == 404
    bulk = await client.post(f"{URL}/bulk-delete", headers=h2, json={"ids": [entry["id"]]})
    assert bulk.status_code == 404
    assert (await client.get(f"{URL}/{entry['id']}", headers=h1)).json()["text"] == "секрет"


@pytest.mark.asyncio
async def test_entries_deleted_with_pet(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    pet_id = await _create_pet(client, auth_headers, "ДневникКаскад")
    entry = await _create_entry(client, auth_headers, pet_id, "x")

    await client.delete(f"/api/v1/pets/{pet_id}", headers=auth_headers)
    assert (await client.get(f"{URL}/{entry['id']}", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_diary_requires_auth(client: AsyncClient) -> None:
    res = await client.get(URL)
    assert res.status_code == 403
