"""Baby profile persistence - JSON file storage."""

import json
import logging
from pathlib import Path

from baby_nutrition_ai.models import BabyProfile

logger = logging.getLogger(__name__)


class ProfileStore:
    """File-based profile store. Keyed by (phone_number, baby_id)."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._data_dir / "index.json"

    def _profile_path(self, phone: str, baby_id: str) -> Path:
        safe_phone = "".join(c for c in phone if c.isalnum())
        return self._data_dir / f"{safe_phone}_{baby_id}.json"

    def _load_index(self) -> dict[str, str]:
        """phone -> baby_id mapping for default baby."""
        if not self._index_path.exists():
            return {}
        try:
            with self._index_path.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load index: %s", e)
            return {}

    def _save_index(self, index: dict[str, str]) -> None:
        try:
            with self._index_path.open("w") as f:
                json.dump(index, f, indent=2)
        except OSError as e:
            logger.error("Could not save index: %s", e)

    def get(self, phone: str, baby_id: str | None = None) -> BabyProfile | None:
        """Get profile by phone and optional baby_id."""
        if baby_id is None:
            baby_id = self._load_index().get(phone)
        if not baby_id:
            return None
        path = self._profile_path(phone, baby_id)
        if not path.exists():
            return None
        try:
            with path.open() as f:
                data = json.load(f)
            return BabyProfile.model_validate(data)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load profile %s: %s", path, e)
            return None

    def save(self, profile: BabyProfile, phone: str) -> None:
        """Save profile and set as default for phone."""
        path = self._profile_path(phone, profile.baby_id)
        try:
            with path.open("w") as f:
                json.dump(profile.model_dump(mode="json"), f, indent=2)
            index = self._load_index()
            index[phone] = profile.baby_id
            self._save_index(index)
        except OSError as e:
            logger.error("Could not save profile %s: %s", path, e)
            raise
