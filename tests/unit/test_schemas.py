"""Unit tests for Pydantic schema validation — no DB required."""
import unittest
from datetime import date, timedelta

from pydantic import ValidationError

from app.models.dose import DoseStatus
from app.schemas.auth import RegisterRequest
from app.schemas.calendar import DoseActionRequest
from app.schemas.medication import MedicationCreate
from app.schemas.pet import PetCreate, PetUpdate


class TestRegisterRequest(unittest.TestCase):
    def test_valid_registration(self) -> None:
        req = RegisterRequest(
            email="user@example.com",
            username="testuser",
            password="password123",
        )
        self.assertEqual(req.username, "testuser")

    def test_invalid_email_raises(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(email="not-an-email", username="user", password="password123")

    def test_short_password_raises(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(email="u@e.com", username="user", password="short")

    def test_username_with_special_chars_raises(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(email="u@e.com", username="user name!", password="password123")

    def test_username_too_short_raises(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(email="u@e.com", username="ab", password="password123")

    def test_username_too_long_raises(self) -> None:
        with self.assertRaises(ValidationError):
            RegisterRequest(email="u@e.com", username="a" * 51, password="password123")

    def test_username_with_underscore_ok(self) -> None:
        req = RegisterRequest(email="u@e.com", username="user_name", password="password123")
        self.assertEqual(req.username, "user_name")


class TestPetSchemas(unittest.TestCase):
    def test_valid_pet(self) -> None:
        pet = PetCreate(name="Барсик", species="cat", weight_kg=5.0)
        self.assertEqual(pet.name, "Барсик")
        self.assertEqual(pet.weight_kg, 5.0)
        self.assertIsNone(pet.breed)
        self.assertIsNone(pet.birth_date)

    def test_negative_weight_raises(self) -> None:
        with self.assertRaises(ValidationError):
            PetCreate(name="X", species="cat", weight_kg=-1.0)

    def test_zero_weight_raises(self) -> None:
        with self.assertRaises(ValidationError):
            PetCreate(name="X", species="cat", weight_kg=0.0)

    def test_none_weight_allowed(self) -> None:
        pet = PetCreate(name="X", species="cat", weight_kg=None)
        self.assertIsNone(pet.weight_kg)

    def test_pet_update_all_optional(self) -> None:
        update = PetUpdate()
        self.assertIsNone(update.name)
        self.assertIsNone(update.species)

    def test_pet_update_partial(self) -> None:
        update = PetUpdate(name="Мурка", weight_kg=3.5)
        self.assertEqual(update.name, "Мурка")
        self.assertIsNone(update.breed)


class TestMedicationSchemas(unittest.TestCase):
    def _payload(self) -> dict[str, object]:
        return {
            "pet_id": 1,
            "name": "Амоксициллин",
            "dosage": "250mg",
            "frequency_per_day": 2,
            "start_date": date.today().isoformat(),
        }

    def test_valid_medication(self) -> None:
        med = MedicationCreate(**self._payload())  # type: ignore[arg-type]
        self.assertEqual(med.frequency_per_day, 2)
        self.assertIsNone(med.end_date)

    def test_frequency_too_high_raises(self) -> None:
        data = {**self._payload(), "frequency_per_day": 30}
        with self.assertRaises(ValidationError):
            MedicationCreate(**data)  # type: ignore[arg-type]

    def test_frequency_zero_raises(self) -> None:
        data = {**self._payload(), "frequency_per_day": 0}
        with self.assertRaises(ValidationError):
            MedicationCreate(**data)  # type: ignore[arg-type]

    def test_frequency_negative_raises(self) -> None:
        data = {**self._payload(), "frequency_per_day": -1}
        with self.assertRaises(ValidationError):
            MedicationCreate(**data)  # type: ignore[arg-type]

    def test_end_date_before_start_raises(self) -> None:
        data = {
            **self._payload(),
            "end_date": (date.today() - timedelta(days=1)).isoformat(),
        }
        with self.assertRaises(ValidationError):
            MedicationCreate(**data)  # type: ignore[arg-type]

    def test_valid_end_date_after_start(self) -> None:
        data = {
            **self._payload(),
            "end_date": (date.today() + timedelta(days=7)).isoformat(),
        }
        med = MedicationCreate(**data)  # type: ignore[arg-type]
        self.assertIsNotNone(med.end_date)

    def test_frequency_boundary_24_ok(self) -> None:
        data = {**self._payload(), "frequency_per_day": 24}
        med = MedicationCreate(**data)  # type: ignore[arg-type]
        self.assertEqual(med.frequency_per_day, 24)

    def test_frequency_boundary_25_raises(self) -> None:
        data = {**self._payload(), "frequency_per_day": 25}
        with self.assertRaises(ValidationError):
            MedicationCreate(**data)  # type: ignore[arg-type]


class TestDoseActionRequest(unittest.TestCase):
    def test_taken_status(self) -> None:
        req = DoseActionRequest(status=DoseStatus.TAKEN)
        self.assertEqual(req.status, DoseStatus.TAKEN)

    def test_skipped_status(self) -> None:
        req = DoseActionRequest(status=DoseStatus.SKIPPED)
        self.assertEqual(req.status, DoseStatus.SKIPPED)

    def test_pending_status(self) -> None:
        req = DoseActionRequest(status=DoseStatus.PENDING)
        self.assertEqual(req.status, DoseStatus.PENDING)

    def test_invalid_status_raises(self) -> None:
        with self.assertRaises(ValidationError):
            DoseActionRequest(status="flying")  # type: ignore[arg-type]

    def test_optional_fields_default_none(self) -> None:
        req = DoseActionRequest(status=DoseStatus.TAKEN)
        self.assertIsNone(req.notes)
        self.assertIsNone(req.taken_at)

    def test_notes_passed_through(self) -> None:
        req = DoseActionRequest(status=DoseStatus.SKIPPED, notes="Питомец спал")
        self.assertEqual(req.notes, "Питомец спал")


if __name__ == "__main__":
    unittest.main()
