"""AI service - prompts from AI_PROMPTS.md. No hardcoded food items."""

import json
import logging
import re
from datetime import date
from typing import Any

from baby_nutrition_ai.llm.base import LLMClient
from baby_nutrition_ai.models import BabyProfile, Meal, MealPlan, Story
from baby_nutrition_ai.rules import RuleEngine

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a pediatric nutrition assistant following WHO and Indian Academy of Pediatrics complementary feeding guidelines.
You must never suggest unsafe foods or incorrect textures.
Never add salt, sugar, or honey for babies under 12 months.
Never suggest whole nuts for young children.
Do not give medical advice - only nutrition guidance.
Use simple Indian foods. Quantities in spoons. Output valid JSON when asked."""

MEAL_PLAN_USER_TEMPLATE = """Generate a daily meal plan (exactly 4 meals) for a baby.

Context:
- Age: {age_in_months} months
- Feeding type: {feeding_type}
- Preferences: {preferences}
- Allergies (AVOID these): {allergies}
- Foods already introduced (prioritise rotation): {foods_introduced}
- Location: {location}
- Current weight (kg): {current_weight_kg}

Rules (MUST follow):
- Use ONLY age-appropriate textures: {allowed_textures}
- Quantities in spoons (e.g. 2-3 spoons)
- Simple Indian foods
- 4 meals: breakfast, mid-morning, lunch, evening/dinner
- No salt, sugar, honey if under 12 months

Respond with ONLY a JSON object, no other text:
{{
  "meals": [
    {{"time": "07:00-09:00", "name": "breakfast", "item": "...", "quantity": "...", "texture": "..."}},
    ...
  ],
  "notes": "optional brief note"
}}

Output exactly 4 meals. Valid texture values: {allowed_textures}"""

STORY_USER_TEMPLATE = """Create a 60-90 second bedtime story suitable for a baby.
- Age bucket: {age_bucket}
- Language: {language}
- Use simple language, Indian context, gentle moral
- No scary elements
- Warm and soothing tone

Output ONLY the story text, nothing else."""


class AIService:
    """Orchestrates LLM calls with prompts. Rules applied by RuleEngine after generation."""

    def __init__(self, llm: LLMClient, rule_engine: RuleEngine) -> None:
        self._llm = llm
        self._rules = rule_engine

    async def generate_meal_plan(
        self,
        profile: BabyProfile,
        plan_date: date | None = None,
    ) -> MealPlan:
        """Generate 4-meal plan. Rule engine validates and filters output."""
        plan_date = plan_date or date.today()
        age = profile.age_in_months(plan_date)
        ctx = profile.to_ai_context()
        allowed = self._rules.allowed_textures(age)

        user_prompt = MEAL_PLAN_USER_TEMPLATE.format(
            age_in_months=ctx["age_in_months"],
            feeding_type=ctx["feeding_type"],
            preferences=", ".join(ctx["preferences"]) or "any",
            allergies=", ".join(ctx["allergies"]) or "none",
            foods_introduced=", ".join(ctx["foods_introduced"]) or "starting solids",
            location=ctx["location"] or "India",
            current_weight_kg=ctx["current_weight_kg"] or "not provided",
            allowed_textures=", ".join(allowed),
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        raw = await self._llm.chat(messages, max_tokens=1024)
        meals = self._parse_meal_plan_response(raw, profile)
        return MealPlan(
            plan_date=plan_date,
            age_in_months=age,
            meals=meals,
            notes=self._rules.get_disclaimer(),
        )

    def _parse_meal_plan_response(self, raw: str, profile: BabyProfile) -> list[Meal]:
        """Parse LLM JSON response. Apply rule engine filtering."""
        try:
            # Extract JSON block if wrapped in markdown
            json_str = raw.strip()
            if "```" in json_str:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", json_str)
                if match:
                    json_str = match.group(1).strip()
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse meal plan JSON: %s. Raw: %s", e, raw[:200])
            return []
        raw_meals = data.get("meals", [])
        meals: list[Meal] = []
        meal_times = [
            ("07:00-09:00", "breakfast"),
            ("10:00-11:00", "mid_morning"),
            ("12:00-14:00", "lunch"),
            ("16:00-18:00", "evening"),
        ]
        for i, m in enumerate(raw_meals[:4]):
            if isinstance(m, dict):
                time_slot, name = meal_times[i] if i < len(meal_times) else ("", "meal")
                meals.append(
                    Meal(
                        time=m.get("time", time_slot),
                        name=m.get("name", name),
                        item=str(m.get("item", "")).strip() or "Consult pediatrician",
                        quantity=str(m.get("quantity", "")).strip() or "-",
                        texture=str(m.get("texture", "")).strip() or "soft",
                        notes=m.get("notes"),
                    )
                )
        validated = self._rules.validate_and_filter_meals(profile, meals)
        return validated[:4]  # Exactly 4 meals

    async def generate_story(
        self,
        profile: BabyProfile,
        language: str = "en",
    ) -> Story:
        """Generate bedtime story. Rule engine provides age bucket."""
        age = profile.age_in_months()
        bucket = self._rules.age_bucket(age)
        user_prompt = STORY_USER_TEMPLATE.format(
            age_bucket=bucket,
            language=language,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        text = await self._llm.chat(messages, max_tokens=512)
        return Story(
            age_bucket=bucket,
            language=language,
            text=text.strip() or "Once upon a time, in a cozy home in India, a little baby went to sleep. The end.",
        )
