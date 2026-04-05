"""Main application orchestrator for File Wayfinder."""

from __future__ import annotations

import datetime
import fnmatch
import logging
import os
import shutil
import sys
import threading

from file_wayfinder.classifier import suggest_destinations
from file_wayfinder.config import Config
from file_wayfinder.conflict_ui import resolve_conflict
from file_wayfinder.constants import DEFAULT_UNSORTED_DIR
from file_wayfinder.dashboard_ui import show_batch_list, show_dashboard
from file_wayfinder.duplicate import find_duplicate
from file_wayfinder.history import History
from file_wayfinder.notifications import notify
from file_wayfinder.prompt import SortPrompt, SetupWizard
from file_wayfinder.rules import Rules
from file_wayfinder.rules_ui import RulesDialog
from file_wayfinder.settings_ui import SettingsDialog
from file_wayfinder.tray import TrayIcon
from file_wayfinder.watcher import FolderWatcher

logger = logging.getLogger(__name__)


def _is_dnd_active() -> bool:
    """Check if system Do Not Disturb / Focus Assist is active (Windows).

    Returns *False* on non-Windows platforms or when the state cannot be read.
    """
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\CloudStore"
            r"\Store\DefaultAccount\Current"
            r"\default$windows.data.notifications.quiethourssettings"
            r"\windows.data.notifications.quiethourssettings",
            0,
            winreg.KEY_READ,
        )
        try:
            data, _ = winreg.QueryValueEx(key, "Data")
            # A non-empty Data value indicates Focus Assist is enabled.
            return bool(data)
        except OSError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def _apply_rename_pattern(filepath: str, pattern: str) -> str:
    """Apply a rename pattern to *filepath*, returning the new filename.

    Supported tokens: ``{date}``, ``{name}``, ``{ext}``.
    """
    basename = os.path.basename(filepath)
    name, ext = os.path.splitext(basename)
    today = datetime.date.today().isoformat()
    result = pattern.replace("{date}", today)
    result = result.replace("{name}", name)
    result = result.replace("{ext}", ext)
    # Ensure the extension is preserved
    if not result.endswith(ext):
        result += ext
    return result


class App:
    """Top-level application that wires all components together."""

    def __init__(
        self,
        config: Config | None = None,
        history: History | None = None,
        rules: Rules | None = None,
    ) -> None:
        self.config = config or Config()
        self.history = history or History()
        self.rules = rules or Rules()

        self._focus_mode = self.config.get_setting("focus_mode", False)
        self._batch_queue: list[str] = []
        self._lock = threading.Lock()

        self.watcher = FolderWatcher(
            callback=self._on_file_detected,
            ignore_patterns=self.config.ignore_patterns,
            catch_folders=self.config.get_setting("catch_folders", False),
        )
        self.tray = TrayIcon(
            on_open_dashboard=self._show_dashboard,
            on_toggle_focus=self._toggle_focus,
            on_undo=self._undo_last,
            on_open_settings=self._show_settings,
            on_open_rules=self._show_rules,
            on_add_folder=self._add_folder_via_tray,
            on_quit=self._quit,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the application (blocks until quit)."""
        # First-run setup if no monitored folders
        if not self.config.monitored_folders:
            wizard = SetupWizard()
            folders = wizard.run()
            if not folders:
                logger.info("No folders configured -- exiting.")
                return
            for folder, dests in folders.items():
                self.config.add_monitored_folder(folder, dests)

        # Validate monitored folders exist before starting
        missing: list[str] = []
        for folder in list(self.config.monitored_folders):
            if not os.path.isdir(folder):
                logger.warning("Monitored folder does not exist: %s", folder)
                missing.append(folder)

        if missing:
            logger.warning(
                "Missing monitored folders: %s -- they will be skipped.",
                ", ".join(missing),
            )

        # Start watching configured folders
        for folder in self.config.monitored_folders:
            if folder not in missing:
                try:
                    self.watcher.add_folder(folder)
                except Exception as exc:
                    logger.error("Cannot watch %s: %s", folder, exc)
        self.watcher.start()

        # Scan existing files in monitored folders
        if self.config.get_setting("scan_existing_enabled", False):
            whitelist = self.config.get_whitelist()
            for folder in self.config.monitored_folders:
                if folder not in missing:
                    self.watcher.scan_existing(
                        folder, self._on_file_detected, whitelist,
                    )

        logger.info("File Wayfinder is running.")
        self._update_tray_monitored_count()
        # Tray icon runs on the main thread (required by OS)
        try:
            self.tray.start()
        finally:
            self.watcher.stop()
            self.history.close()

    def _update_tray_monitored_count(self) -> None:
        """Update the tray tooltip to show how many folders are being monitored."""
        count = len(self.config.monitored_folders)
        self.tray.set_monitored_count(count)

    def _quit(self) -> None:
        logger.info("Shutting down...")
        self.watcher.stop()
        self.history.close()

    # ------------------------------------------------------------------
    # File event handling
    # ------------------------------------------------------------------

    def _on_file_detected(self, filepath: str) -> None:
        """Called by the watcher when a new/stable file or folder is detected."""
        logger.info("Detected: %s", filepath)

        # Skip files that live inside a configured destination folder.
        # Destination folders are whitelisted by the program so that files
        # already sorted into them are never re-prompted.
        parent = os.path.dirname(os.path.abspath(filepath))
        for dests in self.config.monitored_folders.values():
            for dest in dests:
                if os.path.abspath(dest) == parent:
                    logger.debug(
                        "In destination folder, skipping: %s", filepath,
                    )
                    return

        # Skip whitelisted files
        basename = os.path.basename(filepath)
        for pat in self.config.get_whitelist():
            if fnmatch.fnmatch(basename, pat):
                logger.debug("Whitelisted, skipping: %s", filepath)
                return

        # Pause when DND / Focus Assist is active (Q6.3)
        if self.config.get_setting("pause_on_dnd", False) and _is_dnd_active():
            with self._lock:
                self._batch_queue.append(filepath)
                count = len(self._batch_queue)
            self.tray.set_pending(True, count)
            return

        if self._focus_mode:
            with self._lock:
                self._batch_queue.append(filepath)
                count = len(self._batch_queue)
            self.tray.set_pending(True, count)
            return

        # Check pattern rules
        if self.config.get_setting("pattern_rules_enabled", True):
            pattern_dest = self.rules.get_pattern_destination(filepath)
            if pattern_dest and os.path.isdir(pattern_dest):
                self._move_file(filepath, pattern_dest)
                return

        # Determine which monitored folder this file belongs to
        parent = os.path.dirname(os.path.abspath(filepath))
        destinations = self.config.monitored_folders.get(parent, [])
        if not destinations:
            # Try to find a matching monitored folder (with proper path check)
            for mf, dests in self.config.monitored_folders.items():
                mf_abs = os.path.abspath(mf)
                if parent == mf_abs or parent.startswith(mf_abs + os.sep):
                    destinations = dests
                    break

        if not destinations:
            logger.debug("No destinations configured for %s", filepath)
            return

        ordered = suggest_destinations(
            filepath, destinations, self.rules.extension_map
        )

        theme_name = self.config.get_setting("theme", "dark")

        # Build quick-add callback (only meaningful for directories)
        parent_monitored = parent
        for mf in self.config.monitored_folders:
            if os.path.abspath(mf) == parent:
                parent_monitored = mf
                break

        def _on_quick_add(folder_path: str) -> None:
            self._quick_add_folder(folder_path, parent_monitored)

        # Show prompt on the main thread via threading
        prompt = SortPrompt(
            filepath, ordered, self._on_prompt_done,
            theme=theme_name,
            on_whitelist=self.config.add_to_whitelist,
            on_quick_add=_on_quick_add,
        )
        t = threading.Thread(target=prompt.show, daemon=True)
        t.start()

    def _on_prompt_done(
        self, filepath: str, destination: str | None, always: bool
    ) -> None:
        """Callback after the user responds to a prompt."""
        if destination is None:
            logger.info("Ignored: %s", filepath)
            return

        self._move_file(filepath, destination)

        if always:
            _, ext = os.path.splitext(filepath)
            if ext:
                self.rules.set_rule(ext, destination)
                logger.info("Auto-rule created: %s -> %s", ext, destination)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _move_file(self, src: str, dest_dir: str) -> None:
        """Move *src* (file or folder) into *dest_dir*, recording the action.

        On failure, falls back to an "unsorted" folder so items are never lost.
        Uses conflict resolution UI when a file already exists.
        """
        try:
            os.makedirs(dest_dir, exist_ok=True)

            # Apply rename pattern if configured (files only, not folders)
            if not os.path.isdir(src):
                _, ext = os.path.splitext(src)
                rename_pat = self.config.get_rename_pattern(ext.lower())
                if rename_pat:
                    new_name = _apply_rename_pattern(src, rename_pat)
                    dst = os.path.join(dest_dir, new_name)
                else:
                    dst = os.path.join(dest_dir, os.path.basename(src))
            else:
                dst = os.path.join(dest_dir, os.path.basename(src))

            # Duplicate detection
            if self.config.get_setting("duplicate_detection", False):
                dup = find_duplicate(src, dest_dir)
                if dup is not None:
                    resolved = resolve_conflict(src, dup, self.config)
                    if resolved is None:
                        logger.info("Skipped (duplicate): %s", src)
                        return
                    dst = resolved

            # Conflict resolution UI (Q11.15)
            if os.path.exists(dst):
                resolved = resolve_conflict(src, dst, self.config)
                if resolved is None:
                    logger.info("Skipped (conflict): %s", src)
                    return
                dst = resolved

            self.watcher.mark_self_moved(dst)
            shutil.move(src, dst)
            self.history.record(src, dst)
            logger.info("Moved %s -> %s", src, dst)

            # Native notification
            if self.config.get_setting("native_notifications", True):
                src_name = os.path.basename(src)
                dest_name = os.path.basename(dest_dir)
                notify("File sorted", f"{src_name} -> {dest_name}")
        except (OSError, shutil.Error) as exc:
            logger.error("Failed to move %s -> %s: %s", src, dest_dir, exc)
            try:
                fallback = DEFAULT_UNSORTED_DIR
                os.makedirs(fallback, exist_ok=True)
                fb_dst = os.path.join(fallback, os.path.basename(src))
                if os.path.exists(fb_dst):
                    base, ext = os.path.splitext(os.path.basename(src))
                    counter = 1
                    while os.path.exists(fb_dst):
                        fb_dst = os.path.join(
                            fallback, f"{base} ({counter}){ext}"
                        )
                        counter += 1
                self.watcher.mark_self_moved(fb_dst)
                shutil.move(src, fb_dst)
                self.history.record(src, fb_dst)
                logger.warning("Fallback: moved %s -> %s", src, fb_dst)
            except (OSError, shutil.Error) as fb_exc:
                logger.error(
                    "Fallback move also failed for %s: %s", src, fb_exc
                )

    # ------------------------------------------------------------------
    # Tray menu actions
    # ------------------------------------------------------------------

    def _add_folder_via_tray(self) -> None:
        """Handle 'Add folder to watch...' from the tray menu.

        Opens a directory picker, then prompts the user whether to whitelist
        all existing files in the folder or sort them now.  The folder is then
        added to monitoring.
        """
        t = threading.Thread(target=self._add_folder_flow, daemon=True)
        t.start()

    def _add_folder_flow(self) -> None:
        """Background thread: pick folder → configure destinations → start watching."""
        import tkinter as tk
        from tkinter import filedialog, messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        folder = filedialog.askdirectory(
            title="Choose a folder to watch",
            parent=root,
        )
        if not folder or not os.path.isdir(folder):
            root.destroy()
            return

        # Already monitored?
        if folder in self.config.monitored_folders:
            messagebox.showinfo(
                "Already watched",
                f"This folder is already being monitored:\n{folder}",
                parent=root,
            )
            root.destroy()
            return

        # Pick initial destination folders for this monitored folder
        dests: list[str] = []
        messagebox.showinfo(
            "Add destinations",
            "Now choose one or more destination folders for files from:\n"
            f"{folder}\n\n"
            "You will be prompted to pick each destination. Click Cancel when done.",
            parent=root,
        )
        while True:
            dest = filedialog.askdirectory(
                title=f"Destination folder for {os.path.basename(folder)} (Cancel to finish)",
                parent=root,
            )
            if not dest:
                break
            if dest not in dests:
                dests.append(dest)

        if not dests:
            messagebox.showwarning(
                "No destinations",
                "No destination folders were chosen — folder not added.",
                parent=root,
            )
            root.destroy()
            return

        # Check for existing files
        try:
            existing = [
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if os.path.isfile(os.path.join(folder, f))
                or (
                    self.config.get_setting("catch_folders", False)
                    and os.path.isdir(os.path.join(folder, f))
                )
            ]
        except OSError:
            existing = []

        whitelist_existing = False
        if existing:
            answer = messagebox.askyesnocancel(
                "Existing files found",
                f"{len(existing)} item(s) already in {os.path.basename(folder)}.\n\n"
                "Yes  — Add them all to the whitelist (ignore forever)\n"
                "No   — Sort them now using the main sorting screen\n"
                "Cancel — Abort",
                parent=root,
            )
            if answer is None:
                root.destroy()
                return
            whitelist_existing = bool(answer)

        root.destroy()

        # Persist configuration
        self.config.add_monitored_folder(folder, dests)
        if whitelist_existing:
            for item in existing:
                self.config.add_to_whitelist(os.path.basename(item))
            logger.info(
                "Whitelisted %d existing items in %s", len(existing), folder
            )
        else:
            # Queue existing files for sorting
            for item in existing:
                with self._lock:
                    self._batch_queue.append(item)
            count = len(self._batch_queue)
            self.tray.set_pending(True, count)

        # Start watching the new folder
        try:
            self.watcher.add_folder(folder)
        except Exception as exc:
            logger.error("Cannot watch %s: %s", folder, exc)

        self._update_tray_monitored_count()
        logger.info("Added monitored folder: %s -> %s", folder, dests)

        # If not whitelisted, open sorting screen immediately
        if not whitelist_existing and existing:
            self._process_batch_queue()

    def _quick_add_folder(self, folder_path: str, parent_monitored: str) -> None:
        """Add a detected directory as a new monitored folder (Quick Add Folder).

        Behaviour is controlled by three settings:

        * ``quick_add_inherit_destinations`` — if True, the new folder inherits
          the destination list of the monitored folder it was detected in.  If
          False, a destination picker dialog is shown.
        * ``quick_add_auto_whitelist`` — if True, the folder name is added to
          the whitelist so it is never re-prompted from the parent folder.
        * ``quick_add_auto_start_watch`` — if True, the watcher begins
          monitoring the new folder immediately.
        """
        # Already monitored?
        if folder_path in self.config.monitored_folders:
            logger.info("Quick Add: already monitored — %s", folder_path)
            return

        inherit = self.config.get_setting("quick_add_inherit_destinations", True)
        auto_whitelist = self.config.get_setting("quick_add_auto_whitelist", True)
        auto_watch = self.config.get_setting("quick_add_auto_start_watch", True)

        # Resolve destinations
        if inherit:
            dests = list(self.config.monitored_folders.get(parent_monitored, []))
        else:
            # Open a destination picker
            import tkinter as tk
            from tkinter import filedialog, messagebox

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            messagebox.showinfo(
                "Quick Add Folder — Destinations",
                f"Choose destination folders for:\n{folder_path}\n\n"
                "Click Cancel when finished.",
                parent=root,
            )
            dests = []
            while True:
                dest = filedialog.askdirectory(
                    title=f"Destination for {os.path.basename(folder_path)} (Cancel to finish)",
                    parent=root,
                )
                if not dest:
                    break
                if dest not in dests:
                    dests.append(dest)
            root.destroy()

            if not dests:
                logger.info(
                    "Quick Add: no destinations chosen, aborting — %s", folder_path
                )
                return

        self.config.add_monitored_folder(folder_path, dests)
        logger.info(
            "Quick Add: added %s -> %s", folder_path, dests
        )

        if auto_whitelist:
            self.config.add_to_whitelist(os.path.basename(folder_path))
            logger.info(
                "Quick Add: whitelisted folder name '%s'",
                os.path.basename(folder_path),
            )

        if auto_watch:
            try:
                self.watcher.add_folder(folder_path)
                logger.info("Quick Add: now watching %s", folder_path)
            except Exception as exc:
                logger.error("Quick Add: cannot watch %s: %s", folder_path, exc)

        self._update_tray_monitored_count()

    def _toggle_focus(self) -> None:
        self._focus_mode = not self._focus_mode
        self.config.set_setting("focus_mode", self._focus_mode)
        if not self._focus_mode:
            self._process_batch_queue()
        logger.info("Focus mode: %s", self._focus_mode)

    def _undo_last(self) -> None:
        result = self.history.undo_last()
        if result:
            # Mark the restored path so the watcher ignores it
            self.watcher.mark_self_moved(result[1])
            logger.info("Undone: %s -> %s", *result)
        else:
            logger.info("Nothing to undo.")

    def _show_settings(self) -> None:
        """Open the settings dialog."""
        t = threading.Thread(
            target=lambda: SettingsDialog(self.config).show(),
            daemon=True,
        )
        t.start()

    def _show_rules(self) -> None:
        """Open the rule management dialog."""
        t = threading.Thread(
            target=lambda: RulesDialog(self.rules, self.config).show(),
            daemon=True,
        )
        t.start()

    def _show_dashboard(self) -> None:
        """Open the enhanced dashboard window."""
        theme_name = self.config.get_setting("theme", "dark")
        t = threading.Thread(
            target=show_dashboard,
            args=(
                self.config, self.history, self._batch_queue,
                self._lock, self.watcher, theme_name,
            ),
            daemon=True,
        )
        t.start()

    def _process_batch_queue(self) -> None:
        """Process all files queued during focus mode.

        Respects the ``batch_mode_style`` setting (Q6.2):
        - ``'one-by-one'``: process each file individually
        - ``'batch-list'``: show a batch window
        """
        with self._lock:
            queue = list(self._batch_queue)
            self._batch_queue.clear()
        self.tray.set_pending(False)

        style = self.config.get_setting("batch_mode_style", "one-by-one")
        if style == "batch-list" and queue:
            theme_name = self.config.get_setting("theme", "dark")
            show_batch_list(
                self.config, self.rules, self.watcher, queue,
                theme_name, self._move_file,
            )
        else:
            for filepath in queue:
                if os.path.exists(filepath):
                    self._on_file_detected(filepath)


