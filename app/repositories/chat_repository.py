from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_history import ChatHistory, MessageRole


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        detected_language: str | None = None,
        intent: str | None = None,
    ) -> ChatHistory:
        message = ChatHistory(
            conversation_id=conversation_id,
            role=role,
            content=content,
            detected_language=detected_language,
            intent=intent,
        )
        self._session.add(message)
        await self._session.flush()
        return message

    async def recent_messages(
        self, conversation_id: str, limit: int = 20
    ) -> list[ChatHistory]:
        result = await self._session.execute(
            select(ChatHistory)
            .where(ChatHistory.conversation_id == conversation_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))
