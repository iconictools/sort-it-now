"""Main application orchestrator for Sort It Now."""

from __future__ import annotations

import logging
import os
import shutil
import threading

from sort_it_now.classifier import suggest_destinations
from sort_it_now.config import Config
from sort_it_now.constants import DEFAULT_UNSORTED_DIR
from sort_it_now.history import History
from sort_it_now.prompt import SortPrompt, SetupWizard
from sort_it_now.rules import Rules
from sort_it_now.tray import TrayIcon
from sort_it_now.watcher import FolderWatcher

logger = logging.getLogger(__name__)


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
        )
        self.tray = TrayIcon(
            on_open_dashboard=self._show_dashboard,
            on_toggle_focus=self._toggle_focus,
            on_undo=self._undo_last,
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
                "Missing monitored folders: %s — they will be skipped.",
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

        logger.info("Sort It Now is running.")
        # Tray icon runs on the main thread (required by OS)
        try:
            self.tray.start()
        finally:
            self.watcher.stop()
            self.history.close()

    def _quit(self) -> None:
        logger.info("Shutting down...")
        self.watcher.stop()
        self.history.close()

    # ------------------------------------------------------------------
    # File event handling
    # ------------------------------------------------------------------

    def _on_file_detected(self, filepath: str) -> None:
        """Called by the watcher when a new/stable file is detected."""
        logger.info("Detected: %s", filepath)

        if self._focus_mode or self.config.get_setting("batch_mode", False):
            with self._lock:
                self._batch_queue.append(filepath)
            self.tray.set_pending(True)
            return

        # Check auto-rules
        if self.config.get_setting("auto_learn", True):
            auto_dest = self.rules.get_auto_destination(filepath)
            if auto_dest and os.path.isdir(auto_dest):
                self._move_file(filepath, auto_dest)
                return

        # Determine which monitored folder this file belongs to
        parent = os.path.dirname(filepath)
        destinations = self.config.monitored_folders.get(parent, [])
        if not destinations:
            # Try to find a matching monitored folder
            for mf, dests in self.config.monitored_folders.items():
                if filepath.startswith(mf):
                    destinations = dests
                    break

        if not destinations:
            logger.debug("No destinations configured for %s", filepath)
            return

        ordered = suggest_destinations(
            filepath, destinations, self.rules.extension_map
        )

        # Show prompt on the main thread via threading
        prompt = SortPrompt(filepath, ordered, self._on_prompt_done)
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
        threshold = self.config.get_setting("auto_learn_threshold", 3)
        self.rules.record_action(filepath, destination, threshold=threshold)

        if always:
            _, ext = os.path.splitext(filepath)
            if ext:
                self.rules.set_rule(ext, destination)
                logger.info("Auto-rule created: %s -> %s", ext, destination)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _move_file(self, src: str, dest_dir: str) -> None:
        """Move *src* into *dest_dir*, recording the action.

        On failure, falls back to an "unsorted" folder so files are never lost.
        """
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dst = os.path.join(dest_dir, os.path.basename(src))

            # Avoid overwriting
            if os.path.exists(dst):
                base, ext = os.path.splitext(os.path.basename(src))
                counter = 1
                while os.path.exists(dst):
                    dst = os.path.join(dest_dir, f"{base} ({counter}){ext}")
                    counter += 1

            self.watcher.mark_self_moved(dst)
            shutil.move(src, dst)
            self.history.record(src, dst)
            logger.info("Moved %s -> %s", src, dst)
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

    def _show_dashboard(self) -> None:
        """Open a simple dashboard window showing pending & recent items."""
        t = threading.Thread(target=self._dashboard_window, daemon=True)
        t.start()

    def _dashboard_window(self) -> None:
        import tkinter as tk

        root = tk.Tk()
        root.title("Sort It Now — Dashboard")
        root.configure(bg="#1e1e2e")
        root.geometry("500x400")

        tk.Label(
            root,
            text="📋 Recent Actions",
            bg="#1e1e2e",
            fg="#89b4fa",
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(16, 8))

        recent = self.history.recent(15)
        for action in recent:
            status = "↩️" if action["undone"] else "✅"
            src_name = os.path.basename(action["src_path"])
            dst_name = os.path.basename(os.path.dirname(action["dst_path"]))
            text = f"{status}  {src_name}  →  {dst_name}"
            tk.Label(
                root,
                text=text,
                bg="#1e1e2e",
                fg="#cdd6f4",
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(fill="x", padx=24, pady=1)

        with self._lock:
            pending = len(self._batch_queue)
        if pending:
            tk.Label(
                root,
                text=f"\n⏳ {pending} file(s) pending (focus mode)",
                bg="#1e1e2e",
                fg="#f38ba8",
                font=("Segoe UI", 10),
            ).pack(pady=8)

        root.mainloop()

    def _process_batch_queue(self) -> None:
        """Process all files queued during focus mode."""
        with self._lock:
            queue = list(self._batch_queue)
            self._batch_queue.clear()
        self.tray.set_pending(False)
        for filepath in queue:
            if os.path.exists(filepath):
                self._on_file_detected(filepath)
