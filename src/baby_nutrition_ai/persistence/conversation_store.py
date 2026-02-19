"""Conversation history persistence for conversational handler."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_MESSAGES = 10  # Last 5 user + 5 assistant


class ConversationStore:
    """File-based conversation history per phone."""

    def __init__(self, data_dir: Path) -> None:
        self._dir = Path(data_dir) / "conversations"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, phone: str) -> Path:
        safe = "".join(c for c in phone if c.isalnum())
        return self._dir / f"{safe}.json"

    def get(self, phone: str) -> list[dict[str, str]]:
        """Get last N messages: [{"role": "user"|"assistant", "content": "..."}]"""
        path = self._path(phone)
        if not path.exists():
            return []
        try:
            with path.open() as f:
                data = json.load(f)
            return data.get("messages", [])[-MAX_MESSAGES:]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load conversation %s: %s", path, e)
            return []

    def append(self, phone: str, role: str, content: str) -> None:
        """Append a message and trim to MAX_MESSAGES."""
        messages = self.get(phone)
        messages.append({"role": role, "content": content})
        messages = messages[-MAX_MESSAGES:]
        path = self._path(phone)
        try:
            with path.open("w") as f:
                json.dump({"messages": messages}, f, indent=2)
        except OSError as e:
            logger.error("Could not save conversation %s: %s", path, e)
