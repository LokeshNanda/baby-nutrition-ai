"""Redis-backed stores for cloud deployment. Use when REDIS_URL is set."""

import json
import logging
from pathlib import Path

from baby_nutrition_ai.models import BabyProfile

logger = logging.getLogger(__name__)

KEY_PREFIX = "baby_nutrition"
MAX_MESSAGES = 10


class RedisProfileStore:
    """Redis-backed profile store. Keyed by (phone, baby_id)."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client = None

    def _get_client(self):
        """Lazy-init Redis client."""
        if self._client is None:
            import redis
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
            )
        return self._client

    @property
    def data_dir(self) -> Path:
        """For factory compatibility when mixing file/Redis. Not used for Redis."""
        return Path("/tmp")  # Unused when Redis is active

    def _key(self, phone: str, baby_id: str) -> str:
        safe = "".join(c for c in phone if c.isalnum())
        return f"{KEY_PREFIX}:profile:{safe}:{baby_id}"

    def _index_key(self, phone: str) -> str:
        safe = "".join(c for c in phone if c.isalnum())
        return f"{KEY_PREFIX}:index:{safe}"

    def get(self, phone: str, baby_id: str | None = None) -> BabyProfile | None:
        """Get profile by phone and optional baby_id."""
        try:
            r = self._get_client()
            if baby_id is None:
                baby_id = r.get(self._index_key(phone))
            if not baby_id:
                return None
            data = r.get(self._key(phone, baby_id))
            if not data:
                return None
            return BabyProfile.model_validate(json.loads(data))
        except Exception as e:
            logger.warning("Redis profile get failed: %s", e)
            return None

    def save(self, profile: BabyProfile, phone: str) -> None:
        """Save profile and set as default for phone."""
        try:
            r = self._get_client()
            key = self._key(phone, profile.baby_id)
            r.set(key, json.dumps(profile.model_dump(mode="json")))
            r.set(self._index_key(phone), profile.baby_id)
        except Exception as e:
            logger.error("Redis profile save failed: %s", e)
            raise


class RedisConversationStore:
    """Redis-backed conversation history per phone."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._client = None

    def _get_client(self):
        """Lazy-init Redis client."""
        if self._client is None:
            import redis
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
            )
        return self._client

    def _key(self, phone: str) -> str:
        safe = "".join(c for c in phone if c.isalnum())
        return f"{KEY_PREFIX}:conversation:{safe}"

    def get(self, phone: str) -> list[dict[str, str]]:
        """Get last N messages."""
        try:
            r = self._get_client()
            data = r.lrange(self._key(phone), -MAX_MESSAGES, -1)
            if not data:
                return []
            return [json.loads(m) for m in data]
        except Exception as e:
            logger.warning("Redis conversation get failed: %s", e)
            return []

    def append(self, phone: str, role: str, content: str) -> None:
        """Append a message and trim to MAX_MESSAGES."""
        try:
            r = self._get_client()
            key = self._key(phone)
            r.rpush(key, json.dumps({"role": role, "content": content}))
            r.ltrim(key, -MAX_MESSAGES, -1)
        except Exception as e:
            logger.error("Redis conversation append failed: %s", e)
