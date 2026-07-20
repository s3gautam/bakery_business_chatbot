from pydantic import BaseModel, Field

from app.models.feedback import FeedbackPlatform


class FeedbackIn(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=64)
    order_id: str | None = Field(default=None, max_length=64)
    platform: FeedbackPlatform
    message: str = Field(min_length=1, max_length=4000)


class FeedbackOut(BaseModel):
    id: str
    message: str
