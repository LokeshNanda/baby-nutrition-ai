"""LLM abstraction - OpenAI-compatible."""

from baby_nutrition_ai.llm.base import LLMClient
from baby_nutrition_ai.llm.openai_client import OpenAIClient

__all__ = ["LLMClient", "OpenAIClient"]
