from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu_item import MenuItem


class MenuRepository:
    """Read/write access to menu_items. The agent's Menu Tool must go
    through this repository — it must never scrape during a conversation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_available(self) -> list[MenuItem]:
        result = await self._session.execute(
            select(MenuItem).where(MenuItem.is_available.is_(True)).order_by(MenuItem.name)
        )
        return list(result.scalars().all())

    async def search(self, query: str) -> list[MenuItem]:
        like = f"%{query.strip()}%"
        result = await self._session.execute(
            select(MenuItem)
            .where(MenuItem.is_available.is_(True))
            .where(
                MenuItem.name.ilike(like)
                | MenuItem.description.ilike(like)
                | MenuItem.category.ilike(like)
            )
            .order_by(MenuItem.name)
        )
        return list(result.scalars().all())

    async def by_category(self, category: str) -> list[MenuItem]:
        result = await self._session.execute(
            select(MenuItem)
            .where(MenuItem.is_available.is_(True))
            .where(MenuItem.category.ilike(f"%{category.strip()}%"))
            .order_by(MenuItem.name)
        )
        return list(result.scalars().all())

    async def upsert_from_scrape(
        self,
        source_id: str,
        name: str,
        description: str | None,
        price: float,
        image_url: str | None,
        category: str | None,
    ) -> MenuItem:
        result = await self._session.execute(
            select(MenuItem).where(MenuItem.source_id == source_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            item = MenuItem(source_id=source_id)
            self._session.add(item)

        item.name = name
        item.description = description
        item.price = price
        item.image_url = image_url
        item.category = category
        item.is_available = True
        return item
