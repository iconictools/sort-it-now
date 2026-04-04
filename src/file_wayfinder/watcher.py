"""File system watcher for File Wayfinder.

Uses *watchdog* to monitor folders for new, moved, or modified files.
Implements smart delay to wait for downloads to finish before prompting.
"""

from __future__ import annotations

import fnmatch as fnmatch_mod
import logging
import os
import time
import threading
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from file_wayfinder.classifier import is_temp_file, matches_ignore_pattern
from file_wayfinder.constants import (
    FILE_STABLE_CHECK_INTERVAL,
    FILE_STABLE_DELAY_SECONDS,
    FILE_STABLE_MAX_CHECKS,
)

logger = logging.getLogger(__name__)


def _wait_until_stable(filepath: str) -> bool:
    """Block until *filepath* stops changing size.

    Returns *True* if the file is stable, *False* if it disappeared or
    remained unstable after the maximum number of checks.
    """
    time.sleep(FILE_STABLE_DELAY_SECONDS)
    prev_size = -1
    for _ in range(FILE_STABLE_MAX_CHECKS):
        if not os.path.exists(filepath):
            return False
        size = os.path.getsize(filepath)
        if size == prev_size:
            return True
        prev_size = size
        time.sleep(FILE_STABLE_CHECK_INTERVAL)
    return os.path.exists(filepath)


class _Handler(FileSystemEventHandler):
    """Dispatches relevant file-system events to a callback."""

    def __init__(
        self,
        callback: Callable[[str], None],
        ignore_patterns: list[str],
        self_moved_paths: set[str],
        self_moved_lock: threading.Lock,
        catch_folders: bool = False,
    ) -> None:
        super().__init__()
        self._callback = callback
        self._ignore_patterns = ignore_patterns
        self._self_moved: set[str] = self_moved_paths
        self._self_moved_lock = self_moved_lock
        self._pending: set[str] = set()
        self._pending_lock = threading.Lock()
        self._catch_folders = catch_folders

    def _should_ignore(self, path: str) -> bool:
        if os.path.isdir(path):
            return not self._catch_folders
        basename = os.path.basename(path)
        if matches_ignore_pattern(basename, self._ignore_patterns):
            return True
        if is_temp_file(path):
            return True
        return False

    def _handle(self, path: str) -> None:
        if self._should_ignore(path):
            return
        # Prevent self-triggered loops
        with self._self_moved_lock:
            if path in self._self_moved:
                self._self_moved.discard(path)
                return
        with self._pending_lock:
            if path in self._pending:
                return
            self._pending.add(path)

        def _process() -> None:
            try:
                if _wait_until_stable(path):
                    self._callback(path)
            finally:
                with self._pending_lock:
                    self._pending.discard(path)

        thread = threading.Thread(target=_process, daemon=True)
        thread.start()

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if hasattr(event, "dest_path"):
            self._handle(event.dest_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event.src_path)


class FolderWatcher:
    """Watches multiple folders and dispatches events via a callback.

    Parameters
    ----------
    callback:
        Called with the absolute path of every newly-detected file
        (or folder, when *catch_folders* is enabled).
    ignore_patterns:
        Shell-glob patterns for filenames to ignore.
    catch_folders:
        When *True*, directories created/moved into a monitored folder
        are also dispatched to the callback.
    """

    def __init__(
        self,
        callback: Callable[[str], None],
        ignore_patterns: list[str] | None = None,
        catch_folders: bool = False,
    ) -> None:
        self._callback = callback
        self._ignore_patterns = ignore_patterns or []
        self._catch_folders = catch_folders
        self._observer = Observer()
        self._self_moved_paths: set[str] = set()
        self._self_moved_lock = threading.Lock()
        self._watches: dict[str, object] = {}

    def mark_self_moved(self, path: str) -> None:
        """Register *path* so the next event on it is ignored (loop prevention)."""
        with self._self_moved_lock:
            self._self_moved_paths.add(path)

    def add_folder(self, folder: str) -> None:
        """Start watching *folder* (non-recursive)."""
        folder = os.path.abspath(folder)
        if folder in self._watches:
            return
        handler = _Handler(
            self._callback, self._ignore_patterns, self._self_moved_paths,
            self._self_moved_lock,
            catch_folders=self._catch_folders,
        )
        watch = self._observer.schedule(handler, folder, recursive=False)
        self._watches[folder] = watch
        logger.info("Watching %s", folder)

    def remove_folder(self, folder: str) -> None:
        folder = os.path.abspath(folder)
        watch = self._watches.pop(folder, None)
        if watch is not None:
            self._observer.unschedule(watch)
            logger.info("Stopped watching %s", folder)

    def start(self) -> None:
        self._observer.start()
        logger.info("Watcher started")

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=5)
        logger.info("Watcher stopped")

    def scan_existing(
        self,
        folder: str,
        callback: Callable[[str], None],
        whitelist: list[str] | None = None,
    ) -> None:
        """Scan *folder* for existing files (and folders when enabled).

        Respects ignore patterns and optional *whitelist* patterns.
        """
        folder = os.path.abspath(folder)
        wl = whitelist or []
        for entry in os.scandir(folder):
            if entry.is_dir():
                if not self._catch_folders:
                    continue
            else:
                if is_temp_file(entry.path):
                    continue
            basename = entry.name
            if matches_ignore_pattern(basename, self._ignore_patterns):
                continue
            # Skip whitelisted items
            skip = False
            for pat in wl:
                if fnmatch_mod.fnmatch(basename, pat):
                    skip = True
                    break
            if skip:
                continue
            callback(entry.path)
