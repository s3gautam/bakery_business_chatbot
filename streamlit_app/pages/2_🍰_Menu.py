import asyncio
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.store.config_store import ConfigStore  # noqa: E402
from app.store.menu_store import MenuStore  # noqa: E402
from app.store.models import MenuItem  # noqa: E402
from scraper.swiggy_scraper import MenuScrapeError, detect_platform, sync_menu  # noqa: E402

_COLUMNS = ["Name", "Price (₹)", "Category", "Description", "Image URL", "Available"]

settings = get_settings()
config = ConfigStore(settings).load()
menu_store = MenuStore(settings)

st.set_page_config(page_title=f"Menu — {config.business_name}", page_icon="🍰", layout="centered")
st.title(f"🍰 {config.business_name} Menu")
st.caption(
    "The chatbot only ever answers from this list — it never scrapes live "
    "during a conversation. Sync it from Swiggy/Zomato, or add/edit/delete "
    "items directly in the table below."
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
st.subheader(f"Current menu ({len(items)} items)")
st.caption(
    "Edit cells directly, use the ⊕ row at the bottom to add an item, or "
    "select a row and press Delete to remove it. Click **Save menu changes** "
    "when done."
)

menu_df = pd.DataFrame(
    [
        {
            "Name": item.name,
            "Price (₹)": item.price,
            "Category": item.category or "",
            "Description": item.description or "",
            "Image URL": item.image_url or "",
            "Available": item.is_available,
        }
        for item in items
    ],
    columns=_COLUMNS,
)

edited_df = st.data_editor(
    menu_df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Name": st.column_config.TextColumn(required=True),
        "Price (₹)": st.column_config.NumberColumn(required=True, min_value=0.0, step=1.0),
        "Available": st.column_config.CheckboxColumn(default=True),
    },
    key="menu_editor",
)

if st.button("💾 Save menu changes", type="primary"):
    errors = []
    new_items = []
    seen_names = set()

    for i, row in enumerate(edited_df.to_dict("records"), start=1):
        name = str(row.get("Name") or "").strip()
        if not name:
            continue  # blank trailing row from the "add" affordance

        price = row.get("Price (₹)")
        if price is None or (isinstance(price, float) and pd.isna(price)):
            errors.append(f"Row {i} ('{name}'): price is required.")
            continue
        if price < 0:
            errors.append(f"Row {i} ('{name}'): price can't be negative.")
            continue

        if name.lower() in seen_names:
            errors.append(f"Duplicate item name: '{name}'.")
            continue
        seen_names.add(name.lower())

        new_items.append(
            MenuItem(
                name=name,
                description=(str(row.get("Description")).strip() or None)
                if row.get("Description")
                else None,
                price=float(price),
                category=(str(row.get("Category")).strip() or None)
                if row.get("Category")
                else None,
                image_url=(str(row.get("Image URL")).strip() or None)
                if row.get("Image URL")
                else None,
                is_available=bool(row.get("Available", True)),
            )
        )

    if errors:
        for error in errors:
            st.error(error)
    else:
        menu_store.save_all(new_items)
        st.success(f"Saved {len(new_items)} menu items.")
        st.rerun()
