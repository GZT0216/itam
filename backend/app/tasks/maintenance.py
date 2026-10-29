import logging
from datetime import datetime

from app.celery_app import celery

logger = logging.getLogger("itam.tasks")


@celery.task(name="app.tasks.maintenance.heartbeat")
def heartbeat() -> str:
    message = f"itam celery heartbeat at {datetime.now().isoformat(timespec='seconds')}"
    logger.info(message)
    return message
