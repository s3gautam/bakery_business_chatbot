from dataclasses import dataclass

from app.models.feedback import FeedbackPlatform
from app.repositories.feedback_repository import FeedbackRepository

APOLOGY_MESSAGE = "We're really sorry about your experience."
ESCALATION_MESSAGE = (
    "Please also raise this directly with {platform} support so they can "
    "action it on their end — we've logged it on our side too."
)


@dataclass(frozen=True)
class FeedbackExtraction:
    order_id: str | None
    platform: FeedbackPlatform | None
    message: str | None


class FeedbackTool:
    """Agent tool: collects and stores customer feedback. Never promises
    refunds, cashback, or replacement, and never blames the customer.
    """

    def __init__(self, repository: FeedbackRepository) -> None:
        self._repository = repository

    def missing_fields(self, extraction: FeedbackExtraction) -> list[str]:
        missing = []
        if not extraction.order_id:
            missing.append("order_id")
        if extraction.platform is None:
            missing.append("platform (Swiggy or Zomato)")
        if not extraction.message:
            missing.append("feedback")
        return missing

    async def record(self, conversation_id: str, extraction: FeedbackExtraction) -> str:
        if self.missing_fields(extraction):
            raise ValueError("Cannot record feedback with missing required fields.")

        assert extraction.order_id is not None
        assert extraction.platform is not None
        assert extraction.message is not None

        await self._repository.create(
            conversation_id=conversation_id,
            platform=extraction.platform,
            message=extraction.message,
            order_id=extraction.order_id,
        )

        platform_label = extraction.platform.value.capitalize()
        return f"{APOLOGY_MESSAGE} {ESCALATION_MESSAGE.format(platform=platform_label)}"
