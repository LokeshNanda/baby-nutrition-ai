"""OpenAI-compatible LLM client implementation."""

import json
import logging
from typing import Any, Awaitable, Callable

from baby_nutrition_ai.config import get_settings
from baby_nutrition_ai.llm.base import LLMClient

logger = logging.getLogger(__name__)

TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "get_meal_plan",
            "description": "Get today's age-appropriate meal plan (4 meals) for the baby.",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_story",
            "description": "Get a short bedtime story for the baby.",
        },
    },
]


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

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        execute_tool: Callable[[str, dict[str, Any]], str | Awaitable[str]],
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        max_iterations: int = 5,
    ) -> str:
        """
        Chat with tool calling. Loops until no tool calls or max_iterations.
        execute_tool(name, args) should return result string (or awaitable).
        """
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package required. pip install openai")

        client_kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        client = AsyncOpenAI(**client_kwargs)
        m = model or self._model

        current = list(messages)
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model=m,
                messages=current,
                tools=tools,
                tool_choice="auto",
                max_tokens=max_tokens,
            )
            msg = response.choices[0].message
            if msg.content:
                return (msg.content or "").strip()
            if not msg.tool_calls:
                return ""
            assistant_msg = {
                "role": "assistant",
                "content": msg.content or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                    }
                    for tc in msg.tool_calls
                ],
            }
            current.append(assistant_msg)
            for tc in msg.tool_calls:
                if tc.type != "function":
                    continue
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(name, args)
                if hasattr(result, "__await__"):
                    result = await result
                current.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
