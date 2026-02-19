"""Meal plan service - business logic layer."""

import logging
from datetime import date

from baby_nutrition_ai.models import BabyProfile, MealPlan
from baby_nutrition_ai.persistence import ProfileStore
from baby_nutrition_ai.rules import RuleEngine
from baby_nutrition_ai.services.ai_service import AIService

logger = logging.getLogger(__name__)


class MealPlanService:
    """Orchestrates meal plan generation. Separates transport from business logic."""

    def __init__(
        self,
        ai_service: AIService,
        profile_store: ProfileStore,
        rule_engine: RuleEngine,
    ) -> None:
        self._ai = ai_service
        self._store = profile_store
        self._rules = rule_engine

    async def get_today_plan(
        self,
        phone: str,
        baby_id: str | None = None,
    ) -> MealPlan | str:
        """
        Get today's meal plan for baby. Returns MealPlan or error message.
        """
        profile = self._store.get(phone, baby_id)
        if not profile:
            return (
                "No profile found. Send START to create your baby's profile first."
            )
        plan_date = date.today()
        try:
            plan = await self._ai.generate_meal_plan(profile, plan_date)
            return plan
        except Exception as e:
            logger.exception("Meal plan generation failed: %s", e)
            return f"Sorry, we couldn't generate your meal plan. {self._rules.get_disclaimer()}"
