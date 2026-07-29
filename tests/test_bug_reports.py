import pytest


@pytest.mark.asyncio
async def test_create_bug_report(client, auth_headers):
    res = await client.post(
        "/api/v1/bug-reports", headers=auth_headers, json={"message": "Кнопка не работает"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["message"] == "Кнопка не работает"
    assert data["is_resolved"] is False
    assert data["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_create_bug_report_blank_message_rejected(client, auth_headers):
    res = await client.post("/api/v1/bug-reports", headers=auth_headers, json={"message": "   "})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_list_bug_reports_requires_admin(client, auth_headers):
    await client.post(
        "/api/v1/bug-reports", headers=auth_headers, json={"message": "Ошибка на календаре"}
    )
    res = await client.get("/api/v1/bug-reports", headers=auth_headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_list_and_resolve_bug_report(client, auth_headers, admin_headers):
    create_res = await client.post(
        "/api/v1/bug-reports", headers=auth_headers, json={"message": "Ошибка на календаре"}
    )
    report_id = create_res.json()["id"]

    list_res = await client.get("/api/v1/bug-reports", headers=admin_headers)
    assert list_res.status_code == 200
    assert any(r["id"] == report_id for r in list_res.json())

    update_res = await client.patch(
        f"/api/v1/bug-reports/{report_id}", headers=admin_headers, json={"is_resolved": True}
    )
    assert update_res.status_code == 200
    assert update_res.json()["is_resolved"] is True
    assert update_res.json()["resolved_at"] is not None

    filtered_res = await client.get(
        "/api/v1/bug-reports", headers=admin_headers, params={"is_resolved": True}
    )
    assert any(r["id"] == report_id for r in filtered_res.json())
