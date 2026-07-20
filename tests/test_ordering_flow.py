import pytest

from app.agent.graph import AgentDependencies, build_graph
from app.agent.nlu import NLUResult
from app.agent.tools.cart_tool import CartTool
from app.agent.tools.feedback_tool import FeedbackTool
from app.agent.tools.menu_tool import MenuTool
from app.agent.tools.order_confirmation_tool import OrderConfirmationTool
from app.agent.tools.payment_tool import PaymentTool
from app.config import get_settings
from app.services.business_hours import BusinessHoursService
from app.services.language import LanguageDetectionService
from app.store.menu_store import MenuStore
from app.store.models import BusinessConfig, MenuItem


class _StubLLMService:
    """Text completion always succeeds trivially, except for the
    payment-extraction call (identified by its prompt), which returns a
    fixed valid payment JSON payload.
    """

    async def complete(self, messages, **kwargs) -> str:
        if any("OCR text" in m.get("content", "") for m in messages):
            return (
                '{"receiver_name": "Test Bakery", "receiver_phone_or_upi": '
                '"7000000000", "amount": 500, "status": "success"}'
            )
        return "OK"


class _RecordingEmailService:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to_address: str, subject: str, body: str) -> None:
        self.sent.append((to_address, subject, body))


class _ScriptedNLUService:
    """Replays a fixed sequence of NLUResults, one per graph turn,
    instead of calling an LLM.
    """

    def __init__(self, results: list[NLUResult]) -> None:
        self._results = list(results)

    async def classify(self, message, business_config, history=None) -> NLUResult:
        return self._results.pop(0)


def _nlu(intent, **overrides) -> NLUResult:
    defaults = dict(
        intent=intent,
        search_query=None,
        order_id=None,
        platform=None,
        feedback_message=None,
        cart_item_name=None,
        cart_quantity=None,
        customer_name=None,
        customer_phone=None,
        customer_email=None,
        customer_address=None,
        maps_link=None,
        delivery_slot_text=None,
    )
    defaults.update(overrides)
    return NLUResult(**defaults)


def _business_config() -> BusinessConfig:
    return BusinessConfig(
        business_name="Test Bakery",
        menu_source_url="https://www.swiggy.com/x",
        min_cart_for_free_delivery=300.0,
        free_delivery_radius_km=7.0,
        delivery_time_minutes=120,
        discount_percent=25.0,
        payment_phone_number="7000000000",
        payment_upi_id="7000000000@paytm",
        delivery_fee=75.0,
        accepted_receiver_names="Test Bakery",
        extra_instructions=None,
    )


def _build(tmp_path, nlu_results: list[NLUResult], email_service=None):
    settings = get_settings().model_copy(update={"menu_file_path": tmp_path / "menu.json"})
    menu_store = MenuStore(settings)
    menu_store.save_all([MenuItem("Chocolate Cake", None, 500.0, "Chocolate", None, True)])

    llm_service = _StubLLMService()
    email_service = email_service or _RecordingEmailService()
    deps = AgentDependencies(
        settings=settings,
        business_config=_business_config(),
        llm_service=llm_service,
        nlu_service=_ScriptedNLUService(nlu_results),
        language_service=LanguageDetectionService(llm_service),
        business_hours_service=BusinessHoursService(settings),
        menu_tool=MenuTool(menu_store),
        feedback_tool=FeedbackTool(
            email_service=email_service, admin_email="a@b.com", business_name="Test Bakery"
        ),
        cart_tool=CartTool(menu_store),
        payment_tool=PaymentTool(llm_service, settings, ocr_extract=lambda _: "some OCR text"),
        order_confirmation_tool=OrderConfirmationTool(email_service, "admin@test.com"),
    )
    return build_graph(deps)


@pytest.mark.asyncio
async def test_add_to_cart_updates_state(tmp_path):
    graph = _build(tmp_path, [_nlu("cart_add", cart_item_name="chocolate", cart_quantity=2)])
    result = await graph.ainvoke(
        {"conversation_id": "c1", "user_message": "add 2 chocolate cakes", "cart": []}
    )
    assert result["cart"] == [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 2}]
    assert result["reply"] == "Added 2 x Chocolate Cake to your cart."


@pytest.mark.asyncio
async def test_cart_add_reply_never_claims_success_when_item_not_found(tmp_path):
    """Regression test: the bot must never say an item was added unless
    it actually was — this is what let it claim a nonexistent item was
    in the cart in the originally reported bug.
    """
    graph = _build(tmp_path, [_nlu("cart_add", cart_item_name="banana bread", cart_quantity=1)])
    result = await graph.ainvoke(
        {"conversation_id": "c1", "user_message": "add banana bread", "cart": []}
    )
    assert result["cart"] == []
    assert "Added" not in result["reply"]
    assert "banana bread" in result["reply"]


@pytest.mark.asyncio
async def test_checkout_with_empty_cart_reports_empty(tmp_path):
    graph = _build(tmp_path, [_nlu("checkout")])
    result = await graph.ainvoke({"conversation_id": "c1", "user_message": "checkout", "cart": []})
    assert result["tool_result"] == "EMPTY_CART"


@pytest.mark.asyncio
async def test_checkout_asks_for_missing_customer_details(tmp_path):
    graph = _build(tmp_path, [_nlu("checkout")])
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]
    result = await graph.ainvoke({"conversation_id": "c1", "user_message": "checkout", "cart": cart})
    assert result["tool_result"].startswith("NEED_CUSTOMER_DETAILS")


@pytest.mark.asyncio
async def test_full_flow_reaches_payment_ready_state(tmp_path):
    graph = _build(
        tmp_path,
        [
            _nlu(
                "provide_customer_details",
                customer_name="Asha",
                customer_phone="9999999999",
                customer_email="asha@example.com",
                customer_address="123 Main St",
            )
        ],
    )
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]
    result = await graph.ainvoke(
        {
            "conversation_id": "c1",
            "user_message": "Asha, 9999999999, asha@example.com, 123 Main St",
            "cart": cart,
            "customer_details": {},
        }
    )
    assert result["tool_result"].startswith("NEED_DELIVERY_SLOT")
    assert result["customer_details"]["name"] == "Asha"


@pytest.mark.asyncio
async def test_payment_screenshot_validates_and_generates_order_id(tmp_path):
    email_service = _RecordingEmailService()
    graph = _build(tmp_path, [], email_service=email_service)
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]
    result = await graph.ainvoke(
        {
            "conversation_id": "c1",
            "user_message": "here's my payment",
            "cart": cart,
            "customer_details": {
                "name": "Asha",
                "phone": "9999999999",
                "email": "asha@example.com",
                "address": "123 Main St",
            },
            "delivery_slot": "2PM-3PM",
            "payment_image_b64": "ZmFrZQ==",
        }
    )
    assert result["payment_status"] == "validated"
    assert result["order_id"].startswith("TB-")
    assert result["cart"] == []
    assert "confirmed" in result["reply"].lower()
    assert result["order_id"] in result["reply"]

    # Order confirmation email sent to both admin and customer
    recipients = [to for to, _, _ in email_service.sent]
    assert "admin@test.com" in recipients
    assert "asha@example.com" in recipients
    for _, subject, body in email_service.sent:
        assert result["order_id"] in subject
        assert "Chocolate Cake" in body
        assert "123 Main St" in body


@pytest.mark.asyncio
async def test_custom_cake_request_routes_to_phone_template(tmp_path):
    graph = _build(tmp_path, [_nlu("custom_cake_request")])
    result = await graph.ainvoke(
        {"conversation_id": "c1", "user_message": "I need a custom 3-tier cake", "cart": []}
    )
    assert "7015943285" in result["reply"]
