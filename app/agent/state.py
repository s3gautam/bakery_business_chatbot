from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from app.agent.nlu import NLUResult

Intent = Literal[
    "menu_query",
    "feedback",
    "order_request",
    "custom_cake_request",
    "bulk_order_request",
    "general",
]


class AgentState(TypedDict, total=False):
    conversation_id: str
    user_message: str
    detected_language: str
    intent: Intent
    history: list[dict[str, str]]
    tool_result: str | None
    reply: str
    nlu_result: "NLUResult"
