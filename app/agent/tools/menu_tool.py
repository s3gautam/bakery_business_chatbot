from app.models.menu_item import MenuItem
from app.repositories.menu_repository import MenuRepository


def format_menu_items(items: list[MenuItem]) -> str:
    if not items:
        return "NO_MATCHING_ITEMS"

    lines = []
    for item in items:
        line = f"- {item.name}: Rs. {item.price}"
        if item.category:
            line += f" ({item.category})"
        if item.description:
            line += f" — {item.description}"
        lines.append(line)
    return "\n".join(lines)


class MenuTool:
    """Agent tool: searches the menu database only. Never scrapes and
    never returns items not present in the database.
    """

    def __init__(self, repository: MenuRepository) -> None:
        self._repository = repository

    async def search(self, query: str) -> str:
        items = await self._repository.search(query) if query.strip() else []
        if not items:
            items = await self._repository.list_available()
        return format_menu_items(items[:15])
