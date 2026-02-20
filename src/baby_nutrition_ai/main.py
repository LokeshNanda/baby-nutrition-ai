"""FastAPI application - webhook endpoint and health."""

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


@app.post("/webhook")
async def webhook_receive(request: Request) -> Response:
    """
    WhatsApp webhook - receives incoming messages.
    Returns 200 immediately; Meta requires response within 20s.
    """
    try:
        body = await request.json()
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
