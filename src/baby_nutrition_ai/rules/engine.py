"""Rule engine for age, texture, and food safety. Rules override AI output."""

import logging
from dataclasses import dataclass
from typing import Any

from baby_nutrition_ai.config import get_food_rules
from baby_nutrition_ai.models import BabyProfile, Meal, MealPlan

logger = logging.getLogger(__name__)

# Must never appear in AI output
FORBIDDEN_ITEMS_BEFORE_12M = {"salt", "sugar", "honey", "jaggery", "gur"}
FORBIDDEN_WHOLE_NUTS = {"whole nuts", "whole peanuts", "whole almonds", "whole cashews"}


@dataclass
class RuleContext:
    """Context passed to rules."""

    age_months: int
    allergies: list[str]
    preferences: list[str]


class RuleEngine:
    """Enforces WHO and IAP guidelines. Rules first, AI second."""

    def __init__(self) -> None:
        self._rules = get_food_rules()

    def age_bucket(self, age_months: int) -> str:
        """Get texture bucket name for age."""
        buckets = self._rules.get("age_buckets", [])
        for b in buckets:
            if b.get("min_months", 0) <= age_months < b.get("max_months", 999):
                return b.get("name", "12+")
        return "12+"

    def allowed_textures(self, age_months: int) -> list[str]:
        """Get allowed textures for age from config."""
        bucket = self.age_bucket(age_months)
        texture_map = self._rules.get("texture_by_age_months", {})
        return texture_map.get(bucket, ["family_food", "varied"])

    def validate_and_filter_meals(
        self,
        profile: BabyProfile,
        meals: list[Meal],
    ) -> list[Meal]:
        """
        Validate AI output against rules. Remove or adjust non-compliant items.
        """
        age = profile.age_in_months()
        allergies_lower = {a.lower() for a in profile.allergies}
        bucket = self.age_bucket(age)
        allowed_textures = set(self.allowed_textures(age))

        safe: list[Meal] = []
        no_salt_sugar = age < self._rules.get("safety", {}).get(
            "no_salt_sugar_until_months", 12
        )
        no_honey = age < self._rules.get("safety", {}).get(
            "no_honey_until_months", 12
        )
        no_whole_nuts = age < self._rules.get("safety", {}).get(
            "no_whole_nuts_until_months", 60
        )

        for m in meals:
            item_lower = m.item.lower()

            # Allergen check
            if any(a in item_lower for a in allergies_lower):
                logger.info("Filtered meal due to allergy: %s", m.item)
                continue

            # Forbidden items < 12 months
            if no_salt_sugar and any(f in item_lower for f in FORBIDDEN_ITEMS_BEFORE_12M):
                logger.info("Filtered meal: salt/sugar/honey before 12m: %s", m.item)
                continue
            if no_honey and "honey" in item_lower:
                logger.info("Filtered meal: honey before 12m: %s", m.item)
                continue
            if no_whole_nuts and any(n in item_lower for n in FORBIDDEN_WHOLE_NUTS):
                logger.info("Filtered meal: whole nuts before age: %s", m.item)
                continue

            # Texture: if AI gave invalid texture, override to first allowed
            if allowed_textures and m.texture.lower() not in {
                t.lower() for t in allowed_textures
            }:
                m = Meal(
                    time=m.time,
                    name=m.name,
                    item=m.item,
                    quantity=m.quantity,
                    texture=allowed_textures[0] if allowed_textures else m.texture,
                    notes=(m.notes or "") + " (texture adjusted per guidelines)",
                )

            safe.append(m)
        return safe

    def rule_context(self, profile: BabyProfile) -> RuleContext:
        """Build context for AI prompts."""
        return RuleContext(
            age_months=profile.age_in_months(),
            allergies=profile.allergies,
            preferences=[p.value for p in profile.preferences],
        )

    def get_disclaimer(self) -> str:
        """Safety disclaimer from config."""
        return self._rules.get("disclaimer", "")
