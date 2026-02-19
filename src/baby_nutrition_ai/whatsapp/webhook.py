"""WhatsApp webhook handler - routes commands to services."""

import logging
from typing import Any

from baby_nutrition_ai.llm import OpenAIClient
from baby_nutrition_ai.persistence import ProfileStore
from baby_nutrition_ai.rules import RuleEngine
from baby_nutrition_ai.services.ai_service import AIService
from baby_nutrition_ai.services.meal_plan_service import MealPlanService
from baby_nutrition_ai.services.profile_service import ProfileService
from baby_nutrition_ai.services.story_service import StoryService
from baby_nutrition_ai.whatsapp.sender import WhatsAppSender

logger = logging.getLogger(__name__)

# Commands from WHATSAPP_FLOW.md
CMD_START = "start"
CMD_PROFILE = "profile"
CMD_TODAY = "today"
CMD_MONTH = "month"
CMD_STORY = "story"


class WebhookHandler:
    """Handles incoming webhook, dispatches to services, sends response."""

    def __init__(
        self,
        profile_store: ProfileStore,
        meal_plan_service: MealPlanService,
        story_service: StoryService,
        profile_service: ProfileService,
        sender: WhatsAppSender,
    ) -> None:
        self._store = profile_store
        self._meal_plan = meal_plan_service
        self._story = story_service
        self._profile = profile_service
        self._sender = sender

    def _normalize_command(self, text: str) -> str:
        return text.strip().lower() if text else ""

    def _extract_phone(self, from_id: str) -> str:
        """Normalize phone for storage. Meta sends with country code."""
        return str(from_id).lstrip("+")

    async def handle_webhook(self, body: dict[str, Any]) -> None:
        """
        Process webhook payload. Meta format: entry[].changes[].value.messages[].
        """
        try:
            entries = body.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    if change.get("field") != "messages":
                        continue
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    metadata = value.get("metadata", {})
                    phone_id = metadata.get("phone_number_id", "")
                    for msg in messages:
                        from_id = msg.get("from", "")
                        msg_id = msg.get("id", "")
                        msg_type = msg.get("type", "")
                        if msg_type == "text":
                            text = msg.get("text", {}).get("body", "")
                            await self._handle_message(
                                phone=from_id,
                                text=text,
                                msg_id=msg_id,
                            )
        except Exception as e:
            logger.exception("Webhook handle error: %s", e)

    async def _handle_message(
        self,
        phone: str,
        text: str,
        msg_id: str,
    ) -> None:
        """Route command and send response."""
        cmd = self._normalize_command(text)
        phone_key = self._extract_phone(phone)

        if cmd == CMD_START:
            reply = await self._handle_start(phone_key)
        elif cmd == CMD_PROFILE:
            reply = await self._handle_profile(phone_key)
        elif cmd == CMD_TODAY:
            reply = await self._handle_today(phone_key)
        elif cmd == CMD_MONTH:
            reply = await self._handle_month(phone_key)
        elif cmd == CMD_STORY:
            reply = await self._handle_story(phone_key)
        else:
            reply = (
                "Commands: START, PROFILE, TODAY, MONTH, STORY\n"
                "Send one of these for baby nutrition guidance."
            )

        await self._sender.send_text(phone_key, reply, idempotency_key=msg_id)

    async def _handle_start(self, phone: str) -> str:
        """Onboarding - create or show profile."""
        existing = self._profile.get_profile(phone)
        if existing:
            return (
                "Profile already exists.\n"
                f"{self._profile.profile_to_message(existing)}\n\n"
                "Send PROFILE to view, TODAY for meal plan, STORY for bedtime story."
            )
        self._profile.create_default_profile(phone)
        return (
            "Welcome! A default profile was created.\n"
            "Send PROFILE to view it. You can update details later.\n"
            "Commands: PROFILE, TODAY, STORY, MONTH"
        )

    async def _handle_profile(self, phone: str) -> str:
        """Show baby profile."""
        profile = self._profile.get_profile(phone)
        if not profile:
            return "No profile. Send START to create one."
        return self._profile.profile_to_message(profile)

    async def _handle_today(self, phone: str) -> str:
        """Today's meal plan."""
        result = await self._meal_plan.get_today_plan(phone)
        if isinstance(result, str):
            return result
        return result.to_whatsapp_text()

    async def _handle_month(self, phone: str) -> str:
        """Monthly PDF - stub."""
        profile = self._profile.get_profile(phone)
        if not profile:
            return "No profile. Send START to create one."
        return (
            "Monthly PDF generation is coming soon.\n"
            "For now, use TODAY for your daily meal plan."
        )

    async def _handle_story(self, phone: str) -> str:
        """Bedtime story."""
        result = await self._story.get_story(phone)
        if isinstance(result, str):
            return result
        return result.to_whatsapp_text()


def create_webhook_handler(
    profile_store: ProfileStore,
    sender: WhatsAppSender,
) -> WebhookHandler:
    """Factory - wires dependencies."""
    rule_engine = RuleEngine()
    llm = OpenAIClient()
    ai_service = AIService(llm, rule_engine)
    meal_plan = MealPlanService(ai_service, profile_store, rule_engine)
    story = StoryService(ai_service, profile_store, rule_engine)
    profile = ProfileService(profile_store, rule_engine)
    return WebhookHandler(
        profile_store=profile_store,
        meal_plan_service=meal_plan,
        story_service=story,
        profile_service=profile,
        sender=sender,
    )
