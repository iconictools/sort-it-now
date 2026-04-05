"""File system watcher for File Wayfinder.

Uses *watchdog* to monitor folders for new, moved, or modified files.
Implements smart stability detection:
  - On Linux (inotify): ``FileClosedEvent`` (IN_CLOSE_WRITE) is the gold-
    standard signal that a file is done being written — used as the primary
    trigger.  Size/mtime polling is still done as a fallback.
  - On all platforms: size + mtime are both checked (not just size) with
    exponential backoff.
  - On Windows: an exclusive open is attempted to confirm the file is not
    held by another process (e.g. a browser mid-download).
"""

from __future__ import annotations

import fnmatch as fnmatch_mod
import logging
import os
import sys
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


def _wait_until_stable(
    filepath: str,
    close_event: threading.Event | None = None,
) -> bool:
    """Block until *filepath* is done being written and safe to move.

    Strategy:
    1. If *close_event* is already set (Linux inotify ``IN_CLOSE_WRITE``
       fired before we even started polling), return immediately.
    2. Wait ``FILE_STABLE_DELAY_SECONDS`` — check *close_event* while waiting.
    3. Poll size **and** mtime with exponential backoff.  The file is stable
       once both values are unchanged across two consecutive checks.
    4. On Windows, confirm the file is not exclusively locked before returning.

    Returns *True* if the file is stable, *False* if it disappeared.
    """
    if close_event is not None and close_event.is_set():
        return os.path.exists(filepath)

    # Wait the initial delay, but wake up early if inotify signals done.
    if close_event is not None:
        close_event.wait(timeout=FILE_STABLE_DELAY_SECONDS)
        if close_event.is_set():
            return os.path.exists(filepath)
    else:
        time.sleep(FILE_STABLE_DELAY_SECONDS)

    prev_size = -1
    prev_mtime = -1.0
    delay = FILE_STABLE_CHECK_INTERVAL

    for _ in range(FILE_STABLE_MAX_CHECKS):
        if not os.path.exists(filepath):
            return False
        try:
            stat = os.stat(filepath)
        except OSError:
            return False

        size, mtime = stat.st_size, stat.st_mtime

        if size == prev_size and mtime == prev_mtime:
            # On Windows, also confirm the file is not exclusively locked.
            if sys.platform == "win32":
                try:
                    with open(filepath, "rb"):
                        pass
                except (IOError, PermissionError, OSError):
                    # Still locked — reset and keep polling.
                    prev_size = -1
                    prev_mtime = -1.0
                    time.sleep(delay)
                    delay = min(delay * 1.5, 5.0)
                    continue
            return True

        prev_size = size
        prev_mtime = mtime

        # Wake early if inotify signals; otherwise sleep with backoff.
        if close_event is not None:
            close_event.wait(timeout=delay)
            if close_event.is_set():
                return os.path.exists(filepath)
        else:
            time.sleep(delay)

        delay = min(delay * 1.5, 5.0)

    return os.path.exists(filepath)


class _Handler(FileSystemEventHandler):
    """Dispatches relevant file-system events to a callback.

    On Linux (inotify), ``on_closed`` fires when a file descriptor is closed
    after writing (``IN_CLOSE_WRITE``).  This is the most reliable signal that
    a file is done being written, so we use it to short-circuit size/mtime
    polling.  On other platforms ``on_closed`` may not fire; in that case
    ``on_created`` / ``on_moved`` drive processing via the polling fallback.
    """

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
        # Maps path → close_event.  The event is set when inotify confirms
        # IN_CLOSE_WRITE so the polling loop can wake up immediately.
        self._pending: dict[str, threading.Event] = {}
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

    def _handle(self, path: str, already_closed: bool = False) -> None:
        if self._should_ignore(path):
            return
        # Prevent self-triggered loops (file moved by us).
        with self._self_moved_lock:
            if path in self._self_moved:
                self._self_moved.discard(path)
                return

        with self._pending_lock:
            if path in self._pending:
                # Already being processed — if we now know it's closed,
                # signal the polling thread so it can finish early.
                if already_closed:
                    self._pending[path].set()
                return
            close_event = threading.Event()
            if already_closed:
                close_event.set()
            self._pending[path] = close_event

        def _process() -> None:
            try:
                ev = self._pending.get(path)
                if _wait_until_stable(path, close_event=ev):
                    self._callback(path)
            finally:
                with self._pending_lock:
                    self._pending.pop(path, None)

        threading.Thread(target=_process, daemon=True).start()

    def on_closed(self, event: FileSystemEvent) -> None:
        """Linux inotify IN_CLOSE_WRITE — the file is definitively done."""
        if not event.is_directory:
            self._handle(event.src_path, already_closed=True)

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        # A rename (e.g. .crdownload → .pdf by the browser when the download
        # completes) means the file is done — treat as already_closed.
        if hasattr(event, "dest_path"):
            self._handle(event.dest_path, already_closed=True)

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
