"""Main application orchestrator for File Wayfinder."""

from __future__ import annotations

import datetime
import fnmatch
import logging
import os
import shutil
import sys
import threading

from file_wayfinder.achievements import Achievements
from file_wayfinder.classifier import suggest_destinations
from file_wayfinder.config import Config
from file_wayfinder.conflict_ui import resolve_conflict
from file_wayfinder.constants import DEFAULT_UNSORTED_DIR
from file_wayfinder.dashboard_ui import show_batch_list, show_dashboard
from file_wayfinder.duplicate import find_duplicate
from file_wayfinder.history import History
from file_wayfinder.ipc import IPCServer
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
        self._stop_event = threading.Event()
        self._health_notified: set[str] = set()
        # Serialise sort prompts: never show more than one at a time.
        self._prompt_semaphore = threading.Semaphore(1)
        # Active snooze timers so they can be cancelled on quit.
        self._snooze_timers: list[threading.Timer] = []

        self.achievements = Achievements(
            os.path.join(os.path.dirname(self.config.path), "achievements.db")
        )

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
            on_process_pending=self._process_batch_queue,
            on_quit=self._quit,
        )
        self._ipc_server = IPCServer(on_command=self._handle_ipc_command)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the application (blocks until quit)."""
        # First-run setup if no monitored folders
        first_run = not bool(self.config.monitored_folders)
        if first_run:
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

        # Sync focus mode state into the tray icon
        self.tray.set_focus_mode(self._focus_mode)

        # Scan existing files: always on first run so the user can sort what's
        # already there; on subsequent starts only when the setting is enabled.
        if first_run or self.config.get_setting("scan_existing_enabled", False):
            whitelist = self.config.get_whitelist()
            for folder in self.config.monitored_folders:
                if folder not in missing:
                    self.watcher.scan_existing(
                        folder, self._on_file_detected, whitelist,
                    )

        logger.info("File Wayfinder is running.")
        self._ipc_server.start()
        self._update_tray_monitored_count()
        # Start background cleanup-reminder polling thread
        cleanup_thread = threading.Thread(
            target=self._cleanup_reminder_loop, daemon=True
        )
        cleanup_thread.start()
        # Start background folder health monitor thread
        health_thread = threading.Thread(
            target=self._folder_health_loop, daemon=True
        )
        health_thread.start()
        # Tray icon runs on the main thread (required by OS)
        try:
            self.tray.start()
        finally:
            self._ipc_server.stop()
            self.watcher.stop()
            self.history.close()

    def _update_tray_monitored_count(self) -> None:
        """Update the tray tooltip to show how many folders are being monitored."""
        count = len(self.config.monitored_folders)
        self.tray.set_monitored_count(count)

    def _handle_ipc_command(self, command: str) -> None:
        """Handle a command sent by another File Wayfinder instance via IPC.

        Currently supported commands:
        ``ADD_FOLDER:<abs_path>`` — start watching the given folder, inheriting
        destinations from the closest already-watched parent (if any).
        """
        if command.startswith("ADD_FOLDER:"):
            folder = command[len("ADD_FOLDER:"):]
            if not folder or folder in self.config.monitored_folders:
                return
            # Find a parent folder to inherit destinations from (proper path containment)
            folder_abs = os.path.abspath(folder)
            parent_monitored = next(
                (
                    mf for mf in self.config.monitored_folders
                    if folder_abs == os.path.abspath(mf)
                    or folder_abs.startswith(os.path.abspath(mf) + os.sep)
                ),
                next(iter(self.config.monitored_folders), ""),
            )
            logger.info("IPC: adding folder %s (parent: %s)", folder, parent_monitored)
            threading.Thread(
                target=self._quick_add_folder,
                args=(folder, parent_monitored),
                daemon=True,
            ).start()

    def _quit(self) -> None:
        logger.info("Shutting down...")
        self._stop_event.set()
        for timer in self._snooze_timers:
            timer.cancel()
        self._snooze_timers.clear()
        self._ipc_server.stop()
        self.watcher.stop()
        self.history.close()
        self.achievements.close()

    def _cleanup_reminder_loop(self) -> None:
        """Background daemon: notify when a monitored folder has too many files."""
        notified_folders: set[str] = set()
        while not self._stop_event.wait(30):
            threshold = self.config.get_setting("cleanup_reminder_threshold", 0)
            if not threshold:
                notified_folders.clear()
                continue
            for folder in list(self.config.monitored_folders):
                if not os.path.isdir(folder):
                    continue
                try:
                    count = sum(
                        1 for name in os.listdir(folder)
                        if os.path.isfile(os.path.join(folder, name))
                        and not any(
                            fnmatch.fnmatch(name, pat)
                            for pat in self.config.ignore_patterns
                        )
                    )
                except OSError:
                    continue
                if count >= threshold:
                    if folder not in notified_folders:
                        folder_name = os.path.basename(folder)
                        notify(
                            "Cleanup reminder",
                            f"{count} unsorted files in {folder_name}",
                        )
                        logger.info(
                            "Cleanup reminder: %d files in %s", count, folder
                        )
                        notified_folders.add(folder)
                else:
                    notified_folders.discard(folder)

    def _folder_health_loop(self) -> None:
        """Background daemon: notify when a monitored folder becomes unavailable."""
        while not self._stop_event.wait(30):
            for folder in list(self.config.monitored_folders):
                if not os.path.isdir(folder):
                    if folder not in self._health_notified:
                        fallback = self.config.get_setting(
                            "notification_fallback", "toast-fallback"
                        )
                        notify(
                            "Folder unavailable",
                            f'"{os.path.basename(folder)}" is no longer accessible. '
                            "Check Settings to reconfigure.",
                            fallback_strategy=fallback,
                        )
                        self._health_notified.add(folder)
                        logger.warning("Folder unavailable: %s", folder)
                else:
                    self._health_notified.discard(folder)

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
        for folder_cfg in self.config.monitored_folders.values():
            for dest in folder_cfg.get("destinations", []):
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

        # Determine which monitored folder this file belongs to.
        # Always resolve via monitored_folders first — never call get_folder_destinations()
        # on an arbitrary path because Config._folder_data() auto-creates entries.
        parent = os.path.dirname(os.path.abspath(filepath))
        parent_monitored: str | None = None
        for mf in self.config.monitored_folders:
            mf_abs = os.path.abspath(mf)
            if parent == mf_abs or parent.startswith(mf_abs + os.sep):
                parent_monitored = mf
                break

        if not parent_monitored:
            logger.debug("No monitored folder for %s", filepath)
            return

        destinations = self.config.get_folder_destinations(parent_monitored)
        if not destinations:
            logger.debug("No destinations configured for %s", filepath)
            return

        # Merge global and per-folder extension maps (per-folder takes priority)
        folder_ext_map = self.config.get_folder_extension_map(parent_monitored)
        if folder_ext_map:
            merged_ext_map = {**self.rules.extension_map, **folder_ext_map}
        else:
            merged_ext_map = self.rules.extension_map

        # Check per-folder extension map as an auto-rule override
        _, file_ext = os.path.splitext(filepath)
        if folder_ext_map and file_ext and file_ext.lower() in folder_ext_map:
            auto_dest = folder_ext_map[file_ext.lower()]
            if os.path.isdir(auto_dest):
                self._move_file(filepath, auto_dest)
                return

        ordered = suggest_destinations(
            filepath, destinations, merged_ext_map
        )

        theme_name = self.config.get_setting("theme", "dark")
        always_rule_default = self.config.get_setting("prompt_always_rule", True)
        auto_accept_secs = self.config.get_setting("prompt_auto_accept_seconds", 0)

        # Capture for the closure — parent_monitored is already correctly resolved above.
        _pm = parent_monitored

        def _on_quick_add(folder_path: str) -> None:
            self._quick_add_folder(folder_path, _pm)

        def _on_save_destination(dest: str) -> None:
            self._add_permanent_destination(_pm, dest)

        # Show prompt serialised: acquire semaphore so only one prompt is
        # visible at a time.  Other detections wait their turn.
        prompt = SortPrompt(
            filepath, ordered, self._on_prompt_done,
            theme=theme_name,
            on_whitelist=self.config.add_to_whitelist,
            on_quick_add=_on_quick_add,
            history=self.history,
            on_snooze=lambda fp=filepath: self._on_snooze_file(fp),
            on_save_destination=_on_save_destination,
            always_rule_default=always_rule_default,
            auto_accept_seconds=auto_accept_secs,
        )

        def _show_serialised() -> None:
            with self._prompt_semaphore:
                prompt.show()

        t = threading.Thread(target=_show_serialised, daemon=True)
        t.start()

    def _on_prompt_done(
        self, filepath: str, destination: str | None, always: bool
    ) -> None:
        """Callback after the user responds to a prompt."""
        if destination is None:
            logger.info("Ignored: %s", filepath)
            return

        self._move_file(filepath, destination)

        _, ext = os.path.splitext(filepath)
        ext_lower = ext.lower()

        if always:
            if ext_lower:
                self.rules.set_rule(ext_lower, destination)
                logger.info("Auto-rule created: %s -> %s", ext_lower, destination)
        else:
            # Auto-learn: silently create a rule once the user has manually
            # sorted the same extension to the same destination N times.
            threshold = self.config.get_setting("auto_learn_threshold", 3)
            if threshold and ext_lower and ext_lower not in self.rules.extension_map:
                dest_abs = os.path.abspath(destination)
                count = sum(
                    1 for s, d in self.history.all_moves()
                    if os.path.splitext(s)[1].lower() == ext_lower
                    and os.path.abspath(os.path.dirname(d)) == dest_abs
                )
                if count >= threshold:
                    self.rules.set_rule(ext_lower, destination)
                    fallback = self.config.get_setting(
                        "notification_fallback", "log-only"
                    )
                    notify(
                        "Auto-rule created",
                        f"{ext_lower} files will now automatically go to "
                        f"{os.path.basename(destination)}",
                        fallback_strategy=fallback,
                    )
                    logger.info(
                        "Auto-rule created after %d sorts: %s -> %s",
                        count, ext_lower, destination,
                    )

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _move_file(self, src: str, dest_dir: str, source_folder: str | None = None) -> None:
        """Move *src* (file or folder) into *dest_dir*, recording the action.

        On failure, falls back to an "unsorted" folder so items are never lost.
        Uses conflict resolution UI when a file already exists.
        """
        try:
            os.makedirs(dest_dir, exist_ok=True)

            # Derive source_folder from monitored folders if not provided
            if source_folder is None:
                src_parent = os.path.dirname(os.path.abspath(src))
                for mf in self.config.monitored_folders:
                    mf_abs = os.path.abspath(mf)
                    if src_parent == mf_abs or src_parent.startswith(mf_abs + os.sep):
                        source_folder = mf
                        break

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
            self.history.record(src, dst, source_folder=source_folder)
            logger.info("Moved %s -> %s", src, dst)

            # Evaluate achievements
            try:
                newly = self.achievements.evaluate(self.history)
                for ach in newly:
                    notify(
                        f"Achievement unlocked: {ach.emoji} {ach.name}",
                        ach.description,
                        fallback_strategy=self.config.get_setting(
                            "notification_fallback", "toast-fallback"
                        ),
                    )
            except Exception:
                logger.debug("Achievement evaluation failed", exc_info=True)

            # Native notification (passes configured fallback strategy)
            if self.config.get_setting("native_notifications", True):
                src_name = os.path.basename(src)
                dest_name = os.path.basename(dest_dir)
                fallback = self.config.get_setting(
                    "notification_fallback", "toast-fallback"
                )
                notify(
                    "File sorted", f"{src_name} -> {dest_name}",
                    fallback_strategy=fallback,
                )
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
                self.history.record(src, fb_dst, source_folder=source_folder)
                logger.warning("Fallback: moved %s -> %s", src, fb_dst)
            except (OSError, shutil.Error) as fb_exc:
                logger.error(
                    "Fallback move also failed for %s: %s", src, fb_exc
                )

    # ------------------------------------------------------------------
    # Tray menu actions
    # ------------------------------------------------------------------

    def _on_snooze_file(self, filepath: str) -> None:
        """Re-queue *filepath* for prompting after the configured snooze delay."""
        snooze = max(1, self.config.get_setting("snooze_minutes", 30))
        delay = snooze * 60

        def _requeue() -> None:
            if os.path.exists(filepath):
                self._on_file_detected(filepath)
            else:
                logger.debug("Snoozed file no longer exists: %s", filepath)

        timer = threading.Timer(delay, _requeue)
        timer.daemon = True
        timer.start()
        with self._lock:
            self._snooze_timers.append(timer)
        logger.info("Snoozed %s for %d minutes", filepath, snooze)

    def _add_permanent_destination(
        self, monitored_folder: str, dest: str
    ) -> None:
        """Permanently add *dest* as a destination for *monitored_folder*."""
        current = list(self.config.get_folder_destinations(monitored_folder))
        if dest not in current:
            current.append(dest)
            self.config.set_destinations(monitored_folder, current)
            logger.info(
                "Added permanent destination %s for %s", dest, monitored_folder
            )

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

        sort_existing = True
        if existing:
            sort_existing = messagebox.askyesno(
                "Existing files found",
                f"{len(existing)} {'item' if len(existing) == 1 else 'items'} already in '{os.path.basename(folder)}'.\n\n"
                "Sort them now?\n\n"
                "Yes — Open sorting screen for each file\n"
                "No  — Ignore them (whitelist all existing files)",
                parent=root,
            )

        root.destroy()

        # Persist configuration
        self.config.add_monitored_folder(folder, dests)

        # Start watching the new folder immediately
        try:
            self.watcher.add_folder(folder)
        except Exception as exc:
            logger.error("Cannot watch %s: %s", folder, exc)

        self._update_tray_monitored_count()
        logger.info("Added monitored folder: %s -> %s", folder, dests)

        if existing:
            if sort_existing:
                # Queue all existing files and open the sorting screen immediately
                for item in existing:
                    with self._lock:
                        self._batch_queue.append(item)
                self._process_batch_queue()
            else:
                # Whitelist all so they are never prompted
                for item in existing:
                    self.config.add_to_whitelist(os.path.basename(item))
                logger.info(
                    "Whitelisted %d existing items in %s", len(existing), folder
                )

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
            dests = list(self.config.get_folder_destinations(parent_monitored))
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
        self.tray.set_focus_mode(self._focus_mode)
        if not self._focus_mode:
            self._process_batch_queue()
        logger.info("Focus mode: %s", self._focus_mode)

    def _undo_last(self) -> None:
        result = self.history.undo_last()
        if not result:
            logger.info("Nothing to undo.")
            return

        dst_path, src_path = result
        # Mark restored path so the watcher ignores it
        self.watcher.mark_self_moved(src_path)
        logger.info("Undone: %s -> %s", dst_path, src_path)

        # Check whether a rename happened during the move.
        dst_basename = os.path.basename(dst_path)
        src_basename = os.path.basename(src_path)
        if dst_basename == src_basename:
            return  # No rename — nothing more to do.

        strategy = self.config.get_setting("undo_restore_name", "ask")

        def _should_restore() -> bool:
            if strategy == "always":
                return True
            if strategy == "never":
                return False
            # "ask" — prompt the user
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            answer = messagebox.askyesno(
                "Undo rename?",
                f"The file was renamed during the move:\n\n"
                f"  Original name: {dst_basename}\n"
                f"  Current name:  {src_basename}\n\n"
                "Do you also want to restore the original filename?",
                parent=root,
            )
            root.destroy()
            return answer

        if _should_restore() and os.path.exists(src_path):
            restored = os.path.join(os.path.dirname(src_path), dst_basename)
            try:
                os.rename(src_path, restored)
                logger.info("Name restored: %s -> %s", src_basename, dst_basename)
            except OSError as exc:
                logger.warning("Could not restore filename: %s", exc)

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
            threading.Thread(
                target=show_batch_list,
                args=(self.config, self.rules, self.watcher, queue,
                      theme_name, self._move_file),
                daemon=True,
            ).start()
        else:
            for filepath in queue:
                if os.path.exists(filepath):
                    self._on_file_detected(filepath)


