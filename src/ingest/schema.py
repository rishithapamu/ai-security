"""Attack record schema
The normalized representation of a single adversarial prompt."""

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AttackRecord(BaseModel):
    id: str
    source: str
    prompt: str
    target_behavior: str | None = None
    attack_category: str | None = None
    is_harmful: bool | None = None
    severity: Literal["low", "med", "high"] | None = None
    created_at: datetime
    raw: dict

    @classmethod
    def make_id(cls, source: str, prompt: str) -> str:
        """Generate a stable hash from source and prompt."""
        content = json.dumps({"source": source, "prompt": prompt}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
