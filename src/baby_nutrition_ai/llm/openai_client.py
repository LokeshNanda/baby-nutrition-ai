"""OpenAI-compatible LLM client implementation."""

import logging
from typing import Any

from baby_nutrition_ai.config import get_settings
from baby_nutrition_ai.llm.base import LLMClient

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    """OpenAI API client - works with OpenAI or compatible endpoints (e.g. LiteLLM)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.llm_api_key
        self._base_url = base_url or settings.llm_base_url
        self._model = model or settings.llm_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Call OpenAI-compatible chat completion."""
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required. pip install openai")

        client_kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url

        client = AsyncOpenAI(**client_kwargs)
        m = model or self._model

        response = await client.chat.completions.create(
            model=m,
            messages=messages,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""
