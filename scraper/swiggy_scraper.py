"""Rerunnable WarmOven menu scraper (Swiggy or Zomato).

Usage:
    python -m scraper.swiggy_scraper

The menu source link is admin-configurable (see the Configure page /
`GET|PUT /config`, `BusinessConfig.menu_source_url`) — this module reads
it from the database rather than a hardcoded URL, and picks a parser
based on the domain.

Both Swiggy and Zomato render their restaurant pages client-side and
embed the menu as a JSON blob inside a <script> tag — there's no stable
server-rendered HTML table to scrape. Because that embedded state shape
changes frequently and isn't publicly documented, `extract_items_from_page`
isolates the "find the JSON blob and pull out name/price/description/
image" step so it can be adjusted in one place the next time either site
changes their page. Adjust `_iter_raw_menu_entries` / `_STATE_SCRIPT_PATTERNS`
if the site structure changes.

This scraper never runs during a chat conversation — see
`app.repositories.menu_repository.MenuRepository`, which is the only
thing the chatbot itself queries.
"""

import asyncio
import json
import re
import sys
from urllib.parse import urlparse

import structlog

from app.db.session import async_session_factory
from app.repositories.config_repository import ConfigRepository
from app.repositories.menu_repository import MenuRepository
from app.config import get_settings
from app.ssl_utils import build_async_httpx_client

logger = structlog.get_logger(__name__)

# (platform, regex-to-locate-embedded-JSON, price-is-in-paise)
_STATE_SCRIPT_PATTERNS: list[tuple[str, re.Pattern, bool]] = [
    (
        "swiggy",
        re.compile(r"window\.___INITIAL_STATE___\s*=\s*(\{.*?\})\s*;\s*</script>", re.DOTALL),
        True,
    ),
    (
        "zomato",
        re.compile(r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>", re.DOTALL),
        False,
    ),
]


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "zomato" in host:
        return "zomato"
    return "swiggy"


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


def extract_items_from_page(html: str, platform: str) -> list[dict]:
    pattern = next((p for name, p, _ in _STATE_SCRIPT_PATTERNS if name == platform), None)
    price_is_paise = next(
        (paise for name, _, paise in _STATE_SCRIPT_PATTERNS if name == platform), True
    )
    if pattern is None:
        raise MenuScrapeError(f"Unsupported menu platform: {platform!r}")

    match = pattern.search(html)
    if not match:
        raise MenuScrapeError(
            f"Could not locate embedded page state in {platform} HTML — the "
            "page structure may have changed."
        )

    try:
        page_state = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise MenuScrapeError("Embedded page state was not valid JSON.") from exc

    raw_entries = _iter_raw_menu_entries(page_state)
    price_divisor = 100.0 if price_is_paise else 1.0

    items = []
    for entry in raw_entries:
        raw_price = entry.get("price") or entry.get("defaultPrice") or 0
        image_id = entry.get("imageId")
        items.append(
            {
                "source_id": str(entry.get("id") or entry.get("itemId") or entry["name"]),
                "name": entry["name"],
                "description": entry.get("description") or None,
                "price": round(float(raw_price) / price_divisor, 2),
                "image_url": (
                    f"https://media-assets.swiggy.com/swiggy/image/upload/{image_id}"
                    if image_id and platform == "swiggy"
                    else entry.get("imageUrl")
                ),
                "category": entry.get("category") or None,
            }
        )
    return items


async def fetch_menu_html(url: str) -> str:
    settings = get_settings()
    async with build_async_httpx_client(
        settings, timeout=30.0, follow_redirects=True
    ) as client:
        response = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (WarmOven menu sync bot)"},
        )
        response.raise_for_status()
        return response.text


async def sync_menu() -> int:
    async with async_session_factory() as session:
        config_repository = ConfigRepository(session)
        business_config = await config_repository.get()
        menu_url = business_config.menu_source_url
        await session.commit()

    platform = detect_platform(menu_url)
    html = await fetch_menu_html(menu_url)
    items = extract_items_from_page(html, platform)

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

    logger.info("menu_sync_complete", item_count=len(items), platform=platform)
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
