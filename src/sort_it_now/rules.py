"""Auto-rules / pattern learning for Sort It Now.

Persists extension-to-destination mappings so the app can auto-sort
files the user has previously classified.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from collections import Counter
from typing import Any

from sort_it_now.constants import DEFAULT_RULES_FILE

logger = logging.getLogger(__name__)


class Rules:
    """Manages learned sorting rules."""

    def __init__(self, rules_path: str | None = None) -> None:
        self.path = rules_path or DEFAULT_RULES_FILE
        self._data: dict[str, Any] = {"extension_map": {}, "history": []}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "Rules file corrupted (%s) -- backing up and resetting.",
                    exc,
                )
                backup = f"{self.path}.bak.{int(time.time())}"
                try:
                    shutil.copy2(self.path, backup)
                except OSError:
                    pass
                self._data = {"extension_map": {}, "history": []}
        else:
            self._data = {"extension_map": {}, "history": []}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    @property
    def extension_map(self) -> dict[str, str]:
        """Return ``{".ext": "Destination"}`` mapping."""
        return self._data.get("extension_map", {})

    def record_action(
        self, filepath: str, destination: str, threshold: int = 3
    ) -> None:
        """Record that the user sent *filepath* to *destination*.

        After enough consistent decisions for the same extension,
        this creates an automatic rule.  The *threshold* can be
        configured (default 3).
        """
        _, ext = os.path.splitext(filepath)
        ext_lower = ext.lower()
        if not ext_lower:
            return

        self._data.setdefault("history", []).append(
            {"ext": ext_lower, "destination": destination}
        )

        # Auto-learn after *threshold* consistent choices
        counts = Counter(
            entry["destination"]
            for entry in self._data["history"]
            if entry["ext"] == ext_lower
        )
        if counts:
            most_common_dest, count = counts.most_common(1)[0]
            if count >= threshold:
                self._data["extension_map"][ext_lower] = most_common_dest

        self.save()

    def set_rule(self, ext: str, destination: str) -> None:
        """Manually set an extension rule."""
        ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        self._data["extension_map"][ext] = destination
        self.save()

    def remove_rule(self, ext: str) -> None:
        """Remove a learned/manual rule for *ext*."""
        ext = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        self._data["extension_map"].pop(ext, None)
        self.save()

    def get_auto_destination(self, filepath: str) -> str | None:
        """Return the auto-learned destination for *filepath*, or *None*."""
        _, ext = os.path.splitext(filepath)
        return self.extension_map.get(ext.lower())
