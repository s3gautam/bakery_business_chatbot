"""Rerunnable WarmOven menu scraper.

Usage:
    python -m scraper.swiggy_scraper

Swiggy renders its restaurant pages client-side and embeds the menu as a
JSON blob inside a <script> tag (window.__INITIAL_STATE__ or similar) —
there's no stable server-rendered HTML table to scrape. Because that
embedded state shape changes frequently and isn't publicly documented,
`extract_items_from_page` isolates the "find the JSON blob and pull out
name/price/description/image" step so it can be adjusted in one place the
next time Swiggy changes their page. The parsing below expects a `RESULTS`-
style menu item list (Swiggy's common shape as of this writing); adjust
`_iter_raw_menu_entries` if the site structure changes.

This scraper never runs during a chat conversation — see
`app.repositories.menu_repository.MenuRepository`, which is the only
thing the chatbot itself queries.
"""

import asyncio
import json
import re
import sys

import structlog

from app.config import get_settings
from app.db.session import async_session_factory
from app.repositories.menu_repository import MenuRepository
from app.ssl_utils import build_async_httpx_client

logger = structlog.get_logger(__name__)

WARMOVEN_MENU_URL = (
    "https://www.swiggy.com/city/gurgaon/"
    "warmoven-cake-and-desserts-sector-49-sohna-road-rest1296665"
)

_STATE_SCRIPT_RE = re.compile(
    r"window\.___INITIAL_STATE___\s*=\s*(\{.*?\})\s*;\s*</script>", re.DOTALL
)


class MenuScrapeError(RuntimeError):
    pass


def _iter_raw_menu_entries(page_state: dict) -> list[dict]:
    """Walk the embedded page state looking for menu item dicts.

    Swiggy menu item entries carry `name`, `price` (or `defaultPrice`,
    in paise), and usually `description`/`imageId`. We do a defensive
    recursive search rather than hardcoding a fixed path, since the exact
    nesting under page_state changes between deployments.
    """
    found: list[dict] = []
    seen_ids: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "name" in node and ("price" in node or "defaultPrice" in node):
                item_id = str(node.get("id") or node.get("itemId") or node["name"])
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(page_state)
    return found


def extract_items_from_page(html: str) -> list[dict]:
    match = _STATE_SCRIPT_RE.search(html)
    if not match:
        raise MenuScrapeError(
            "Could not locate embedded page state in Swiggy HTML — the "
            "page structure may have changed."
        )

    try:
        page_state = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise MenuScrapeError("Embedded page state was not valid JSON.") from exc

    raw_entries = _iter_raw_menu_entries(page_state)

    items = []
    for entry in raw_entries:
        price_paise = entry.get("price") or entry.get("defaultPrice") or 0
        image_id = entry.get("imageId")
        items.append(
            {
                "source_id": str(entry.get("id") or entry.get("itemId") or entry["name"]),
                "name": entry["name"],
                "description": entry.get("description") or None,
                "price": round(float(price_paise) / 100, 2),
                "image_url": (
                    f"https://media-assets.swiggy.com/swiggy/image/upload/{image_id}"
                    if image_id
                    else None
                ),
                "category": entry.get("category") or None,
            }
        )
    return items


async def fetch_menu_html() -> str:
    settings = get_settings()
    async with build_async_httpx_client(
        settings, timeout=30.0, follow_redirects=True
    ) as client:
        response = await client.get(
            WARMOVEN_MENU_URL,
            headers={"User-Agent": "Mozilla/5.0 (WarmOven menu sync bot)"},
        )
        response.raise_for_status()
        return response.text


async def sync_menu() -> int:
    html = await fetch_menu_html()
    items = extract_items_from_page(html)

    async with async_session_factory() as session:
        repository = MenuRepository(session)
        for item in items:
            await repository.upsert_from_scrape(
                source_id=item["source_id"],
                name=item["name"],
                description=item["description"],
                price=item["price"],
                image_url=item["image_url"],
                category=item["category"],
            )
        await session.commit()

    logger.info("menu_sync_complete", item_count=len(items))
    return len(items)


def main() -> None:
    count = asyncio.run(sync_menu())
    print(f"Synced {count} menu items.")


if __name__ == "__main__":
    try:
        main()
    except MenuScrapeError as exc:
        logger.error("menu_sync_failed", error=str(exc))
        sys.exit(1)
