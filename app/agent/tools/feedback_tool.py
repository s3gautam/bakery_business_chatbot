from dataclasses import dataclass

from app.services.email_service import EmailService

APOLOGY_MESSAGE = "We're really sorry about your experience."
ESCALATION_MESSAGE = (
    "Please also raise this directly with {platform} support so they can "
    "action it on their end — we've logged it on our side too."
)
GENERIC_ESCALATION_MESSAGE = (
    "We've passed this on to our team so they can look into it."
)


@dataclass(frozen=True)
class FeedbackExtraction:
    order_id: str | None
    platform: str | None  # "swiggy" | "zomato" | "other"
    message: str | None


class FeedbackTool:
    """Agent tool: collects customer feedback and emails it to the
    admin inbox (there is no database — email is the durable record).
    Never promises refunds, cashback, or replacement, and never blames
    the customer.
    """

    def __init__(
        self, email_service: EmailService, admin_email: str, business_name: str
    ) -> None:
        self._email_service = email_service
        self._admin_email = admin_email
        self._business_name = business_name

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

        subject = f"{self._business_name} feedback — Order {extraction.order_id}"
        body = (
            f"Conversation ID: {conversation_id}\n"
            f"Order ID: {extraction.order_id}\n"
            f"Platform: {extraction.platform}\n\n"
            f"Feedback:\n{extraction.message}\n"
        )

        try:
            await self._email_service.send(self._admin_email, subject, body)
            escalation = ESCALATION_MESSAGE.format(platform=extraction.platform.capitalize())
        except Exception:
            escalation = GENERIC_ESCALATION_MESSAGE

        return f"{APOLOGY_MESSAGE} {escalation}"
