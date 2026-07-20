from app.agent.reply_templates import build_deterministic_reply


def test_returns_none_for_menu_query():
    assert build_deterministic_reply("menu_query", "- Chocolate Cake: Rs. 500") is None


def test_returns_none_when_no_tool_result():
    assert build_deterministic_reply("cart_add", None) is None


def test_cart_add_success_passthrough():
    reply = build_deterministic_reply("cart_add", "Added 2 x Chocolate Cake to your cart.")
    assert reply == "Added 2 x Chocolate Cake to your cart."


def test_cart_add_no_match_never_claims_success():
    reply = build_deterministic_reply(
        "cart_add", "NO_MATCH: 'banana bread' is not on the menu."
    )
    assert "banana bread" in reply
    assert "not on the menu" in reply
    assert "Added" not in reply


def test_cart_add_ambiguous_asks_to_clarify():
    reply = build_deterministic_reply(
        "cart_add", "AMBIGUOUS: multiple items match 'cake': Chocolate Cake, Vanilla Cake"
    )
    assert "Chocolate Cake, Vanilla Cake" in reply
    assert "Which one" in reply


def test_cart_add_no_item_specified_asks_which_item():
    reply = build_deterministic_reply("cart_add", "NO_ITEM_SPECIFIED")
    assert "which item" in reply.lower()
    assert "add" in reply.lower()


def test_cart_show_empty():
    reply = build_deterministic_reply("cart_show", "EMPTY_CART")
    assert "empty" in reply.lower()


def test_cart_show_with_items():
    reply = build_deterministic_reply("cart_show", "- 1 x Chocolate Cake @ Rs. 500")
    assert "Chocolate Cake" in reply


def test_checkout_empty_cart():
    reply = build_deterministic_reply("checkout", "EMPTY_CART")
    assert "empty" in reply.lower()


def test_checkout_need_customer_details():
    reply = build_deterministic_reply(
        "checkout", "NEED_CUSTOMER_DETAILS: still need phone, email."
    )
    assert "phone, email" in reply


def test_checkout_ready_for_payment_strips_sentinel():
    reply = build_deterministic_reply(
        "checkout", "READY_FOR_PAYMENT\nSubtotal: Rs. 500\nPay Rs. 500 to 999999"
    )
    assert not reply.startswith("READY_FOR_PAYMENT")
    assert "Pay Rs. 500 to 999999" in reply


def test_delivery_slot_invalid():
    reply = build_deterministic_reply(
        "provide_delivery_slot", "INVALID_SLOT: available slots are 2PM-3PM, 3PM-4PM."
    )
    assert "2PM-3PM" in reply


def test_payment_failed_never_claims_success():
    reply = build_deterministic_reply(
        "provide_delivery_slot", "PAYMENT_FAILED: receiver name doesn't match."
    )
    assert "couldn't be validated" in reply
    assert "confirmed" not in reply.lower()


def test_payment_validated_confirms_order():
    reply = build_deterministic_reply(
        None, "PAYMENT_VALIDATED\nOrder ID: TB-ABC123\nTotal paid: Rs. 500"
    )
    assert "confirmed" in reply.lower()
    assert "TB-ABC123" in reply


def test_no_screenshot_provided():
    reply = build_deterministic_reply(None, "NO_SCREENSHOT_PROVIDED")
    assert "screenshot" in reply.lower()
