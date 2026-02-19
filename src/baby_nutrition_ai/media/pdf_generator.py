"""PDF generator stub - for monthly meal plan PDF."""

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from baby_nutrition_ai.models import BabyProfile

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Stub for generating monthly meal plan PDF. To be implemented."""

    async def generate_monthly_pdf(
        self,
        profile: "BabyProfile",
        month: date,
    ) -> Path | None:
        """
        Generate PDF for the month's meal plans.
        Returns path to generated file or None if not implemented.
        """
        logger.info(
            "PDFGenerator stub: generate_monthly_pdf not implemented for %s",
            month,
        )
        return None
