"""Conversational handler - natural language routing via LLM tool-calling."""

import logging
import re
from datetime import date
from typing import Any

from baby_nutrition_ai.llm import OpenAIClient
from baby_nutrition_ai.models import FeedingType, Preference
from baby_nutrition_ai.llm.openai_client import TOOLS_DEFINITION
from baby_nutrition_ai.persistence import ConversationStore, ProfileStore
from baby_nutrition_ai.services.meal_plan_service import MealPlanService
from baby_nutrition_ai.services.story_service import StoryService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a friendly pediatric nutrition assistant for parents. Follow WHO and Indian Academy of Pediatrics guidelines.
You have access to tools:
- get_meal_plan: today's 4 meals. Use exclude_foods/swap_meal/include_foods when user wants changes.
- get_story: bedtime story.
- log_food_introduced: when user says they tried/introduced a food, record it.
- update_profile: bulk update multiple fields at once. When user wants to update profile (e.g. "name is Ravi, boy, allergic to peanut"), extract ALL mentioned fields and call this tool. Supports: baby_name, gender, birth_weight_kg, dob, allergies, feeding_type, preferences, foods_introduced, location, current_weight_kg, height_cm.
For general questions about feeding, textures, food safety, answer briefly. Never give medical advice - say "Consult your pediatrician for medical concerns."
Keep responses short and WhatsApp-friendly (no long paragraphs).

Baby profile context:
{profile_context}
"""

NO_PROFILE_CONTEXT = "No profile yet. If user asks for meal plan or story, the tool will return a message asking them to send START first."


class ConversationalHandler:
    """Handles non-command messages via LLM with tool-calling."""

    def __init__(
        self,
        llm: OpenAIClient,
        meal_plan_service: MealPlanService,
        story_service: StoryService,
        profile_store: ProfileStore,
        conversation_store: ConversationStore,
    ) -> None:
        self._llm = llm
        self._meal_plan = meal_plan_service
        self._story = story_service
        self._profile_store = profile_store
        self._conversation = conversation_store

    def _bulk_update_profile(self, phone: str, args: dict[str, Any]) -> str:
        """Apply bulk profile update from conversational args."""
        profile = self._profile_store.get(phone)
        if not profile:
            return "No profile. Send START to create one first."
        updates: dict[str, Any] = {}
        if v := args.get("baby_name"):
            updates["baby_name"] = str(v).strip() or None
        if v := args.get("gender"):
            g = str(v).lower()
            if g in ("male", "boy", "m"):
                updates["gender"] = "male"
            elif g in ("female", "girl", "f"):
                updates["gender"] = "female"
            elif g in ("other",):
                updates["gender"] = "other"
        if args.get("birth_weight_kg") is not None:
            try:
                w = float(args.get("birth_weight_kg", 0))
                if 0 < w < 10:
                    updates["birth_weight_kg"] = w
            except (TypeError, ValueError):
                pass
        if v := args.get("dob"):
            match = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", str(v))
            if match:
                try:
                    dob = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    if dob <= date.today():
                        updates["dob"] = dob
                except ValueError:
                    pass
        if "allergies" in args:
            s = str(args.get("allergies", "")).strip().lower()
            updates["allergies"] = [] if s == "none" else [a.strip() for a in str(args.get("allergies", "")).split(",") if a.strip()]
        if v := args.get("feeding_type"):
            f = str(v).lower()
            if f in ("breastfed", "breast", "bf"):
                updates["feeding_type"] = FeedingType.BREASTFED
            elif f in ("formula", "formula-fed"):
                updates["feeding_type"] = FeedingType.FORMULA
            elif f in ("mixed", "both"):
                updates["feeding_type"] = FeedingType.MIXED
        if v := args.get("preferences"):
            prefs: list[Preference] = []
            for p in re.split(r"[,.\s]+", str(v).lower()):
                p = p.strip()
                if p in ("veg", "vegetarian"):
                    prefs.append(Preference.VEG)
                elif p in ("egg", "eggs"):
                    prefs.append(Preference.EGG)
                elif p in ("non_veg", "nonveg", "non-veg"):
                    prefs.append(Preference.NON_VEG)
            if prefs:
                updates["preferences"] = list(dict.fromkeys(prefs))
        if v := args.get("foods_introduced"):
            items = [f.strip() for f in str(v).split(",") if f.strip()]
            if items:
                merged = list(dict.fromkeys(profile.foods_introduced + items))
                updates["foods_introduced"] = merged
        if v := args.get("location"):
            updates["location"] = str(v).strip() or None
        if args.get("current_weight_kg") is not None:
            try:
                w = float(args.get("current_weight_kg", 0))
                if 0 < w < 50:
                    updates["current_weight_kg"] = w
            except (TypeError, ValueError):
                pass
        if args.get("height_cm") is not None:
            try:
                h = float(args.get("height_cm", 0))
                if 0 < h < 150:
                    updates["height_cm"] = h
            except (TypeError, ValueError):
                pass
        if not updates:
            return "No valid fields to update. Check the values provided."
        updated = profile.model_copy(update=updates)
        self._profile_store.save(updated, phone)
        fields = ", ".join(updates.keys())
        return f"Profile updated: {fields}. Send PROFILE to view."

    def _add_foods_introduced(self, phone: str, foods_str: str) -> str:
        """Add foods to profile's foods_introduced. Returns confirmation message."""
        if not foods_str or not foods_str.strip():
            return "No foods specified."
        profile = self._profile_store.get(phone)
        if not profile:
            return "No profile. Send START to create one first."
        new_foods = [f.strip() for f in foods_str.split(",") if f.strip()]
        if not new_foods:
            return "No valid foods to add."
        merged = list(dict.fromkeys(profile.foods_introduced + new_foods))
        updated = profile.model_copy(update={"foods_introduced": merged})
        self._profile_store.save(updated, phone)
        return f"Added to foods introduced: {', '.join(new_foods)}. Profile updated."

    def _profile_context(self, phone: str) -> str:
        """Build profile summary for prompt."""
        profile = self._profile_store.get(phone)
        if not profile:
            return NO_PROFILE_CONTEXT
        ctx = profile.to_ai_context()
        return (
            f"Name: {ctx.get('baby_name') or 'not set'}. "
            f"Age: {ctx['age_in_months']} months. "
            f"Feeding: {ctx['feeding_type']}. "
            f"Preferences: {ctx['preferences']}. "
            f"Allergies: {ctx['allergies']}. "
            f"Foods introduced: {ctx['foods_introduced']}. "
            f"Location: {ctx['location'] or 'not set'}."
        )

    async def handle(self, phone: str, user_message: str) -> str:
        """
        Process user message conversationally. Uses LLM with tools.
        Returns response string.
        """
        profile_ctx = self._profile_context(phone)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(profile_context=profile_ctx)
        history = self._conversation.get(phone)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": user_message})

        async def execute_tool(name: str, args: dict[str, Any]) -> str:
            if name == "get_meal_plan":
                constraints: dict[str, Any] = {}
                if s := args.get("exclude_foods"):
                    constraints["exclude_foods"] = [
                        f.strip() for f in str(s).split(",") if f.strip()
                    ]
                if s := args.get("swap_meal"):
                    constraints["swap_meal"] = str(s).strip()
                if s := args.get("include_foods"):
                    constraints["include_foods"] = [
                        f.strip() for f in str(s).split(",") if f.strip()
                    ]
                result = await self._meal_plan.get_today_plan(
                    phone, constraints=constraints if constraints else None
                )
                if hasattr(result, "to_whatsapp_text"):
                    return result.to_whatsapp_text()
                return str(result)
            if name == "get_story":
                result = await self._story.get_story(phone)
                if hasattr(result, "to_whatsapp_text"):
                    return result.to_whatsapp_text()
                return str(result)
            if name == "log_food_introduced":
                return self._add_foods_introduced(phone, args.get("foods", ""))
            if name == "update_profile":
                return self._bulk_update_profile(phone, args)
            return f"Unknown tool: {name}"

        try:
            response = await self._llm.chat_with_tools(
                messages=messages,
                tools=TOOLS_DEFINITION,
                execute_tool=execute_tool,
                max_tokens=1024,
            )
        except Exception as e:
            logger.exception("Conversational handler failed: %s", e)
            return (
                "Sorry, I couldn't process that. "
                "Try commands: START, PROFILE, TODAY, STORY."
            )

        if not response:
            return "I'm not sure how to help with that. Try: TODAY for meals, STORY for a bedtime story."

        self._conversation.append(phone, "user", user_message)
        self._conversation.append(phone, "assistant", response)
        return response
