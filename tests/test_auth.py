import re
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    res = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "username": "newuser",
        "password": "securepass",
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "username": "user1", "password": "pass1234"}
    await client.post("/api/v1/auth/register", json=payload)
    res = await client.post("/api/v1/auth/register", json={**payload, "username": "user2"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "username": "loginuser", "password": "pass1234"
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com", "password": "pass1234"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com", "username": "wronguser", "password": "correct"
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com", "password": "incorrect"
    })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_returns_generic_message(client):
    res = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert res.status_code == 200
    assert "message" in res.json()


@pytest.mark.asyncio
async def test_forgot_password_known_email_sends_email_with_reset_link(client):
    await client.post("/api/v1/auth/register", json={
        "email": "forgot@example.com", "username": "forgotuser", "password": "pass1234",
    })

    with patch("app.services.auth_service.send_email", new_callable=AsyncMock) as mock_send:
        res = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "forgot@example.com"}
        )

    assert res.status_code == 200
    mock_send.assert_awaited_once()
    to_email, _subject, body = mock_send.call_args[0]
    assert to_email == "forgot@example.com"
    assert "reset_token=" in body


@pytest.mark.asyncio
async def test_reset_password_with_valid_token_changes_password(client):
    await client.post("/api/v1/auth/register", json={
        "email": "resetme@example.com", "username": "resetmeuser", "password": "oldpass123",
    })

    with patch("app.services.auth_service.send_email", new_callable=AsyncMock) as mock_send:
        await client.post("/api/v1/auth/forgot-password", json={"email": "resetme@example.com"})
    token = re.search(r"reset_token=(\S+)", mock_send.call_args[0][2]).group(1)

    res = await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "newpass456",
    })
    assert res.status_code == 200

    login_new = await client.post("/api/v1/auth/login", json={
        "email": "resetme@example.com", "password": "newpass456",
    })
    assert login_new.status_code == 200

    login_old = await client.post("/api/v1/auth/login", json={
        "email": "resetme@example.com", "password": "oldpass123",
    })
    assert login_old.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_token_is_single_use(client):
    await client.post("/api/v1/auth/register", json={
        "email": "singleuse@example.com", "username": "singleuseuser", "password": "oldpass123",
    })
    with patch("app.services.auth_service.send_email", new_callable=AsyncMock) as mock_send:
        await client.post("/api/v1/auth/forgot-password", json={"email": "singleuse@example.com"})
    token = re.search(r"reset_token=(\S+)", mock_send.call_args[0][2]).group(1)

    first = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "firstpass1"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "secondpass2"}
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_invalid_token_returns_400(client):
    res = await client.post("/api/v1/auth/reset-password", json={
        "token": "not-a-real-token", "new_password": "whatever123",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_weak_password_returns_422(client):
    res = await client.post("/api/v1/auth/reset-password", json={
        "token": "whatever-token", "new_password": "short",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_with_username_instead_of_email_returns_422(client):
    """The email field is validated as EmailStr — typing a bare username must not
    silently fail; FastAPI should reject it with a 422 the frontend can surface."""
    await client.post("/api/v1/auth/register", json={
        "email": "byusername@example.com", "username": "byusernameuser", "password": "pass1234",
    })
    res = await client.post("/api/v1/auth/login", json={
        "email": "byusernameuser", "password": "pass1234",
    })
    assert res.status_code == 422
