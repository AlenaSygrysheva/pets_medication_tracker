"""Collects everything that goes into a pet's PDF card. Rendering is in pet_report_pdf.py."""
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.diagnosis import Diagnosis
from app.models.diary_entry import DiaryEntry
from app.models.pet import Pet
from app.repositories.completed_vet_visit_repo import CompletedVetVisitRepository
from app.repositories.diagnosis_repo import DiagnosisRepository
from app.repositories.diary_entry_repo import DiaryEntryRepository
from app.repositories.dose_repo import DoseRepository
from app.repositories.medication_repo import MedicationRepository
from app.repositories.pet_repo import PetRepository
from app.repositories.vet_appointment_repo import VetAppointmentRepository
from app.schemas.pet_report import PetReportRequest
from app.services.medication_service import MedicationService
from app.services.pet_report_pdf import render_pet_report


@dataclass
class ReportCourse:
    drug: str  # "Энроксил 15 мг"
    dosage: str  # per intake, "1 таблетка"
    frequency_per_day: int
    start: date
    end: date
    status: str  # "active" | "completed" | "cancelled"


@dataclass
class ReportVetVisit:
    appointment_at: datetime  # literal user time, like everywhere else in the app
    completed: bool
    clinic_name: str
    clinic_address: str | None
    clinic_phone: str | None
    clinic_website: str | None
    doctor_name: str | None
    comments: str | None


@dataclass
class PetReportData:
    pet: Pet
    request: PetReportRequest
    diagnoses: list[Diagnosis]
    courses: list[ReportCourse]
    vet_visits: list[ReportVetVisit]
    diary_entries: list[DiaryEntry]
    generated_on: date


class PetReportService:
    def __init__(self, db: AsyncSession):
        self.pet_repo = PetRepository(db)
        self.diagnosis_repo = DiagnosisRepository(db)
        self.diary_repo = DiaryEntryRepository(db)
        self.medication_repo = MedicationRepository(db)
        self.dose_repo = DoseRepository(db)
        self.appointment_repo = VetAppointmentRepository(db)
        self.completed_repo = CompletedVetVisitRepository(db)

    async def build_pdf(self, pet_id: int, owner_id: int, req: PetReportRequest) -> tuple[Pet, bytes]:
        data = await self.collect(pet_id, owner_id, req)
        return data.pet, render_pet_report(data)

    async def collect(self, pet_id: int, owner_id: int, req: PetReportRequest) -> PetReportData:
        pet = await self.pet_repo.get_by_id(pet_id)
        if not pet or pet.owner_id != owner_id:
            raise NotFoundError("Pet not found")

        diagnoses = await self.diagnosis_repo.get_all_by_owner(owner_id, pet_id)
        diary = await self.diary_repo.get_all_by_owner(owner_id, pet_id)
        return PetReportData(
            pet=pet,
            request=req,
            diagnoses=self._pick(diagnoses, req.diagnosis_ids, "Diagnosis"),
            courses=await self._courses(pet_id, req.date_from, req.date_to),
            vet_visits=await self._vet_visits(owner_id, pet_id, req.date_from, req.date_to),
            # Diary reads chronologically in a document, unlike the newest-first list in the app.
            diary_entries=sorted(
                self._pick(diary, req.diary_entry_ids, "Diary entry"), key=lambda e: (e.created_at, e.id)
            ),
            generated_on=datetime.now(UTC).date(),
        )

    @staticmethod
    def _pick[T: (Diagnosis, DiaryEntry)](items: list[T], ids: list[int], what: str) -> list[T]:
        """Keeps the selected items of this pet; an id from another pet/owner is a 404."""
        by_id = {item.id: item for item in items}
        missing = set(ids) - by_id.keys()
        if missing:
            raise NotFoundError(f"{what} not found")
        wanted = set(ids)
        return [item for item in items if item.id in wanted]

    async def _courses(self, pet_id: int, start: date, end: date) -> list[ReportCourse]:
        courses = []
        for med in await self.medication_repo.get_all_by_pet(pet_id):
            counts = await self.dose_repo.get_status_counts(med.id)
            last = await self.dose_repo.get_last_scheduled(med.id)
            # The real last day: missed doses push the course past end_date, and a
            # cancelled one stops before it.
            course_end = last.scheduled_at.date() if last else (med.end_date or med.start_date)
            if med.start_date > end or course_end < start:
                continue
            courses.append(ReportCourse(
                drug=f"{med.drug.name} {med.drug.strength}".strip(),
                dosage=med.dosage,
                frequency_per_day=med.frequency_per_day,
                start=med.start_date,
                end=course_end,
                status=MedicationService.course_status(med, counts.get("pending", 0)),
            ))
        return sorted(courses, key=lambda c: (c.start, c.drug))

    async def _vet_visits(self, owner_id: int, pet_id: int, start: date, end: date) -> list[ReportVetVisit]:
        visits = [
            ReportVetVisit(
                appointment_at=a.appointment_at, completed=False,
                clinic_name=a.clinic.name, clinic_address=a.clinic.address,
                clinic_phone=a.clinic.phone, clinic_website=a.clinic.website,
                doctor_name=a.doctor_name, comments=a.comments,
            )
            for a in await self.appointment_repo.get_all_by_owner(owner_id, pet_id)
        ] + [
            ReportVetVisit(
                appointment_at=v.appointment_at, completed=True,
                clinic_name=v.clinic_name, clinic_address=v.clinic_address,
                clinic_phone=v.clinic_phone, clinic_website=None,
                doctor_name=v.doctor_name, comments=v.comments,
            )
            for v in await self.completed_repo.get_all_by_owner(owner_id, pet_id)
        ]
        in_period = [v for v in visits if start <= v.appointment_at.date() <= end]
        return sorted(in_period, key=lambda v: v.appointment_at.replace(tzinfo=None))
