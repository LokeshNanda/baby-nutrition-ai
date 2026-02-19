"""Image generator stub - for meal plan PNG output."""

import logging
from pathlib import Path

from baby_nutrition_ai.models import MealPlan

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Stub for generating meal plan as PNG image. To be implemented."""

    async def generate_meal_plan_image(self, plan: MealPlan) -> Path | None:
        """
        Generate PNG image of meal plan.
        Returns path to generated file or None if not implemented.
        """
        logger.info("ImageGenerator stub: generate_meal_plan_image not implemented")
        return None
