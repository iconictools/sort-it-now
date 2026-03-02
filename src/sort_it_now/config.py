"""Configuration management for Sort It Now.

Stores monitored folders, destination sets, and user preferences as JSON.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
import zipfile
from typing import Any

from sort_it_now.constants import DEFAULT_CONFIG_FILE

logger = logging.getLogger(__name__)

# Default configuration template
_DEFAULT_CONFIG: dict[str, Any] = {
    "monitored_folders": {},
    "global_settings": {
        "focus_mode": False,
        "snooze_minutes": 0,
        "batch_mode": False,
        "auto_learn": True,
        "auto_learn_threshold": 3,
        "prompt_delay_seconds": 3.0,
    },
    "ignore_patterns": [
        "~$*",
        ".~lock.*",
        "desktop.ini",
        ".DS_Store",
        "Thumbs.db",
    ],
}


class Config:
    """Manages application configuration stored as a JSON file."""

    def __init__(self, config_path: str | None = None) -> None:
        self.path = config_path or DEFAULT_CONFIG_FILE
        self._data: dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load configuration from disk, creating defaults if missing.

        If the file exists but contains invalid JSON, back it up and
        reset to defaults.
        """
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "Config file corrupted (%s) -- backing up and resetting.",
                    exc,
                )
                backup = f"{self.path}.bak.{int(time.time())}"
                try:
                    shutil.copy2(self.path, backup)
                    logger.info("Backup saved to %s", backup)
                except OSError:
                    pass
                self._data = json.loads(json.dumps(_DEFAULT_CONFIG))
                self.save()
        else:
            self._data = json.loads(json.dumps(_DEFAULT_CONFIG))
            self.save()

    def save(self) -> None:
        """Persist current configuration to disk (atomic write)."""
        dir_path = os.path.dirname(self.path) or "."
        os.makedirs(dir_path, exist_ok=True)
        tmp_path = self.path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)
        os.replace(tmp_path, self.path)

    # ------------------------------------------------------------------
    # Monitored folders
    # ------------------------------------------------------------------

    @property
    def monitored_folders(self) -> dict[str, list[str]]:
        """Return ``{folder_path: [destination, ...]}`` mapping."""
        return self._data.get("monitored_folders", {})

    def add_monitored_folder(
        self, folder: str, destinations: list[str] | None = None
    ) -> None:
        """Register *folder* for monitoring with optional *destinations*."""
        folder = os.path.abspath(folder)
        if folder not in self._data["monitored_folders"]:
            self._data["monitored_folders"][folder] = destinations or []
            self.save()

    def remove_monitored_folder(self, folder: str) -> None:
        """Stop monitoring *folder*."""
        folder = os.path.abspath(folder)
        self._data["monitored_folders"].pop(folder, None)
        self.save()

    def set_destinations(self, folder: str, destinations: list[str]) -> None:
        """Set destination folders for a monitored *folder*."""
        folder = os.path.abspath(folder)
        self._data["monitored_folders"][folder] = destinations
        self.save()

    # ------------------------------------------------------------------
    # Global settings helpers
    # ------------------------------------------------------------------

    @property
    def global_settings(self) -> dict[str, Any]:
        return self._data.get("global_settings", {})

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.global_settings.get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        self._data.setdefault("global_settings", {})[key] = value
        self.save()

    def save_many(self, settings: dict[str, Any]) -> None:
        """Batch-update multiple settings in a single disk write."""
        gs = self._data.setdefault("global_settings", {})
        gs.update(settings)
        self.save()

    # ------------------------------------------------------------------
    # Ignore patterns
    # ------------------------------------------------------------------

    @property
    def ignore_patterns(self) -> list[str]:
        return self._data.get("ignore_patterns", [])

    def add_ignore_pattern(self, pattern: str) -> None:
        patterns = self._data.setdefault("ignore_patterns", [])
        if pattern not in patterns:
            patterns.append(pattern)
            self.save()

    def remove_ignore_pattern(self, pattern: str) -> None:
        patterns = self._data.get("ignore_patterns", [])
        if pattern in patterns:
            patterns.remove(pattern)
            self.save()

    # ------------------------------------------------------------------
    # Whitelist
    # ------------------------------------------------------------------

    def get_whitelist(self) -> list[str]:
        """Return the list of whitelist glob patterns."""
        return self._data.get("whitelist", [])

    def add_to_whitelist(self, pattern: str) -> None:
        """Add a glob pattern to the whitelist."""
        wl = self._data.setdefault("whitelist", [])
        if pattern not in wl:
            wl.append(pattern)
            self.save()

    def remove_from_whitelist(self, pattern: str) -> None:
        """Remove a glob pattern from the whitelist."""
        wl = self._data.get("whitelist", [])
        if pattern in wl:
            wl.remove(pattern)
            self.save()

    # ------------------------------------------------------------------
    # Rename patterns
    # ------------------------------------------------------------------

    @property
    def rename_patterns(self) -> list[dict[str, Any]]:
        """Return the list of rename pattern dicts."""
        return self._data.get("rename_patterns", [])

    def get_rename_pattern(self, ext: str) -> str | None:
        """Return the rename pattern string for *ext*, or *None*."""
        ext = ext.lower()
        for entry in self.rename_patterns:
            if not entry.get("enabled", True):
                continue
            if ext in entry.get("extensions", []):
                return entry.get("pattern")
        return None

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_config(self, export_path: str) -> None:
        """Export config.json and rules.json into a zip file."""
        rules_path = os.path.join(
            os.path.dirname(self.path) or ".", "rules.json"
        )
        with zipfile.ZipFile(export_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.exists(self.path):
                zf.write(self.path, "config.json")
            if os.path.exists(rules_path):
                zf.write(rules_path, "rules.json")

    def import_config(self, import_path: str) -> None:
        """Import config.json and rules.json from a zip file."""
        dest_dir = os.path.dirname(self.path) or "."
        with zipfile.ZipFile(import_path, "r") as zf:
            for name in ("config.json", "rules.json"):
                if name in zf.namelist():
                    zf.extract(name, dest_dir)
        self.load()
