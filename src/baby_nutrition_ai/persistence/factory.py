"""Store factory - creates file or Redis stores based on config."""

from pathlib import Path

from baby_nutrition_ai.config import get_settings
from baby_nutrition_ai.persistence.conversation_store import ConversationStore
from baby_nutrition_ai.persistence.profile_store import ProfileStore
from baby_nutrition_ai.persistence.redis_store import (
    RedisConversationStore,
    RedisProfileStore,
)


def create_stores() -> tuple:
    """
    Create profile and conversation stores based on REDIS_URL.
    Returns (profile_store, conversation_store).
    Uses Redis when REDIS_URL is set; otherwise file-based.
    """
    settings = get_settings()
    if settings.redis_url:
        return (
            RedisProfileStore(settings.redis_url),
            RedisConversationStore(settings.redis_url),
        )
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return (
        ProfileStore(data_dir),
        ConversationStore(data_dir),
    )
