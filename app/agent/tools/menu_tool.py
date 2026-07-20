from app.store.menu_store import MenuStore
from app.store.models import MenuItem


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
    """Agent tool: searches the menu file only. Never scrapes and never
    returns items not present in `data/menu.json`.
    """

    def __init__(self, store: MenuStore) -> None:
        self._store = store

    async def search(self, query: str) -> str:
        items = self._store.search(query) if query.strip() else []
        if not items:
            items = self._store.load_available()
        return format_menu_items(items[:15])
