"""JSON persistence: last search results and the application tracker.

Writes go to a temp file first and are then renamed, so a crash mid-write
never leaves a half-written, corrupted JSON file behind.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from .decorators import log_call
from .models import Application, Job

_jobs_adapter = TypeAdapter(list[Job])
_apps_adapter = TypeAdapter(dict[str, Application])


class JsonStore:
    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def results_path(self) -> Path:
        return self._dir / "last_search.json"

    @property
    def tracker_path(self) -> Path:
        return self._dir / "applications.json"

    @log_call
    def _write(self, path: Path, data: Any) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)  # folder may have been deleted
        fd, tmp = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def _read(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)

    # --- search results -----------------------------------------------------
    def save_results(self, jobs: list[Job]) -> Path:
        self._write(self.results_path, _jobs_adapter.dump_python(jobs, mode="json"))
        return self.results_path

    def load_results(self) -> list[Job]:
        return _jobs_adapter.validate_python(self._read(self.results_path, []))

    # --- tracker ------------------------------------------------------------
    def save_applications(self, apps: dict[str, Application]) -> None:
        self._write(self.tracker_path, _apps_adapter.dump_python(apps, mode="json"))

    def load_applications(self) -> dict[str, Application]:
        return _apps_adapter.validate_python(self._read(self.tracker_path, {}))

    def export(self, data: Any, filename: str) -> Path:
        path = self._dir / filename
        self._write(path, data)
        return path
