"""Crash-safe progress tracking for resumable scraping."""

from __future__ import annotations

import time
from pathlib import Path

from utils import read_json, write_json


class ProgressManager:
    def __init__(self, progress_path: str | Path, legacy_progress_path: str | Path | None = None) -> None:
        self.progress_path = Path(progress_path)
        self.legacy_progress_path = Path(legacy_progress_path) if legacy_progress_path else None
        self.progress = self._load()

    @property
    def completed_queries(self) -> set[str]:
        return set(self.progress.get("completed_queries", []))

    def is_completed(self, query_key: str) -> bool:
        completed = self.completed_queries
        legacy_key = query_key.split(":", 1)[1] if ":" in query_key else query_key
        return query_key in completed or legacy_key in completed

    def mark_completed(
        self,
        query_key: str,
        raw_records_collected: int,
        location: str,
        category: str,
        location_type: str,
    ) -> None:
        completed = self.completed_queries
        completed.add(query_key)
        self.progress = {
            "completed_queries": sorted(completed),
            "raw_records_collected": raw_records_collected,
            "last_completed_location": location,
            "last_completed_location_type": location_type,
            "last_completed_category": category,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.save()

    def save(self) -> None:
        write_json(self.progress_path, self.progress)

    def _load(self) -> dict:
        progress = read_json(self.progress_path, None)
        if progress is not None:
            return progress

        if self.legacy_progress_path:
            legacy_progress = read_json(self.legacy_progress_path, None)
            if legacy_progress is not None:
                write_json(self.progress_path, legacy_progress)
                return legacy_progress

        progress = {"completed_queries": []}
        write_json(self.progress_path, progress)
        return progress
