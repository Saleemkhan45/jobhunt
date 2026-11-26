"""App settings, read from environment variables with safe defaults."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    data_dir: Path = PROJECT_ROOT / "data"
    fixture_dir: Path = PROJECT_ROOT / "data" / "samples"
    timeout_seconds: float = Field(default=15, gt=0, le=120)
    user_agent: str = "JobHunt-CLI/1.0 (student project)"
    offline: bool = False

    @classmethod
    def from_env(cls, **overrides: object) -> "Settings":
        env: dict[str, object] = {}
        if value := os.getenv("JOBHUNT_DATA_DIR"):
            env["data_dir"] = Path(value)
        if value := os.getenv("JOBHUNT_TIMEOUT"):
            env["timeout_seconds"] = float(value)
        if os.getenv("JOBHUNT_OFFLINE", "").lower() in {"1", "true", "yes"}:
            env["offline"] = True
        env.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**env)
