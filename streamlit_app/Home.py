import asyncio
import base64
import sys
import uuid
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent_factory import build_agent  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.store.config_store import ConfigStore  # noqa: E402

business_name = ConfigStore(get_settings()).load().business_name

st.set_page_config(page_title=f"{business_name} Assistant", page_icon="🍰", layout="centered")

# Keys carried across turns within a conversation — there is no database,
# so this session dict *is* the order state (see CLAUDE.md > Architecture).
_PERSISTENT_KEYS = ("cart", "customer_details", "delivery_slot", "payment_status", "order_id")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "order_state" not in st.session_state:
    st.session_state.order_state = {
        "cart": [],
        "customer_details": {},
        "delivery_slot": None,
        "payment_status": "none",
        "order_id": None,
    }
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

st.title(f"🍰 {business_name}")
st.caption(
    "Ask about our menu, flavours, or delivery — order right here in chat, "
    "or leave feedback on a past order."
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

payment_screenshot = None
if st.session_state.order_state.get("payment_status") in ("awaiting_screenshot", "failed"):
    payment_screenshot = st.file_uploader(
        "Upload your payment screenshot to confirm the order",
        type=["png", "jpg", "jpeg"],
        key=f"payment_uploader_{st.session_state.uploader_key}",
    )

user_input = st.chat_input("Type your message... (English, Hindi, or Hinglish)")

if user_input or payment_screenshot:
    display_text = user_input or "📎 Uploaded a payment screenshot"
    st.session_state.messages.append({"role": "user", "content": display_text})
    with st.chat_message("user"):
        st.markdown(display_text)

    turn_state = {
        **st.session_state.order_state,
        "conversation_id": st.session_state.conversation_id,
        "user_message": user_input or "I've uploaded my payment screenshot.",
        # Prior turns (excluding the one just appended above) so the NLU
        # layer can resolve references like "yes add 1".
        "history": st.session_state.messages[-9:-1],
    }
    if payment_screenshot is not None:
        image_bytes = payment_screenshot.getvalue()
        turn_state["payment_image_b64"] = base64.b64encode(image_bytes).decode("ascii")
        turn_state["payment_image_mime_type"] = payment_screenshot.type or "image/png"
        st.session_state.uploader_key += 1

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                agent = build_agent()
                result = asyncio.run(agent.ainvoke(turn_state))
                reply = result["reply"]
                st.session_state.order_state = {
                    key: result.get(key, st.session_state.order_state.get(key))
                    for key in _PERSISTENT_KEYS
                }
            except Exception as exc:
                reply = (
                    "Sorry, I'm having trouble reaching the kitchen right now. "
                    f"Please try again in a moment. ({exc})"
                )
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

with st.sidebar:
    st.subheader("Your order")
    cart = st.session_state.order_state.get("cart") or []
    if cart:
        for line in cart:
            st.text(f"{line['quantity']} x {line['name']}")
    else:
        st.caption("Cart is empty.")
    order_id = st.session_state.order_state.get("order_id")
    if order_id:
        st.success(f"Order confirmed: {order_id}")

    st.divider()
    st.subheader("Conversation")
    st.text(f"ID: {st.session_state.conversation_id[:8]}…")
    if st.button("Start a new conversation"):
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.order_state = {
            "cart": [],
            "customer_details": {},
            "delivery_slot": None,
            "payment_status": "none",
            "order_id": None,
        }
        st.session_state.uploader_key += 1
        st.rerun()

    st.divider()
    st.page_link("pages/2_🍰_Menu.py", label="View full menu", icon="🍰")
    st.page_link("pages/1_⚙️_Configure.py", label="Configure", icon="⚙️")
