from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_agent
from app.db.session import get_session
from app.models.chat_history import MessageRole
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest, session: AsyncSession = Depends(get_session)
) -> ChatResponse:
    graph, chat_repository = await get_agent(session)

    await chat_repository.add_message(
        conversation_id=payload.conversation_id,
        role=MessageRole.USER,
        content=payload.message,
    )

    result = await graph.ainvoke(
        {
            "conversation_id": payload.conversation_id,
            "user_message": payload.message,
        }
    )

    await chat_repository.add_message(
        conversation_id=payload.conversation_id,
        role=MessageRole.ASSISTANT,
        content=result["reply"],
        detected_language=result.get("detected_language"),
        intent=result.get("intent"),
    )
    await session.commit()

    return ChatResponse(
        conversation_id=payload.conversation_id,
        reply=result["reply"],
        detected_language=result["detected_language"],
        intent=result["intent"],
    )
