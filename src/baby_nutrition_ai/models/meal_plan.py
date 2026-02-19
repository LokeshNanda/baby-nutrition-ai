"""Meal plan data model."""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class Meal(BaseModel):
    """Single meal in a plan."""

    time: str = Field(..., description="Meal time slot, e.g. 07:00-09:00")
    name: str = Field(..., description="Meal name, e.g. breakfast")
    item: str = Field(..., description="Food item description")
    quantity: str = Field(..., description="Quantity in spoons or similar")
    texture: str = Field(..., description="Age-appropriate texture")
    notes: str | None = Field(default=None)


class MealPlan(BaseModel):
    """Daily meal plan per DATA_MODEL.md."""

    plan_date: date = Field(..., description="Date of the meal plan")
    age_in_months: int = Field(...)
    meals: list[Meal] = Field(default_factory=list)
    notes: str | None = Field(default=None)

    def to_whatsapp_text(self) -> str:
        """Format for WhatsApp - short, emoji-light, copy-paste friendly."""
        lines = [f"*Meal Plan - {self.plan_date}*", ""]
        for m in self.meals:
            lines.append(f"*{m.name}* ({m.time})")
            lines.append(f"{m.item}")
            lines.append(f"  Qty: {m.quantity} | Texture: {m.texture}")
            if m.notes:
                lines.append(f"  {m.notes}")
            lines.append("")
        if self.notes:
            lines.append(f"_{self.notes}_")
        return "\n".join(lines).strip()
