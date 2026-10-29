from sqlalchemy import select

from app.models import Menu
from app.repositories.base import BaseRepository


class MenuRepository(BaseRepository[Menu]):
    model = Menu

    async def list_all_enabled(self) -> list[Menu]:
        stmt = select(Menu).where(Menu.status == 1).order_by(Menu.sort, Menu.id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_visible(self) -> list[Menu]:
        stmt = (
            select(Menu)
            .where(
                Menu.status == 1,
                Menu.visible.is_(True),
                Menu.type.in_(("DIR", "MENU")),
            )
            .order_by(Menu.sort, Menu.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())
