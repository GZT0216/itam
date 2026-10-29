import asyncio
import logging

from app.celery_app import celery
from app.core.database import AsyncSessionLocal
from app.services.reminder_service import ReminderService

logger = logging.getLogger("itam.reminder")


async def _scan_due_reminders() -> int:
    async with AsyncSessionLocal() as session:
        result = await ReminderService(session).scan()
        return result.total


@celery.task(name="app.tasks.reminders.scan_due_reminders")
def scan_due_reminders() -> int:
    try:
        return asyncio.run(_scan_due_reminders())
    except Exception:  # noqa: BLE001 - scheduled task must not break the worker
        logger.exception("scan due reminders failed")
        return 0
