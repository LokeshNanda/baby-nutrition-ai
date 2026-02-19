"""Profile update flow - interactive WhatsApp conversation for updating baby profile."""

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from baby_nutrition_ai.models import BabyProfile, FeedingType, Preference

logger = logging.getLogger(__name__)

# Field keys for update flow
FIELD_DOB = "dob"
FIELD_FEEDING = "feeding"
FIELD_PREFERENCES = "preferences"
FIELD_ALLERGIES = "allergies"
FIELD_FOODS = "foods"
FIELD_LOCATION = "location"
FIELD_WEIGHT = "weight"
FIELD_HEIGHT = "height"

UPDATE_MENU = (
    "Reply with a number:\n"
    "1. Date of birth\n"
    "2. Feeding type\n"
    "3. Diet preferences\n"
    "4. Allergies\n"
    "5. Foods introduced\n"
    "6. Location\n"
    "7. Current weight (kg)\n"
    "8. Height (cm)\n"
    "0. Done"
)

FIELD_MAP = {
    "1": FIELD_DOB,
    "2": FIELD_FEEDING,
    "3": FIELD_PREFERENCES,
    "4": FIELD_ALLERGIES,
    "5": FIELD_FOODS,
    "6": FIELD_LOCATION,
    "7": FIELD_WEIGHT,
    "8": FIELD_HEIGHT,
    "0": None,
}


@dataclass
class FlowState:
    """State for a user in the update flow."""

    step: str  # "menu" | "awaiting"
    field_key: str | None
    profile: BabyProfile


def get_field_prompt(field_key: str) -> str:
    """Prompt for entering a specific field value."""
    prompts = {
        FIELD_DOB: "Enter date of birth (YYYY-MM-DD):",
        FIELD_FEEDING: "Enter feeding type: breastfed, formula, or mixed",
        FIELD_PREFERENCES: "Enter diet: veg, egg, non_veg (comma-separated for multiple)",
        FIELD_ALLERGIES: "Enter allergies (comma-separated) or 'none':",
        FIELD_FOODS: "Enter foods already introduced (comma-separated):",
        FIELD_LOCATION: "Enter city/location:",
        FIELD_WEIGHT: "Enter current weight in kg (e.g. 7.5):",
        FIELD_HEIGHT: "Enter height in cm (e.g. 68):",
    }
    return prompts.get(field_key, "Enter value:")


def parse_and_apply(
    profile: BabyProfile,
    field_key: str,
    value: str,
) -> tuple[BabyProfile, bool, str]:
    """
    Parse user input and apply to profile.
    Returns (updated_profile, success, error_message).
    """
    value = value.strip()
    if not value or value.lower() in ("skip", "-", "—"):
        return profile, True, "Skipped"

    if field_key == FIELD_DOB:
        match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
        if match:
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                dob = date(y, m, d)
                if dob > date.today():
                    return profile, False, "Date cannot be in the future"
                return profile.model_copy(update={"dob": dob}), True, "Updated"
            except ValueError:
                return profile, False, "Invalid date"
        return profile, False, "Use YYYY-MM-DD (e.g. 2024-05-15)"

    if field_key == FIELD_FEEDING:
        v = value.lower()
        if v in ("breastfed", "breast", "bf"):
            return profile.model_copy(update={"feeding_type": FeedingType.BREASTFED}), True, "Updated"
        if v in ("formula", "formula-fed"):
            return profile.model_copy(update={"feeding_type": FeedingType.FORMULA}), True, "Updated"
        if v in ("mixed", "both"):
            return profile.model_copy(update={"feeding_type": FeedingType.MIXED}), True, "Updated"
        return profile, False, "Use: breastfed, formula, or mixed"

    if field_key == FIELD_PREFERENCES:
        prefs: list[Preference] = []
        for p in re.split(r"[,.\s]+", value.lower()):
            p = p.strip()
            if p in ("veg", "vegetarian"):
                prefs.append(Preference.VEG)
            elif p in ("egg", "eggs"):
                prefs.append(Preference.EGG)
            elif p in ("non_veg", "nonveg", "non-veg"):
                prefs.append(Preference.NON_VEG)
        if prefs:
            return profile.model_copy(update={"preferences": list(dict.fromkeys(prefs))}), True, "Updated"
        return profile, False, "Use: veg, egg, non_veg (comma-separated)"

    if field_key == FIELD_ALLERGIES:
        if value.lower() == "none":
            return profile.model_copy(update={"allergies": []}), True, "Updated"
        items = [a.strip() for a in value.split(",") if a.strip()]
        return profile.model_copy(update={"allergies": items}), True, "Updated"

    if field_key == FIELD_FOODS:
        items = [f.strip() for f in value.split(",") if f.strip()]
        return profile.model_copy(update={"foods_introduced": items}), True, "Updated"

    if field_key == FIELD_LOCATION:
        return profile.model_copy(update={"location": value}), True, "Updated"

    if field_key == FIELD_WEIGHT:
        try:
            w = float(value.replace(",", "."))
            if 0 < w < 50:
                return profile.model_copy(update={"current_weight_kg": w}), True, "Updated"
            return profile, False, "Weight should be between 0 and 50 kg"
        except ValueError:
            return profile, False, "Enter a number (e.g. 7.5)"

    if field_key == FIELD_HEIGHT:
        try:
            h = float(value.replace(",", "."))
            if 0 < h < 150:
                return profile.model_copy(update={"height_cm": h}), True, "Updated"
            return profile, False, "Height should be between 0 and 150 cm"
        except ValueError:
            return profile, False, "Enter a number (e.g. 68)"

    return profile, False, "Unknown field"


class ProfileUpdateFlow:
    """In-memory state for profile update conversations."""

    def __init__(self) -> None:
        self._states: dict[str, FlowState] = {}

    def get(self, phone: str) -> FlowState | None:
        return self._states.get(phone)

    def cancel(self, phone: str) -> None:
        """Exit update flow without saving."""
        self._states.pop(phone, None)

    def start(self, phone: str, profile: BabyProfile) -> str:
        """Start update flow. Returns menu message."""
        self._states[phone] = FlowState(step="menu", field_key=None, profile=profile)
        return f"Update profile.\n\n{UPDATE_MENU}"

    def handle_input(
        self,
        phone: str,
        text: str,
        on_save: Callable[[BabyProfile, str], None],
    ) -> tuple[str, bool]:
        """
        Process user input. on_save(profile) is called when profile is updated.
        Returns (reply_message, should_continue_flow).
        """
        state = self._states.get(phone)
        if not state:
            return "No update in progress. Send UPDATE to start.", False

        if state.step == "awaiting" and state.field_key:
            updated, ok, msg = parse_and_apply(state.profile, state.field_key, text)
            if not ok:
                return f"{msg}\n\n{get_field_prompt(state.field_key)}", True
            state.profile = updated
            on_save(updated, phone)
            self._states[phone] = FlowState(step="menu", field_key=None, profile=updated)
            return f"{msg}. Update another? Reply 1-8 or 0 when done.\n\n{UPDATE_MENU}", True

        choice = text.strip()
        if choice == "0":
            del self._states[phone]
            return "Profile updated. Send PROFILE to view.", False
        if choice in FIELD_MAP:
            field_key = FIELD_MAP[choice]
            if field_key is None:
                del self._states[phone]
                return "Profile updated. Send PROFILE to view.", False
            state.step = "awaiting"
            state.field_key = field_key
            return get_field_prompt(field_key), True

        return f"Reply with a number 0-8.\n\n{UPDATE_MENU}", True
