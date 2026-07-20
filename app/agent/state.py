from typing import Any, Literal, TypedDict

Intent = Literal[
    "menu_query",
    "feedback",
    "cart_add",
    "cart_remove",
    "cart_update",
    "cart_show",
    "cart_clear",
    "checkout",
    "provide_customer_details",
    "provide_delivery_slot",
    "custom_cake_request",
    "bulk_order_request",
    "general",
]


class CustomerDetails(TypedDict, total=False):
    name: str
    phone: str
    email: str
    address: str
    maps_link: str


class AgentState(TypedDict, total=False):
    conversation_id: str
    user_message: str
    payment_image_b64: str | None
    payment_image_mime_type: str | None
    detected_language: str
    intent: Intent | None
    history: list[dict[str, str]]
    tool_result: str | None
    reply: str | None
    nlu_result: Any  # app.agent.nlu.NLUResult | None (avoids a circular import)

    # Persisted across turns within a conversation (no database — see
    # streamlit_app/Home.py, which carries these keys in st.session_state).
    cart: list[dict]  # [{"name": str, "unit_price": float, "quantity": int}]
    customer_details: CustomerDetails
    delivery_slot: str | None
    payment_status: Literal["none", "awaiting_screenshot", "validated", "failed"]
    order_id: str | None
