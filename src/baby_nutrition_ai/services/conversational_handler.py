"""Conversational handler - natural language routing via LLM tool-calling."""

import logging
from typing import Any

from baby_nutrition_ai.llm import OpenAIClient
from baby_nutrition_ai.llm.openai_client import TOOLS_DEFINITION
from baby_nutrition_ai.persistence import ConversationStore, ProfileStore
from baby_nutrition_ai.services.meal_plan_service import MealPlanService
from baby_nutrition_ai.services.story_service import StoryService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a friendly pediatric nutrition assistant for parents. Follow WHO and Indian Academy of Pediatrics guidelines.
You have access to tools: get_meal_plan (today's 4 meals) and get_story (bedtime story). Use them when the user asks for meals or a story.
For general questions about feeding, textures, food safety, answer briefly. Never give medical advice - say "Consult your pediatrician for medical concerns."
Keep responses short and WhatsApp-friendly (no long paragraphs).

Baby profile context:
{profile_context}
"""

NO_PROFILE_CONTEXT = "No profile yet. If user asks for meal plan or story, the tool will return a message asking them to send START first."


class ConversationalHandler:
    """Handles non-command messages via LLM with tool-calling."""

    def __init__(
        self,
        llm: OpenAIClient,
        meal_plan_service: MealPlanService,
        story_service: StoryService,
        profile_store: ProfileStore,
        conversation_store: ConversationStore,
    ) -> None:
        self._llm = llm
        self._meal_plan = meal_plan_service
        self._story = story_service
        self._profile_store = profile_store
        self._conversation = conversation_store

    def _profile_context(self, phone: str) -> str:
        """Build profile summary for prompt."""
        profile = self._profile_store.get(phone)
        if not profile:
            return NO_PROFILE_CONTEXT
        ctx = profile.to_ai_context()
        return (
            f"Age: {ctx['age_in_months']} months. "
            f"Feeding: {ctx['feeding_type']}. "
            f"Preferences: {ctx['preferences']}. "
            f"Allergies: {ctx['allergies']}. "
            f"Foods introduced: {ctx['foods_introduced']}. "
            f"Location: {ctx['location'] or 'not set'}."
        )

    async def handle(self, phone: str, user_message: str) -> str:
        """
        Process user message conversationally. Uses LLM with tools.
        Returns response string.
        """
        profile_ctx = self._profile_context(phone)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(profile_context=profile_ctx)
        history = self._conversation.get(phone)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        async def execute_tool(name: str, args: dict[str, Any]) -> str:
            if name == "get_meal_plan":
                result = await self._meal_plan.get_today_plan(phone)
                if hasattr(result, "to_whatsapp_text"):
                    return result.to_whatsapp_text()
                return str(result)
            if name == "get_story":
                result = await self._story.get_story(phone)
                if hasattr(result, "to_whatsapp_text"):
                    return result.to_whatsapp_text()
                return str(result)
            return f"Unknown tool: {name}"

        try:
            response = await self._llm.chat_with_tools(
                messages=messages,
                tools=TOOLS_DEFINITION,
                execute_tool=execute_tool,
                max_tokens=1024,
            )
        except Exception as e:
            logger.exception("Conversational handler failed: %s", e)
            return (
                "Sorry, I couldn't process that. "
                "Try commands: START, PROFILE, TODAY, STORY."
            )

        if not response:
            return "I'm not sure how to help with that. Try: TODAY for meals, STORY for a bedtime story."

        self._conversation.append(phone, "user", user_message)
        self._conversation.append(phone, "assistant", response)
        return response
