import asyncio
import logging

from app.celery_app import celery
from app.core.database import AsyncSessionLocal
from app.services.asset_flow_service import AssetFlowService

logger = logging.getLogger("itam.asset_flow")


async def _scan_due_borrows() -> int:
    async with AsyncSessionLocal() as session:
        return await AssetFlowService(session).record_due_reminders()


@celery.task(name="app.tasks.asset_flow.scan_due_borrows")
def scan_due_borrows() -> int:
    try:
        return asyncio.run(_scan_due_borrows())
    except Exception:  # noqa: BLE001 - scheduled task must not break the worker
        logger.exception("scan due borrows failed")
        return 0
