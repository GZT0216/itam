import asyncio
import logging

from app.celery_app import celery
from app.core.database import AsyncSessionLocal
from app.services.contract_service import ContractService

logger = logging.getLogger("itam.contract")


async def _scan_due_contracts() -> int:
    async with AsyncSessionLocal() as session:
        return await ContractService(session).scan_due_reminders()


@celery.task(name="app.tasks.contract.scan_due_contracts")
def scan_due_contracts() -> int:
    try:
        return asyncio.run(_scan_due_contracts())
    except Exception:  # noqa: BLE001 - scheduled task must not break the worker
        logger.exception("scan due contracts failed")
        return 0
