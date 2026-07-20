import asyncio
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.store.config_store import ConfigStore  # noqa: E402
from app.store.menu_store import MenuStore  # noqa: E402
from scraper.swiggy_scraper import MenuScrapeError, detect_platform, sync_menu  # noqa: E402

settings = get_settings()
config = ConfigStore(settings).load()
menu_store = MenuStore(settings)

st.set_page_config(page_title=f"Menu — {config.business_name}", page_icon="🍰", layout="centered")
st.title(f"🍰 {config.business_name} Menu")
st.caption(
    "The chatbot only ever answers from this list — it never scrapes live "
    "during a conversation. Sync it here whenever the source menu changes."
)

st.text(f"Source: {config.menu_source_url}")
st.text(f"Detected platform: {detect_platform(config.menu_source_url)}")

if st.button("🔄 Sync menu now", type="primary"):
    with st.spinner("Fetching and parsing the live menu page..."):
        try:
            count = asyncio.run(sync_menu())
            st.success(f"Synced {count} menu items.")
        except MenuScrapeError as exc:
            st.error(
                "Sync failed — the site's page structure may not match what "
                f"the scraper expects.\n\n**Error:** {exc}"
            )
        except Exception as exc:  # noqa: BLE001 — surface any failure to the admin
            st.error(f"Sync failed: {exc}")

st.divider()

items = menu_store.load_all()
if not items:
    st.info("No menu items yet. Click **Sync menu now** above to fetch them.")
else:
    st.subheader(f"Current menu ({len(items)} items)")
    st.dataframe(
        [
            {
                "Name": item.name,
                "Price (₹)": item.price,
                "Category": item.category or "",
                "Description": item.description or "",
                "Available": item.is_available,
            }
            for item in items
        ],
        use_container_width=True,
        hide_index=True,
    )
