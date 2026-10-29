from sqlalchemy import func, or_, select

from app.models import Dept, User, role_depts
from app.repositories.base import BaseRepository


class DeptRepository(BaseRepository[Dept]):
    model = Dept

    async def list_all(
        self,
        *,
        keyword: str | None = None,
        status: int | None = None,
    ) -> list[Dept]:
        stmt = select(Dept)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(or_(Dept.name.like(pattern), Dept.code.like(pattern)))
        if status is not None:
            stmt = stmt.where(Dept.status == status)
        stmt = stmt.order_by(Dept.sort, Dept.id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_code(self, code: str) -> Dept | None:
        stmt = select(Dept).where(Dept.code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_children(self, dept_id: int) -> int:
        stmt = select(func.count()).select_from(Dept).where(Dept.parent_id == dept_id)
        return int(await self.session.scalar(stmt) or 0)

    async def count_users(self, dept_id: int) -> int:
        stmt = select(func.count()).select_from(User).where(User.dept_id == dept_id)
        return int(await self.session.scalar(stmt) or 0)

    async def count_role_refs(self, dept_id: int) -> int:
        stmt = select(func.count()).select_from(role_depts).where(role_depts.c.dept_id == dept_id)
        return int(await self.session.scalar(stmt) or 0)

    async def user_counts(self) -> dict[int, int]:
        stmt = (
            select(User.dept_id, func.count())
            .where(User.dept_id.is_not(None))
            .group_by(User.dept_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {int(dept_id): int(count) for dept_id, count in rows if dept_id is not None}
