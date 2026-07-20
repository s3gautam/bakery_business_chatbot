import pytest

from app.agent.graph import AgentDependencies, build_graph
from app.agent.nlu import NLUResult
from app.agent.tools.cart_tool import CartTool
from app.agent.tools.feedback_tool import FeedbackTool
from app.agent.tools.menu_tool import MenuTool
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


class _ScriptedNLUService:
    """Replays a fixed sequence of NLUResults, one per graph turn,
    instead of calling an LLM.
    """

    def __init__(self, results: list[NLUResult]) -> None:
        self._results = list(results)

    async def classify(self, message, business_config) -> NLUResult:
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


def _build(tmp_path, nlu_results: list[NLUResult]):
    settings = get_settings().model_copy(update={"menu_file_path": tmp_path / "menu.json"})
    menu_store = MenuStore(settings)
    menu_store.save_all([MenuItem("Chocolate Cake", None, 500.0, "Chocolate", None, True)])

    llm_service = _StubLLMService()
    deps = AgentDependencies(
        settings=settings,
        business_config=_business_config(),
        llm_service=llm_service,
        nlu_service=_ScriptedNLUService(nlu_results),
        language_service=LanguageDetectionService(llm_service),
        business_hours_service=BusinessHoursService(settings),
        menu_tool=MenuTool(menu_store),
        feedback_tool=FeedbackTool(
            email_service=None, admin_email="a@b.com", business_name="Test Bakery"
        ),
        cart_tool=CartTool(menu_store),
        payment_tool=PaymentTool(llm_service, settings, ocr_extract=lambda _: "some OCR text"),
    )
    return build_graph(deps)


@pytest.mark.asyncio
async def test_add_to_cart_updates_state(tmp_path):
    graph = _build(tmp_path, [_nlu("cart_add", cart_item_name="chocolate", cart_quantity=2)])
    result = await graph.ainvoke(
        {"conversation_id": "c1", "user_message": "add 2 chocolate cakes", "cart": []}
    )
    assert result["cart"] == [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 2}]


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
    graph = _build(tmp_path, [])
    cart = [{"name": "Chocolate Cake", "unit_price": 500.0, "quantity": 1}]
    result = await graph.ainvoke(
        {
            "conversation_id": "c1",
            "user_message": "here's my payment",
            "cart": cart,
            "customer_details": {
                "name": "Asha",
                "phone": "9999999999",
                "email": "a@b.com",
                "address": "123 Main St",
            },
            "delivery_slot": "2PM-3PM",
            "payment_image_b64": "ZmFrZQ==",
        }
    )
    assert result["payment_status"] == "validated"
    assert result["order_id"].startswith("TB-")
    assert result["cart"] == []


@pytest.mark.asyncio
async def test_custom_cake_request_routes_to_phone_template(tmp_path):
    graph = _build(tmp_path, [_nlu("custom_cake_request")])
    result = await graph.ainvoke(
        {"conversation_id": "c1", "user_message": "I need a custom 3-tier cake", "cart": []}
    )
    assert "7015943285" in result["reply"]
