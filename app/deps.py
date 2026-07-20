from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import AgentDependencies, build_graph
from app.agent.nlu import NLUService
from app.agent.tools.feedback_tool import FeedbackTool
from app.agent.tools.menu_tool import MenuTool
from app.config import get_settings
from app.db.session import get_session
from app.repositories.chat_repository import ChatRepository
from app.repositories.config_repository import ConfigRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.menu_repository import MenuRepository
from app.services.business_hours import BusinessHoursService
from app.services.language import LanguageDetectionService
from app.services.llm import get_llm_service


async def get_agent(session: AsyncSession) -> tuple:
    settings = get_settings()
    llm_service = get_llm_service()

    menu_repository = MenuRepository(session)
    feedback_repository = FeedbackRepository(session)
    chat_repository = ChatRepository(session)
    config_repository = ConfigRepository(session)

    business_config = await config_repository.get()

    deps = AgentDependencies(
        settings=settings,
        business_config=business_config,
        llm_service=llm_service,
        nlu_service=NLUService(llm_service),
        language_service=LanguageDetectionService(llm_service),
        business_hours_service=BusinessHoursService(settings),
        menu_tool=MenuTool(menu_repository),
        feedback_tool=FeedbackTool(feedback_repository),
    )
    graph = build_graph(deps)
    return graph, chat_repository


__all__ = ["get_agent", "get_session"]
