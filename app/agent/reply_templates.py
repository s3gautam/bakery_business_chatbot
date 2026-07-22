"""Deterministic, code-generated replies for cart/checkout/payment turns.

These are the highest-stakes turns in the conversation — they describe
real order state and real money. The LLM must never be allowed to
paraphrase or "helpfully" describe whether one of these succeeded,
because a paraphrase can drift from what actually happened (this is
exactly how the reported "bot claimed an item was added when it
wasn't" bug occurred). Instead, every possible tool_result for these
intents is mapped here to a fixed English template built entirely from
the tool_result string itself — no model call, no room to invent a
different outcome. Localization to Hindi/Hinglish happens afterwards as
a strict translate-only pass (see graph.py generate_reply), never as
open-ended generation.

`build_deterministic_reply` returns None for any tool_result it doesn't
recognize (e.g. menu search results), signalling the caller to fall
back to LLM-based reply generation for that turn.
"""

_CART_MESSAGE_PREFIXES = ("Added ", "Removed ", "Updated ", "Cart cleared.")


def _cart_mutation_reply(tool_result: str) -> str | None:
    if tool_result == "Cart cleared.":
        return "🧹 Cart cleared! Ready whenever you want to start a fresh order."
    if tool_result == "Quantity must be at least 1.":
        return f"🤔 {tool_result}"
    if tool_result.startswith("Added "):
        return f"✅ {tool_result} 🛒"
    if tool_result.startswith("Removed "):
        return f"🗑️ {tool_result}"
    if tool_result.startswith("Updated "):
        return f"✅ {tool_result}"
    if tool_result.endswith("isn't in your cart."):
        return f"🤔 {tool_result}"
    if tool_result.startswith("NO_MATCH: "):
        detail = tool_result[len("NO_MATCH: ") :]
        return f"😕 {detail} Please check the spelling or ask to see the menu."
    if tool_result.startswith("AMBIGUOUS: "):
        detail = tool_result[len("AMBIGUOUS: ") :]
        return f"🤔 {detail} Which one would you like?"
    return None


def _cart_swap_reply(tool_result: str) -> str | None:
    # SWAPPED\n<remove message>\n<add message> — built by handle_cart_swap.
    if tool_result.startswith("SWAPPED\n"):
        remove_message, add_message = tool_result[len("SWAPPED\n") :].split("\n", 1)
        return f"🔄 Got it — {remove_message.rstrip('.').lower()}, and ✅ {add_message} 🛒"
    # Falls back to plain cart_add/cart_remove-style outcomes (e.g. the
    # new item wasn't found, so nothing changed).
    return _cart_mutation_reply(tool_result)


def _cart_show_reply(tool_result: str) -> str:
    if tool_result == "EMPTY_CART":
        return "🛒 Your cart is empty. Want to see the menu and add something? 🍰"
    return f"🛒 Here's your cart:\n{tool_result}"


def _checkout_status_reply(tool_result: str) -> str:
    if tool_result == "EMPTY_CART":
        return "🛒 Your cart is empty — add something before checking out! Want to see the menu? 🍰"
    if tool_result.startswith("NEED_CUSTOMER_DETAILS: "):
        detail = tool_result[len("NEED_CUSTOMER_DETAILS: ") :]
        return f"📝 Almost there — {detail} Could you share that?"
    if tool_result.startswith("NEED_DELIVERY_SLOT: "):
        detail = tool_result[len("NEED_DELIVERY_SLOT: ") :]
        return f"🎉 Got your details! {detail} Which slot works for you? ⏰"
    if tool_result.startswith("READY_FOR_PAYMENT"):
        return "💳 " + tool_result[len("READY_FOR_PAYMENT") :].strip()
    raise ValueError(f"Unrecognized checkout status: {tool_result!r}")


def _delivery_slot_reply(tool_result: str) -> str:
    if tool_result.startswith("INVALID_SLOT: "):
        detail = tool_result[len("INVALID_SLOT: ") :]
        return f"⏰ I couldn't match that to a slot. {detail}"
    # A matched slot re-runs the same checkout-status logic.
    return _checkout_status_reply(tool_result)


def _payment_reply(tool_result: str) -> str:
    if tool_result == "NO_SCREENSHOT_PROVIDED":
        return "📸 I didn't receive a screenshot — please try uploading it again."
    if tool_result.startswith("PAYMENT_FAILED: "):
        reason = tool_result[len("PAYMENT_FAILED: ") :]
        return (
            f"❌ That payment couldn't be validated: {reason} "
            "Please upload a clear screenshot of a successful payment to us, "
            "and we'll check again."
        )
    if tool_result.startswith("PAYMENT_VALIDATED"):
        details = tool_result[len("PAYMENT_VALIDATED") :].strip()
        return f"✅🎉 Payment verified — your order is confirmed!\n{details}"
    raise ValueError(f"Unrecognized payment result: {tool_result!r}")


_BUILDERS = {
    "cart_add": _cart_mutation_reply,
    "cart_remove": _cart_mutation_reply,
    "cart_update": _cart_mutation_reply,
    "cart_swap": _cart_swap_reply,
    "cart_show": _cart_show_reply,
    "cart_clear": _cart_mutation_reply,
    "checkout": _checkout_status_reply,
    "provide_customer_details": _checkout_status_reply,
    "provide_delivery_slot": _delivery_slot_reply,
}


def build_deterministic_reply(intent: str, tool_result: str | None) -> str | None:
    """Returns a fully-formed English reply for cart/checkout/delivery-
    slot/payment intents, or None if this intent/tool_result isn't one
    of them (caller should fall back to LLM-based generation).
    """
    if tool_result is None:
        return None

    if intent in _BUILDERS:
        try:
            result = _BUILDERS[intent](tool_result)
        except ValueError:
            result = None
        if result is not None:
            return result

    if intent == "cart_add" and tool_result == "NO_ITEM_SPECIFIED":
        return "🍰 Sure — which item would you like to add?"
    if intent == "cart_remove" and tool_result == "NO_ITEM_SPECIFIED":
        return "🍰 Sure — which item would you like to remove?"
    if intent == "cart_update" and tool_result == "NO_ITEM_SPECIFIED":
        return "🍰 Sure — which item's quantity would you like to change?"
    if intent == "cart_swap" and tool_result == "NO_ITEM_SPECIFIED":
        return "🍰 Sure — which item would you like to swap, and for what?"

    if tool_result in ("NO_SCREENSHOT_PROVIDED",) or tool_result.startswith(
        ("PAYMENT_FAILED: ", "PAYMENT_VALIDATED")
    ):
        return _payment_reply(tool_result)

    return None
