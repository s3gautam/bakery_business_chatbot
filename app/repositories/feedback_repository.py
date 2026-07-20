from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback, FeedbackPlatform


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        conversation_id: str,
        platform: FeedbackPlatform,
        message: str,
        order_id: str | None = None,
    ) -> Feedback:
        feedback = Feedback(
            conversation_id=conversation_id,
            platform=platform,
            message=message,
            order_id=order_id,
        )
        self._session.add(feedback)
        await self._session.flush()
        return feedback
