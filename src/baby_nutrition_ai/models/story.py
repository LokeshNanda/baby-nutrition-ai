"""Bedtime story data model."""

from pydantic import BaseModel, Field


class Story(BaseModel):
    """Bedtime story per DATA_MODEL.md."""

    age_bucket: str = Field(..., description="e.g. 6-8 months")
    language: str = Field(default="en", description="Language code")
    text: str = Field(..., description="Story content, 60-90 sec read")

    def to_whatsapp_text(self) -> str:
        """Format for WhatsApp."""
        return f"*Bedtime Story* 🌙\n\n{self.text}"
