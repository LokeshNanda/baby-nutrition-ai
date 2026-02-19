"""Baby profile data model."""

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FeedingType(str, Enum):
    """Infant feeding type."""

    BREASTFED = "breastfed"
    FORMULA = "formula"
    MIXED = "mixed"


class Preference(str, Enum):
    """Dietary preference."""

    VEG = "veg"
    EGG = "egg"
    NON_VEG = "non_veg"


class BabyProfile(BaseModel):
    """Baby profile per DATA_MODEL.md."""

    baby_id: str = Field(..., description="Unique baby identifier")
    dob: date = Field(..., description="Date of birth")
    gender: str | None = Field(default=None, description="Optional gender")
    birth_weight_kg: float | None = Field(default=None, description="Birth weight in kg")
    current_weight_kg: float | None = Field(default=None, description="Current weight in kg")
    height_cm: float | None = Field(default=None, description="Height in cm")
    feeding_type: FeedingType = Field(default=FeedingType.MIXED)
    preferences: list[Preference] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    foods_introduced: list[str] = Field(
        default_factory=list,
        description="Foods already introduced for rotation logic",
    )
    location: str | None = Field(default=None, description="City for regional context")

    def age_in_months(self, reference_date: date | None = None) -> int:
        """Compute age in months."""
        ref = reference_date or date.today()
        months = (ref.year - self.dob.year) * 12 + (ref.month - self.dob.month)
        if ref.day < self.dob.day:
            months -= 1
        return max(0, months)

    def to_ai_context(self) -> dict[str, Any]:
        """Context for AI prompts - no PII leakage."""
        return {
            "age_in_months": self.age_in_months(),
            "feeding_type": self.feeding_type.value,
            "preferences": [p.value for p in self.preferences],
            "allergies": self.allergies,
            "foods_introduced": self.foods_introduced,
            "location": self.location,
            "current_weight_kg": self.current_weight_kg,
            "birth_weight_kg": self.birth_weight_kg,
        }
