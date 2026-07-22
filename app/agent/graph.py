from dataclasses import dataclass
from datetime import datetime

from langgraph.graph import END, StateGraph

from app.agent.nlu import NLUResult, NLUService
from app.agent.prompts import build_reply_system_prompt
from app.agent.reply_templates import build_deterministic_reply
from app.agent.state import AgentState, CustomerDetails
from app.agent.tools.cart_tool import CartTool, compute_totals, format_cart
from app.agent.tools.feedback_tool import FeedbackExtraction, FeedbackTool
from app.agent.tools.menu_tool import MenuTool
from app.agent.tools.order_confirmation_tool import OrderConfirmationTool
from app.agent.tools.order_tool import generate_order_id
from app.agent.tools.payment_tool import PaymentTool
from app.config import Settings
from app.services.business_hours import OFFLINE_MESSAGE, BusinessHoursService
from app.services.delivery_slots import generate_slots, match_slot
from app.services.language import LanguageDetectionService
from app.services.llm import LLMService
from app.store.models import BusinessConfig

_CUSTOM_CAKE_TEMPLATE = (
    "For custom cakes (custom design, message, size, or shape), please "
    "call us at {phone} and our team will help you directly."
)
_BULK_ORDER_TEMPLATE = (
    "For bulk or corporate orders, please call us at {phone} so our team "
    "can help with pricing and logistics."
)
_REQUIRED_CUSTOMER_FIELDS = ("name", "phone", "email", "address")

_LANGUAGE_NAMES = {"hi": "Hindi", "hinglish": "Hinglish (Hindi written in Latin script)"}

_TRANSLATE_SYSTEM_PROMPT = (
    "You are a translator, not an assistant. Translate the given message "
    "into {language}. Preserve every fact, number, name, and detail "
    "exactly as given — do not add, remove, guess, or change any "
    "information. Reply with only the translated text, nothing else."
)


async def _localize(llm_service: LLMService, text: str, language: str) -> str:
    """Translate a deterministically-built reply into the customer's
    language. This is a translate-only call (not open-ended generation)
    so it carries far less hallucination risk than describing what
    happened — the facts are already fixed by `text`.
    """
    target = _LANGUAGE_NAMES.get(language)
    if not target:
        return text
    return await llm_service.complete(
        messages=[
            {"role": "system", "content": _TRANSLATE_SYSTEM_PROMPT.format(language=target)},
            {"role": "user", "content": text},
        ],
        temperature=0.0,
    )


@dataclass
class AgentDependencies:
    settings: Settings
    business_config: BusinessConfig
    llm_service: LLMService
    nlu_service: NLUService
    language_service: LanguageDetectionService
    business_hours_service: BusinessHoursService
    menu_tool: MenuTool
    feedback_tool: FeedbackTool
    cart_tool: CartTool
    payment_tool: PaymentTool
    order_confirmation_tool: OrderConfirmationTool


def _missing_customer_fields(customer_details: CustomerDetails) -> list[str]:
    return [field for field in _REQUIRED_CUSTOMER_FIELDS if not customer_details.get(field)]


def _checkout_status(
    cart: list[dict],
    customer_details: CustomerDetails,
    delivery_slot: str | None,
    business_config: BusinessConfig,
) -> str:
    if not cart:
        return "EMPTY_CART"

    missing = _missing_customer_fields(customer_details)
    if missing:
        return f"NEED_CUSTOMER_DETAILS: still need {', '.join(missing)}."

    if not delivery_slot:
        slots = ", ".join(generate_slots(datetime.now()))
        return f"NEED_DELIVERY_SLOT: available slots are {slots}."

    totals = compute_totals(cart, business_config)
    cart_summary = format_cart(cart, business_config)
    receiver_name = business_config.accepted_receiver_names_list[0]
    return (
        "READY_FOR_PAYMENT\n"
        f"{cart_summary}\n"
        f"Delivery slot: {delivery_slot}\n"
        f"Pay Rs. {totals.total} in advance to phone "
        f"{business_config.payment_phone_number} or UPI "
        f"{business_config.payment_upi_id} (receiver name: {receiver_name}), "
        "then upload a screenshot of the payment."
    )


def build_graph(deps: AgentDependencies):
    graph = StateGraph(AgentState)

    async def detect_language(state: AgentState) -> AgentState:
        language = await deps.language_service.detect(state["user_message"])
        # Defensively clear per-turn fields in case a caller passed in a
        # previous turn's full result (only cart/customer_details/
        # delivery_slot/payment_status/order_id are meant to carry over
        # between turns — see streamlit_app/Home.py's _PERSISTENT_KEYS).
        return {
            "detected_language": language,
            "reply": None,
            "tool_result": None,
            "intent": None,
            "nlu_result": None,
        }

    async def classify_intent(state: AgentState) -> AgentState:
        result = await deps.nlu_service.classify(
            state["user_message"], deps.business_config, state.get("history")
        )
        return {"intent": result.intent, "nlu_result": result}

    async def handle_menu_query(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        search_query = nlu_result.search_query or state["user_message"]
        tool_result = await deps.menu_tool.search(search_query)
        return {"tool_result": tool_result}

    async def handle_feedback(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        extraction = FeedbackExtraction(
            order_id=nlu_result.order_id,
            platform=nlu_result.platform,
            message=nlu_result.feedback_message,
        )
        missing = deps.feedback_tool.missing_fields(extraction)
        if missing:
            return {
                "reply": (
                    "I'm sorry to hear that. Could you share your "
                    f"{', '.join(missing)} so I can log this for our team?"
                )
            }

        reply = await deps.feedback_tool.record(state["conversation_id"], extraction)
        return {"reply": reply}

    async def handle_custom_cake_request(state: AgentState) -> AgentState:
        return {
            "reply": _CUSTOM_CAKE_TEMPLATE.format(
                phone=deps.settings.custom_cake_phone_number
            )
        }

    async def handle_bulk_order_request(state: AgentState) -> AgentState:
        return {
            "reply": _BULK_ORDER_TEMPLATE.format(
                phone=deps.settings.bulk_order_phone_number
            )
        }

    async def handle_cart_add(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        cart = state.get("cart", [])
        if not nlu_result.cart_item_name:
            return {"tool_result": "NO_ITEM_SPECIFIED"}
        new_cart, message = deps.cart_tool.add(
            cart, nlu_result.cart_item_name, nlu_result.cart_quantity or 1
        )
        return {"cart": new_cart, "tool_result": message}

    async def handle_cart_remove(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        cart = state.get("cart", [])
        if not nlu_result.cart_item_name:
            return {"tool_result": "NO_ITEM_SPECIFIED"}
        new_cart, message = deps.cart_tool.remove(cart, nlu_result.cart_item_name)
        return {"cart": new_cart, "tool_result": message}

    async def handle_cart_update(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        cart = state.get("cart", [])
        if not nlu_result.cart_item_name:
            return {"tool_result": "NO_ITEM_SPECIFIED"}
        new_cart, message = deps.cart_tool.update_quantity(
            cart, nlu_result.cart_item_name, nlu_result.cart_quantity or 0
        )
        return {"cart": new_cart, "tool_result": message}

    async def handle_cart_show(state: AgentState) -> AgentState:
        cart = state.get("cart", [])
        return {"tool_result": deps.cart_tool.show(cart, deps.business_config)}

    async def handle_cart_clear(state: AgentState) -> AgentState:
        new_cart, message = deps.cart_tool.clear(state.get("cart", []))
        return {"cart": new_cart, "tool_result": message}

    async def handle_checkout(state: AgentState) -> AgentState:
        cart = state.get("cart", [])
        customer_details = state.get("customer_details", {})
        delivery_slot = state.get("delivery_slot")
        status = _checkout_status(cart, customer_details, delivery_slot, deps.business_config)
        updates: AgentState = {"tool_result": status}
        if status.startswith("READY_FOR_PAYMENT"):
            updates["payment_status"] = "awaiting_screenshot"
        return updates

    async def handle_customer_details(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        customer_details: CustomerDetails = dict(state.get("customer_details", {}))
        field_map = {
            "name": nlu_result.customer_name,
            "phone": nlu_result.customer_phone,
            "email": nlu_result.customer_email,
            "address": nlu_result.customer_address,
            "maps_link": nlu_result.maps_link,
        }
        for field, value in field_map.items():
            if value:
                customer_details[field] = value

        cart = state.get("cart", [])
        delivery_slot = state.get("delivery_slot")
        status = _checkout_status(cart, customer_details, delivery_slot, deps.business_config)
        updates: AgentState = {"customer_details": customer_details, "tool_result": status}
        if status.startswith("READY_FOR_PAYMENT"):
            updates["payment_status"] = "awaiting_screenshot"
        return updates

    async def handle_delivery_slot(state: AgentState) -> AgentState:
        nlu_result: NLUResult = state["nlu_result"]
        valid_slots = generate_slots(datetime.now())
        matched = (
            match_slot(nlu_result.delivery_slot_text, valid_slots)
            if nlu_result.delivery_slot_text
            else None
        )

        if not matched:
            return {"tool_result": f"INVALID_SLOT: available slots are {', '.join(valid_slots)}."}

        cart = state.get("cart", [])
        customer_details = state.get("customer_details", {})
        status = _checkout_status(cart, customer_details, matched, deps.business_config)
        updates: AgentState = {"delivery_slot": matched, "tool_result": status}
        if status.startswith("READY_FOR_PAYMENT"):
            updates["payment_status"] = "awaiting_screenshot"
        return updates

    async def handle_payment_screenshot(state: AgentState) -> AgentState:
        image_b64 = state.get("payment_image_b64")
        if not image_b64:
            return {"tool_result": "NO_SCREENSHOT_PROVIDED"}

        result = await deps.payment_tool.validate(
            image_b64,
            deps.business_config,
            state.get("payment_image_mime_type") or "image/png",
        )

        if not result.is_valid:
            return {
                "tool_result": f"PAYMENT_FAILED: {result.reason}",
                "payment_status": "failed",
            }

        cart = state.get("cart", [])
        customer_details = state.get("customer_details", {})
        delivery_slot = state.get("delivery_slot")
        order_id = generate_order_id(deps.business_config.business_name)
        totals = compute_totals(cart, deps.business_config)
        summary = (
            "PAYMENT_VALIDATED\n"
            f"Order ID: {order_id}\n"
            f"{format_cart(cart, deps.business_config)}\n"
            f"Delivery slot: {delivery_slot}\n"
            f"Delivery address: {customer_details.get('address')}\n"
            f"Total paid: Rs. {totals.total}"
        )

        try:
            await deps.order_confirmation_tool.send(
                order_id, cart, customer_details, delivery_slot, deps.business_config
            )
        except Exception:
            pass  # order is still valid — email delivery is best-effort (see tool docstring)

        return {
            "tool_result": summary,
            "payment_status": "validated",
            "order_id": order_id,
            "cart": [],
            "delivery_slot": None,
        }

    async def generate_reply(state: AgentState) -> AgentState:
        if state.get("reply"):
            return {}

        deterministic_reply = build_deterministic_reply(
            state.get("intent"), state.get("tool_result")
        )
        if deterministic_reply is not None:
            if not deps.business_hours_service.is_open(datetime.now()):
                deterministic_reply = f"{deterministic_reply}\n\n{OFFLINE_MESSAGE}"
            localized = await _localize(
                deps.llm_service, deterministic_reply, state.get("detected_language", "en")
            )
            return {"reply": localized}

        system_prompt = build_reply_system_prompt(deps.settings, deps.business_config)
        if not deps.business_hours_service.is_open(datetime.now()):
            system_prompt += (
                "\nThe bakery is currently outside business hours. Mention "
                "this politely: \"We are currently offline. You may still "
                "place an order and we'll process it during business "
                "hours.\""
            )

        user_content = state["user_message"]
        if state.get("tool_result"):
            user_content = (
                f"Tool result:\n{state['tool_result']}\n\n"
                f"Customer message: {state['user_message']}"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "system",
                "content": f"Detected language: {state['detected_language']}",
            },
        ]
        for turn in (state.get("history") or [])[-6:]:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_content})

        reply = await deps.llm_service.complete(messages=messages)
        return {"reply": reply}

    def route_after_language(state: AgentState) -> str:
        return "handle_payment_screenshot" if state.get("payment_image_b64") else "classify_intent"

    def route_by_intent(state: AgentState) -> str:
        return state["intent"]

    graph.add_node("detect_language", detect_language)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("handle_menu_query", handle_menu_query)
    graph.add_node("handle_feedback", handle_feedback)
    graph.add_node("handle_custom_cake_request", handle_custom_cake_request)
    graph.add_node("handle_bulk_order_request", handle_bulk_order_request)
    graph.add_node("handle_cart_add", handle_cart_add)
    graph.add_node("handle_cart_remove", handle_cart_remove)
    graph.add_node("handle_cart_update", handle_cart_update)
    graph.add_node("handle_cart_show", handle_cart_show)
    graph.add_node("handle_cart_clear", handle_cart_clear)
    graph.add_node("handle_checkout", handle_checkout)
    graph.add_node("handle_customer_details", handle_customer_details)
    graph.add_node("handle_delivery_slot", handle_delivery_slot)
    graph.add_node("handle_payment_screenshot", handle_payment_screenshot)
    graph.add_node("generate_reply", generate_reply)

    graph.set_entry_point("detect_language")
    graph.add_conditional_edges(
        "detect_language",
        route_after_language,
        {
            "handle_payment_screenshot": "handle_payment_screenshot",
            "classify_intent": "classify_intent",
        },
    )
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "menu_query": "handle_menu_query",
            "feedback": "handle_feedback",
            "cart_add": "handle_cart_add",
            "cart_remove": "handle_cart_remove",
            "cart_update": "handle_cart_update",
            "cart_show": "handle_cart_show",
            "cart_clear": "handle_cart_clear",
            "checkout": "handle_checkout",
            "provide_customer_details": "handle_customer_details",
            "provide_delivery_slot": "handle_delivery_slot",
            "custom_cake_request": "handle_custom_cake_request",
            "bulk_order_request": "handle_bulk_order_request",
            "general": "generate_reply",
        },
    )
    for node in (
        "handle_menu_query",
        "handle_feedback",
        "handle_custom_cake_request",
        "handle_bulk_order_request",
        "handle_cart_add",
        "handle_cart_remove",
        "handle_cart_update",
        "handle_cart_show",
        "handle_cart_clear",
        "handle_checkout",
        "handle_customer_details",
        "handle_delivery_slot",
        "handle_payment_screenshot",
    ):
        graph.add_edge(node, "generate_reply")
    graph.add_edge("generate_reply", END)

    return graph.compile()
