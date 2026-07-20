from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.feedback_repository import FeedbackRepository
from app.schemas.feedback import FeedbackIn, FeedbackOut

router = APIRouter()


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    payload: FeedbackIn, session: AsyncSession = Depends(get_session)
) -> FeedbackOut:
    repository = FeedbackRepository(session)
    feedback = await repository.create(
        conversation_id=payload.conversation_id,
        platform=payload.platform,
        message=payload.message,
        order_id=payload.order_id,
    )
    await session.commit()
    return FeedbackOut(id=str(feedback.id), message="Feedback recorded. Thank you.")
