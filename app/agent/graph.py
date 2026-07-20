from dataclasses import dataclass
from datetime import datetime

from langgraph.graph import END, StateGraph

from app.agent.nlu import NLUResult, NLUService
from app.agent.prompts import build_reply_system_prompt
from app.agent.state import AgentState
from app.agent.tools.feedback_tool import FeedbackExtraction, FeedbackTool
from app.agent.tools.menu_tool import MenuTool
from app.config import Settings
from app.models.business_config import BusinessConfig
from app.services.business_hours import BusinessHoursService
from app.services.language import LanguageDetectionService
from app.services.llm import LLMService

_CUSTOM_CAKE_TEMPLATE = (
    "For custom cakes (custom design, message, size, or shape), please "
    "call us at {phone} and our team will help you directly."
)
_ORDER_TEMPLATE = (
    "I can't take orders directly just yet, but please call us at {phone} "
    "and we'll get your order sorted!"
)
_BULK_ORDER_TEMPLATE = (
    "For bulk or corporate orders, please call us at {phone} so our team "
    "can help with pricing and logistics."
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


def build_graph(deps: AgentDependencies):
    graph = StateGraph(AgentState)

    async def detect_language(state: AgentState) -> AgentState:
        language = await deps.language_service.detect(state["user_message"])
        return {"detected_language": language}

    async def classify_intent(state: AgentState) -> AgentState:
        result = await deps.nlu_service.classify(state["user_message"])
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

    async def handle_order_request(state: AgentState) -> AgentState:
        return {"reply": _ORDER_TEMPLATE.format(phone=deps.settings.order_phone_number)}

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

    async def generate_reply(state: AgentState) -> AgentState:
        if state.get("reply"):
            return {}

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
                f"Menu database results:\n{state['tool_result']}\n\n"
                f"Customer message: {state['user_message']}"
            )

        reply = await deps.llm_service.complete(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "system",
                    "content": f"Detected language: {state['detected_language']}",
                },
                {"role": "user", "content": user_content},
            ]
        )
        return {"reply": reply}

    def route_by_intent(state: AgentState) -> str:
        return state["intent"]

    graph.add_node("detect_language", detect_language)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("handle_menu_query", handle_menu_query)
    graph.add_node("handle_feedback", handle_feedback)
    graph.add_node("handle_order_request", handle_order_request)
    graph.add_node("handle_custom_cake_request", handle_custom_cake_request)
    graph.add_node("handle_bulk_order_request", handle_bulk_order_request)
    graph.add_node("generate_reply", generate_reply)

    graph.set_entry_point("detect_language")
    graph.add_edge("detect_language", "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "menu_query": "handle_menu_query",
            "feedback": "handle_feedback",
            "order_request": "handle_order_request",
            "custom_cake_request": "handle_custom_cake_request",
            "bulk_order_request": "handle_bulk_order_request",
            "general": "generate_reply",
        },
    )
    graph.add_edge("handle_menu_query", "generate_reply")
    graph.add_edge("handle_feedback", "generate_reply")
    graph.add_edge("handle_order_request", "generate_reply")
    graph.add_edge("handle_custom_cake_request", "generate_reply")
    graph.add_edge("handle_bulk_order_request", "generate_reply")
    graph.add_edge("generate_reply", END)

    return graph.compile()
