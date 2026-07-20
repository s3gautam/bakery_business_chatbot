from functools import lru_cache

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings, get_settings
from app.ssl_utils import build_async_httpx_client


class LLMService:
    """Thin wrapper around the Groq (OpenAI-compatible) chat completions API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            http_client=build_async_httpx_client(settings),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 800,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._settings.groq_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def complete_with_image(
        self,
        prompt: str,
        image_b64: str,
        image_mime_type: str = "image/png",
        temperature: float = 0.0,
        max_tokens: int = 500,
    ) -> str:
        """Vision-capable completion, used only for payment screenshot
        validation. Uses `groq_vision_model` rather than the text model.
        """
        response = await self._client.chat.completions.create(
            model=self._settings.groq_vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_mime_type};base64,{image_b64}"
                            },
                        },
                    ],
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService(get_settings())
