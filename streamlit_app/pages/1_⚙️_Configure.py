import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import get_settings  # noqa: E402
from app.store.config_store import ConfigStore  # noqa: E402

store = ConfigStore(get_settings())
config = store.load()

st.set_page_config(
    page_title=f"Configure — {config.business_name}", page_icon="⚙️", layout="centered"
)
st.title(f"⚙️ Configure {config.business_name} Assistant")
st.caption("Changes apply immediately to the next customer message.")

with st.form("business_config_form"):
    st.subheader("Business")
    business_name = st.text_input(
        "Business name",
        value=config.business_name,
        help="Shown to customers in the chat UI and used in the assistant's replies and emails.",
    )

    st.subheader("Menu source")
    menu_source_url = st.text_input(
        "Swiggy or Zomato menu link",
        value=config.menu_source_url,
        help="The chatbot never scrapes live — re-run the menu sync after changing this.",
    )

    st.subheader("Delivery")
    col1, col2 = st.columns(2)
    with col1:
        min_cart_for_free_delivery = st.number_input(
            "Min cart value for free delivery (₹)",
            min_value=0.0,
            value=float(config.min_cart_for_free_delivery),
            step=50.0,
        )
        free_delivery_radius_km = st.number_input(
            "Free delivery radius (km)",
            min_value=0.0,
            value=float(config.free_delivery_radius_km),
            step=0.5,
        )
    with col2:
        delivery_time_minutes = st.number_input(
            "Delivery time (minutes)",
            min_value=1,
            value=int(config.delivery_time_minutes),
            step=15,
        )
        discount_percent = st.number_input(
            "Swiggy/Zomato flat discount (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(config.discount_percent),
            step=1.0,
        )
    delivery_fee = st.number_input(
        "Delivery fee when order is below the free-delivery minimum (₹)",
        min_value=0.0,
        value=float(config.delivery_fee),
        step=5.0,
    )

    st.subheader("Payment")
    col3, col4 = st.columns(2)
    with col3:
        payment_phone_number = st.text_input(
            "Payment phone number", value=config.payment_phone_number
        )
    with col4:
        payment_upi_id = st.text_input("Payment UPI ID", value=config.payment_upi_id)

    accepted_receiver_names = st.text_input(
        "Accepted receiver names on payment screenshots (comma-separated)",
        value=config.accepted_receiver_names,
        help="Any one of these names appearing as the payment receiver is accepted.",
    )

    st.subheader("Custom instructions")
    extra_instructions = st.text_area(
        "Extra instructions for the assistant",
        value=config.extra_instructions or "",
        height=150,
        help=(
            "Freeform guidance the assistant should follow in addition to "
            "its core rules (e.g. seasonal promotions, temporary closures). "
            "It can never override safety rules like not promising refunds."
        ),
    )

    submitted = st.form_submit_button("Save settings", type="primary")

if submitted:
    store.update(
        business_name=business_name,
        menu_source_url=menu_source_url,
        min_cart_for_free_delivery=min_cart_for_free_delivery,
        free_delivery_radius_km=free_delivery_radius_km,
        delivery_time_minutes=int(delivery_time_minutes),
        discount_percent=discount_percent,
        delivery_fee=delivery_fee,
        payment_phone_number=payment_phone_number,
        payment_upi_id=payment_upi_id,
        accepted_receiver_names=accepted_receiver_names,
        extra_instructions=extra_instructions or None,
    )
    st.success("Settings saved.")
