import httpx
import streamlit as st

from api_client import get_config, update_config

st.set_page_config(page_title="Configure — WarmOven", page_icon="⚙️", layout="centered")
st.title("⚙️ Configure WarmOven Assistant")
st.caption("Changes apply immediately to the next customer message.")

try:
    config = get_config()
except httpx.HTTPError as exc:
    st.error(f"Could not load current settings from the backend: {exc}")
    st.stop()

with st.form("business_config_form"):
    st.subheader("Menu source")
    menu_source_url = st.text_input(
        "Swiggy or Zomato menu link",
        value=config["menu_source_url"],
        help="The chatbot never scrapes live — re-run the menu sync after changing this.",
    )

    st.subheader("Delivery")
    col1, col2 = st.columns(2)
    with col1:
        min_cart_for_free_delivery = st.number_input(
            "Min cart value for free delivery (₹)",
            min_value=0.0,
            value=float(config["min_cart_for_free_delivery"]),
            step=50.0,
        )
        free_delivery_radius_km = st.number_input(
            "Free delivery radius (km)",
            min_value=0.0,
            value=float(config["free_delivery_radius_km"]),
            step=0.5,
        )
    with col2:
        delivery_time_minutes = st.number_input(
            "Delivery time (minutes)",
            min_value=1,
            value=int(config["delivery_time_minutes"]),
            step=15,
        )
        discount_percent = st.number_input(
            "Swiggy/Zomato flat discount (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(config["discount_percent"]),
            step=1.0,
        )

    st.subheader("Payment")
    col3, col4 = st.columns(2)
    with col3:
        payment_phone_number = st.text_input(
            "Payment phone number", value=config["payment_phone_number"]
        )
    with col4:
        payment_upi_id = st.text_input("Payment UPI ID", value=config["payment_upi_id"])

    st.subheader("Custom instructions")
    extra_instructions = st.text_area(
        "Extra instructions for the assistant",
        value=config.get("extra_instructions") or "",
        height=150,
        help=(
            "Freeform guidance the assistant should follow in addition to "
            "its core rules (e.g. seasonal promotions, temporary closures). "
            "It can never override safety rules like not promising refunds."
        ),
    )

    submitted = st.form_submit_button("Save settings", type="primary")

if submitted:
    payload = {
        "menu_source_url": menu_source_url,
        "min_cart_for_free_delivery": min_cart_for_free_delivery,
        "free_delivery_radius_km": free_delivery_radius_km,
        "delivery_time_minutes": int(delivery_time_minutes),
        "discount_percent": discount_percent,
        "payment_phone_number": payment_phone_number,
        "payment_upi_id": payment_upi_id,
        "extra_instructions": extra_instructions or None,
    }
    try:
        update_config(payload)
        st.success("Settings saved.")
    except httpx.HTTPError as exc:
        st.error(f"Could not save settings: {exc}")
