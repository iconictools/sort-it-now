"""Auto-rules / pattern learning for Iconic Filer.

Persists extension-to-destination mappings so the app can auto-sort
files the user has previously classified.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
import re
import shutil
import time
from typing import Any

from iconic_filer.constants import DEFAULT_RULES_FILE

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
                self.save()  # overwrite the corrupted file once, not on every startup
        else:
            self._data = {"extension_map": {}, "history": []}

    def save(self) -> None:
        dir_path = os.path.dirname(self.path) or "."
        os.makedirs(dir_path, exist_ok=True)
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        os.replace(tmp_path, self.path)

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    @property
    def extension_map(self) -> dict[str, str]:
        """Return ``{".ext": "Destination"}`` mapping."""
        return self._data.get("extension_map", {})

    def record_action(self, filepath: str, destination: str) -> None:
        """Record that the user sent *filepath* to *destination*.

        This is kept purely as an activity log — no automatic rule is
        ever created from it.  Use :meth:`set_rule` to create a rule
        explicitly.
        """
        _, ext = os.path.splitext(filepath)
        ext_lower = ext.lower()
        if not ext_lower:
            return

        self._data.setdefault("history", []).append(
            {"ext": ext_lower, "destination": destination}
        )
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

    # ------------------------------------------------------------------
    # Pattern rules (glob / regex)
    # ------------------------------------------------------------------

    @property
    def pattern_rules(self) -> list[dict[str, str]]:
        """Return the list of pattern rule dicts."""
        return self._data.get("pattern_rules", [])

    def set_pattern_rule(self, pattern: str, destination: str,
                         pattern_type: str = "glob") -> None:
        """Add or update a pattern rule."""
        rules = self._data.setdefault("pattern_rules", [])
        # Update existing rule with same pattern
        for rule in rules:
            if rule["pattern"] == pattern:
                rule["destination"] = destination
                rule["type"] = pattern_type
                self.save()
                return
        rules.append({
            "pattern": pattern,
            "destination": destination,
            "type": pattern_type,
        })
        self.save()

    def remove_pattern_rule(self, pattern: str) -> None:
        """Remove a pattern rule by its pattern string."""
        rules = self._data.get("pattern_rules", [])
        self._data["pattern_rules"] = [
            r for r in rules if r["pattern"] != pattern
        ]
        self.save()

    def get_pattern_destination(self, filepath: str) -> str | None:
        """Return the destination for *filepath* based on pattern rules."""
        basename = os.path.basename(filepath)
        for rule in self.pattern_rules:
            pattern = rule["pattern"]
            pat_type = rule.get("type", "glob")
            try:
                if pat_type == "regex":
                    if re.match(pattern, basename):
                        return rule["destination"]
                else:
                    if fnmatch.fnmatch(basename, pattern):
                        return rule["destination"]
            except re.error:
                logger.warning("Invalid regex pattern: %s", pattern)
                continue
        return None
