from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.core.exceptions import ConflictError


async def commit_or_conflict(
    session: AsyncSession,
    *,
    message: str = "数据已被他人修改，请刷新后重试",
    code: int = 40901,
) -> None:
    try:
        await session.commit()
    except StaleDataError as exc:
        await session.rollback()
        raise ConflictError(message, code=code) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("数据冲突：唯一字段已被占用或存在关联限制", code=40902) from exc
