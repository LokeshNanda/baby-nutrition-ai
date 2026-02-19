"""Profile service - onboarding and profile management."""

import logging
from datetime import date, timedelta

from baby_nutrition_ai.models import BabyProfile, FeedingType, Preference
from baby_nutrition_ai.persistence import ProfileStore
from baby_nutrition_ai.rules import RuleEngine

logger = logging.getLogger(__name__)


class ProfileService:
    """Handles profile CRUD. Onboarding flow via WHATSAPP_FLOW.md."""

    def __init__(
        self,
        profile_store: ProfileStore,
        rule_engine: RuleEngine,
    ) -> None:
        self._store = profile_store
        self._rules = rule_engine

    def get_profile(
        self,
        phone: str,
        baby_id: str | None = None,
    ) -> BabyProfile | None:
        """Retrieve profile."""
        return self._store.get(phone, baby_id)

    def save_profile(
        self,
        profile: BabyProfile,
        phone: str,
    ) -> None:
        """Save or update profile."""
        self._store.save(profile, phone)

    def profile_to_message(self, profile: BabyProfile) -> str:
        """Format profile for WhatsApp - short, emoji-light."""
        age = profile.age_in_months()
        lines = [
            "*Baby Profile*",
            f"Name: {profile.baby_name or '-'}",
            f"Age: {age} months",
            f"Gender: {profile.gender or '-'}",
            f"Birth weight: {profile.birth_weight_kg or '-'} kg",
            f"Feeding: {profile.feeding_type.value}",
            f"Preferences: {', '.join(p.value for p in profile.preferences) or 'any'}",
            f"Allergies: {', '.join(profile.allergies) or 'none'}",
            f"Foods introduced: {', '.join(profile.foods_introduced[:8]) or 'none'}",
            f"Location: {profile.location or '-'}",
            "",
            self._rules.get_disclaimer(),
        ]
        return "\n".join(lines)

    def create_default_profile(self, phone: str, baby_id: str = "default") -> BabyProfile:
        """Create minimal profile for onboarding. User fills details later."""
        # Default 6 months old - typical starting solids age
        default_dob = date.today() - timedelta(days=180)
        profile = BabyProfile(
            baby_id=baby_id,
            dob=default_dob,
            feeding_type=FeedingType.MIXED,
            preferences=[Preference.VEG],
        )
        self._store.save(profile, phone)
        return profile


class OnboardingState:
    """Tracks onboarding conversation state. Stateless alternative: store in profile."""

    def __init__(self) -> None:
        self._states: dict[str, dict] = {}

    def get(self, phone: str) -> dict | None:
        return self._states.get(phone)

    def set(self, phone: str, state: dict) -> None:
        self._states[phone] = state

    def clear(self, phone: str) -> None:
        self._states.pop(phone, None)
