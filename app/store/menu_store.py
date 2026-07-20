import json
from pathlib import Path

from app.config import Settings
from app.store.models import MenuItem


class MenuStore:
    """File-backed menu storage. Replaces a database table — the app has
    no server-side persistence beyond this JSON file, which the admin
    edits by re-running the scraper (see scraper/swiggy_scraper.py) or
    hand-editing `data/menu.json`. The chatbot only ever reads from here,
    never scrapes live during a conversation.
    """

    def __init__(self, settings: Settings) -> None:
        self._path: Path = settings.menu_file_path

    def load_all(self) -> list[MenuItem]:
        if not self._path.exists():
            return []
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return [MenuItem(**entry) for entry in raw]

    def load_available(self) -> list[MenuItem]:
        return [item for item in self.load_all() if item.is_available]

    def search(self, query: str) -> list[MenuItem]:
        query = query.strip().lower()
        if not query:
            return self.load_available()

        def matches(item: MenuItem) -> bool:
            haystack = " ".join(
                filter(None, [item.name, item.description, item.category])
            ).lower()
            return query in haystack

        return [item for item in self.load_available() if matches(item)]

    def save_all(self, items: list[MenuItem]) -> None:
        payload = [
            {
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "category": item.category,
                "image_url": item.image_url,
                "is_available": item.is_available,
            }
            for item in items
        ]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
