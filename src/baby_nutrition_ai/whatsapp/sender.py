"""WhatsApp message sender - idempotent, uses Meta Cloud API."""

import hashlib
import logging
from typing import Any

import httpx

from baby_nutrition_ai.config import get_settings

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppSender:
    """Send WhatsApp messages. Idempotent via content hash."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        phone_id: str | None = None,
    ) -> None:
        settings = get_settings()
        self._token = access_token or settings.whatsapp_access_token
        self._phone_id = phone_id or settings.whatsapp_phone_id

    def _idempotency_key(self, to: str, body: str) -> str:
        """Generate idempotency key for message."""
        raw = f"{to}:{body}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def send_text(
        self,
        to: str,
        body: str,
        *,
        idempotency_key: str | None = None,
    ) -> bool:
        """
        Send text message. Idempotent - same to+body yields same key.
        Returns True on success.
        """
        if not self._token or not self._phone_id:
            logger.warning("WhatsApp credentials not configured, skipping send")
            return False
        key = idempotency_key or self._idempotency_key(to, body)
        url = f"{META_API_BASE}/{self._phone_id}/messages"
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.lstrip("+"),
            "type": "text",
            "text": {"body": body},
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={**headers, "Idempotency-Key": key},
                    timeout=30.0,
                )
            if resp.status_code >= 400:
                logger.error(
                    "WhatsApp send failed: %s %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return False
            return True
        except httpx.HTTPError as e:
            logger.exception("WhatsApp send error: %s", e)
            return False
