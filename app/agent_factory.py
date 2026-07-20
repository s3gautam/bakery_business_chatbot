from app.agent.graph import AgentDependencies, build_graph
from app.agent.nlu import NLUService
from app.agent.tools.cart_tool import CartTool
from app.agent.tools.feedback_tool import FeedbackTool
from app.agent.tools.menu_tool import MenuTool
from app.agent.tools.payment_tool import PaymentTool
from app.config import get_settings
from app.services.business_hours import BusinessHoursService
from app.services.email_service import EmailService
from app.services.language import LanguageDetectionService
from app.services.llm import get_llm_service
from app.store.config_store import ConfigStore
from app.store.menu_store import MenuStore


def build_agent():
    """Build a fresh compiled agent graph. Called once per Streamlit
    chat turn — reads the current menu/config files each time so admin
    changes on the Configure page take effect immediately.
    """
    settings = get_settings()
    llm_service = get_llm_service()

    menu_store = MenuStore(settings)
    config_store = ConfigStore(settings)
    email_service = EmailService(settings)

    business_config = config_store.load()

    deps = AgentDependencies(
        settings=settings,
        business_config=business_config,
        llm_service=llm_service,
        nlu_service=NLUService(llm_service),
        language_service=LanguageDetectionService(llm_service),
        business_hours_service=BusinessHoursService(settings),
        menu_tool=MenuTool(menu_store),
        feedback_tool=FeedbackTool(
            email_service, settings.feedback_email_to, business_config.business_name
        ),
        cart_tool=CartTool(menu_store),
        payment_tool=PaymentTool(llm_service),
    )
    return build_graph(deps)
