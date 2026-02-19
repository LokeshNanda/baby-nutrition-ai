"""LLM client abstract interface - OpenAI-compatible API."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """OpenAI-compatible LLM client interface."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send chat completion request and return assistant message content.
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        ...
