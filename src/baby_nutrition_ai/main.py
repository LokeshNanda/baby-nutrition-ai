"""FastAPI application - webhook endpoint and health."""

import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from baby_nutrition_ai.config import get_settings
from baby_nutrition_ai.persistence import create_stores
from baby_nutrition_ai.whatsapp import WhatsAppSender, create_webhook_handler
from baby_nutrition_ai.whatsapp.webhook import WebhookHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Dependency injection - created at startup
_handler: WebhookHandler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup."""
    global _handler
    profile_store, conversation_store = create_stores()
    sender = WhatsAppSender()
    _handler = create_webhook_handler(
        profile_store=profile_store,
        conversation_store=conversation_store,
        sender=sender,
    )
    yield
    _handler = None


app = FastAPI(
    title="Baby Nutrition AI",
    description="WhatsApp-first AI for age-appropriate baby meal planning and bedtime stories",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check for load balancers."""
    return {"status": "ok"}


@app.get("/webhook")
async def webhook_verify(request: Request) -> Response:
    """
    WhatsApp webhook verification. Meta sends GET with hub.mode, hub.verify_token, hub.challenge.
    """
    settings = get_settings()
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified")
        return PlainTextResponse(challenge or "")
    logger.warning("Webhook verification failed: mode=%s", mode)
    return PlainTextResponse("Forbidden", status_code=403)


def _verify_webhook_signature(raw_body: bytes, signature_header: str | None, secret: str | None) -> bool:
    """Verify X-Hub-Signature-256 from Meta. Returns True if valid or if verification is skipped."""
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return secret is None  # Skip verification if no secret configured
    try:
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        received = signature_header[7:].lower()
        return hmac.compare_digest(expected.lower(), received)
    except Exception:
        return False


@app.post("/webhook")
async def webhook_receive(request: Request) -> Response:
    """
    WhatsApp webhook - receives incoming messages.
    Verifies X-Hub-Signature-256 when WHATSAPP_APP_SECRET is set.
    Returns 200 immediately; Meta requires response within 20s.
    """
    raw_body = await request.body()
    settings = get_settings()
    signature = request.headers.get("x-hub-signature-256")
    if not _verify_webhook_signature(raw_body, signature, settings.whatsapp_app_secret):
        if settings.whatsapp_app_secret:
            logger.warning("Webhook signature verification failed")
            return Response(status_code=403)
    try:
        body = json.loads(raw_body)
    except Exception as e:
        logger.warning("Invalid webhook body: %s", e)
        return Response(status_code=400)
    if _handler:
        import asyncio

        async def _process():
            try:
                await _handler.handle_webhook(body)
            except Exception as e:
                logger.exception("Webhook processing failed: %s", e)

        asyncio.create_task(_process())
    return Response(status_code=200)
