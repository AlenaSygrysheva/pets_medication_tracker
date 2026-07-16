"""Unit tests for password hashing and JWT token functions."""
import unittest
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing(unittest.TestCase):
    def test_hash_differs_from_plain(self) -> None:
        hashed = hash_password("mypassword")
        self.assertNotEqual(hashed, "mypassword")

    def test_correct_password_verifies(self) -> None:
        hashed = hash_password("correct_password")
        self.assertTrue(verify_password("correct_password", hashed))

    def test_wrong_password_fails(self) -> None:
        hashed = hash_password("correct_password")
        self.assertFalse(verify_password("wrong_password", hashed))

    def test_bcrypt_uses_random_salt(self) -> None:
        h1 = hash_password("same_pass")
        h2 = hash_password("same_pass")
        self.assertNotEqual(h1, h2)
        self.assertTrue(verify_password("same_pass", h1))
        self.assertTrue(verify_password("same_pass", h2))

    def test_empty_hash_does_not_verify(self) -> None:
        self.assertFalse(verify_password("anypass", hash_password("different")))


class TestJWTTokens(unittest.TestCase):
    USER_ID = 42

    def test_access_token_type(self) -> None:
        token = create_access_token(self.USER_ID)
        payload = decode_token(token)
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["type"], "access")

    def test_access_token_subject(self) -> None:
        token = create_access_token(self.USER_ID)
        payload = decode_token(token)
        assert payload is not None
        self.assertEqual(int(payload["sub"]), self.USER_ID)

    def test_refresh_token_type(self) -> None:
        token = create_refresh_token(self.USER_ID)
        payload = decode_token(token)
        assert payload is not None
        self.assertEqual(payload["type"], "refresh")

    def test_access_and_refresh_tokens_differ(self) -> None:
        access = create_access_token(self.USER_ID)
        refresh = create_refresh_token(self.USER_ID)
        self.assertNotEqual(access, refresh)

    def test_decode_invalid_token_returns_none(self) -> None:
        self.assertIsNone(decode_token("not.a.valid.token"))

    def test_decode_empty_string_returns_none(self) -> None:
        self.assertIsNone(decode_token(""))

    def test_decode_expired_token_returns_none(self) -> None:
        expired = datetime.now(UTC) - timedelta(seconds=1)
        token = jwt.encode(
            {"sub": "1", "exp": expired, "type": "access"},
            settings.SECRET_KEY,
            settings.ALGORITHM,
        )
        self.assertIsNone(decode_token(token))

    def test_decode_tampered_signature_returns_none(self) -> None:
        token = create_access_token(1)
        tampered = token[:-10] + "X" * 10
        self.assertIsNone(decode_token(tampered))

    def test_decode_wrong_secret_returns_none(self) -> None:
        token = jwt.encode(
            {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=30), "type": "access"},
            "wrong_secret",
            settings.ALGORITHM,
        )
        self.assertIsNone(decode_token(token))


if __name__ == "__main__":
    unittest.main()
