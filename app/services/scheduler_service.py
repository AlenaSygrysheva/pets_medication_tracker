import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal
from app.models.dose import DoseStatus
from app.repositories.dose_repo import DoseRepository
from app.services.medication_service import MedicationService

logger = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler(timezone="UTC")


async def mark_overdue_doses() -> None:
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    logger.info("Scheduler: checking overdue doses (cutoff=%s)", cutoff.isoformat())
    async with AsyncSessionLocal() as db:
        repo = DoseRepository(db)
        medication_service = MedicationService(db)
        overdue = await repo.get_overdue_pending(cutoff)
        if overdue:
            for dose in overdue:
                dose.status = DoseStatus.MISSED
                await medication_service.extend_after_unresolved_dose(dose.medication)
            await db.commit()
            logger.info("Scheduler: marked %d doses as MISSED", len(overdue))
        else:
            logger.info("Scheduler: no overdue doses found")


def start_scheduler() -> None:
    scheduler.add_job(mark_overdue_doses, "interval", minutes=30, id="mark_overdue")
    scheduler.start()
    logger.info("Scheduler started — check interval: 30 min")


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")
