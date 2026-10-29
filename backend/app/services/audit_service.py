from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import get_request_meta
from app.models import AuditLog, User


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        action: str,
        module: str,
        summary: str | None = None,
        actor: User | None = None,
        actor_id: int | None = None,
        actor_name: str | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        status: str = "SUCCESS",
    ) -> AuditLog:
        meta = get_request_meta()
        if actor is not None:
            actor_id = actor.id
            actor_name = actor.username
        log = AuditLog(
            user_id=actor_id,
            username=actor_name,
            action=action,
            module=module,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            summary=summary,
            method=meta["method"] or None,
            path=meta["path"] or None,
            ip=meta["ip"] or None,
            user_agent=(meta["user_agent"] or "")[:255] or None,
            request_id=meta["request_id"] or None,
            status=status,
            before_data=jsonable_encoder(before) if before is not None else None,
            after_data=jsonable_encoder(after) if after is not None else None,
        )
        self.session.add(log)
        return log
