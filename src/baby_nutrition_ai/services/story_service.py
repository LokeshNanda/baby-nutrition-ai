"""Story service - business logic layer."""

import logging

from baby_nutrition_ai.models import BabyProfile, Story
from baby_nutrition_ai.persistence import ProfileStore
from baby_nutrition_ai.rules import RuleEngine
from baby_nutrition_ai.services.ai_service import AIService

logger = logging.getLogger(__name__)


class StoryService:
    """Orchestrates bedtime story generation."""

    def __init__(
        self,
        ai_service: AIService,
        profile_store: ProfileStore,
        rule_engine: RuleEngine,
    ) -> None:
        self._ai = ai_service
        self._store = profile_store
        self._rules = rule_engine

    async def get_story(
        self,
        phone: str,
        baby_id: str | None = None,
        language: str = "en",
    ) -> Story | str:
        """Get bedtime story. Returns Story or error message."""
        profile = self._store.get(phone, baby_id)
        if not profile:
            return "No profile found. Send START to create your baby's profile first."
        try:
            return await self._ai.generate_story(profile, language)
        except Exception as e:
            logger.exception("Story generation failed: %s", e)
            return f"Sorry, we couldn't generate a story. {self._rules.get_disclaimer()}"
