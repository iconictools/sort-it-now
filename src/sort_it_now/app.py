"""Main application orchestrator for Sort It Now."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
import time

from sort_it_now.classifier import suggest_destinations
from sort_it_now.config import Config
from sort_it_now.conflict_ui import resolve_conflict
from sort_it_now.constants import DEFAULT_UNSORTED_DIR
from sort_it_now.history import History
from sort_it_now.prompt import SortPrompt, SetupWizard
from sort_it_now.rules import Rules
from sort_it_now.rules_ui import RulesDialog
from sort_it_now.settings_ui import SettingsDialog
from sort_it_now.themes import get_theme
from sort_it_now.tray import TrayIcon
from sort_it_now.watcher import FolderWatcher

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
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


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
            on_open_settings=self._show_settings,
            on_open_rules=self._show_rules,
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

        theme_name = self.config.get_setting("theme", "dark")

        # Show prompt on the main thread via threading
        prompt = SortPrompt(filepath, ordered, self._on_prompt_done,
                            theme=theme_name)
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
        Uses conflict resolution UI when a file already exists.
        """
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dst = os.path.join(dest_dir, os.path.basename(src))

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
        t = threading.Thread(target=self._dashboard_window, daemon=True)
        t.start()

    def _dashboard_window(self) -> None:
        import tkinter as tk

        theme = get_theme(self.config.get_setting("theme", "dark"))

        root = tk.Tk()
        root.title("Sort It Now -- Dashboard")
        root.configure(bg=theme["bg"])
        root.geometry("560x520")

        # Tab-like sections
        tk.Label(
            root,
            text="Dashboard",
            bg=theme["bg"], fg=theme["accent"],
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(16, 8))

        # -- Pending files --
        with self._lock:
            pending = len(self._batch_queue)
        if pending:
            tk.Label(
                root,
                text=f"Pending: {pending} file(s) in queue (focus mode)",
                bg=theme["bg"], fg=theme["danger"],
                font=("Segoe UI", 10),
            ).pack(pady=4)

        # -- Sorting stats (Q7.1b) --
        stats_frame = tk.Frame(root, bg=theme["bg"])
        stats_frame.pack(fill="x", padx=24, pady=4)

        total = self.history.total_count()
        today = self.history.count_since(time.time() - 86400)
        week = self.history.count_since(time.time() - 7 * 86400)

        tk.Label(
            stats_frame,
            text=f"Total sorted: {total}   |   Today: {today}   |   This week: {week}",
            bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10),
        ).pack(anchor="w")

        # -- Inbox Zero progress (Q7.1c) --
        if pending > 0 or today > 0:
            progress_frame = tk.Frame(root, bg=theme["bg"])
            progress_frame.pack(fill="x", padx=24, pady=4)
            processed = today - pending if today > pending else today
            ratio = max(0.0, processed / max(today, 1))
            bar_w = 400
            canvas = tk.Canvas(
                progress_frame, width=bar_w, height=20,
                bg=theme["list_bg"], highlightthickness=0,
            )
            canvas.pack(anchor="w")
            fill_w = int(bar_w * ratio)
            canvas.create_rectangle(
                0, 0, fill_w, 20, fill=theme["success"], outline=""
            )
            pct = int(ratio * 100)
            tk.Label(
                progress_frame,
                text=f"Inbox Zero: {pct}%",
                bg=theme["bg"], fg=theme["success"],
                font=("Segoe UI", 9),
            ).pack(anchor="w")

        # -- Rules summary (Q7.1d) --
        rules_count = len(self.rules.extension_map)
        tk.Label(
            root,
            text=f"Active rules: {rules_count}",
            bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 10),
        ).pack(padx=24, anchor="w", pady=(8, 4))

        # -- Undo history with clickable checkpoints (Q7.2) --
        tk.Label(
            root,
            text="Recent Actions (click to undo back to that point):",
            bg=theme["bg"], fg=theme["accent"],
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(12, 4), padx=24, anchor="w")

        history_frame = tk.Frame(root, bg=theme["bg"])
        history_frame.pack(fill="both", expand=True, padx=24, pady=4)

        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side="right", fill="y")

        history_list = tk.Listbox(
            history_frame,
            bg=theme["list_bg"], fg=theme["list_fg"],
            selectbackground=theme["list_select_bg"],
            selectforeground=theme["list_select_fg"],
            font=("Segoe UI", 9), relief="flat",
            yscrollcommand=scrollbar.set,
        )
        history_list.pack(fill="both", expand=True)
        scrollbar.config(command=history_list.yview)

        recent = self.history.recent(50)
        for action in recent:
            status = "[undone]" if action["undone"] else "[done]"
            src_name = os.path.basename(action["src_path"])
            dst_name = os.path.basename(os.path.dirname(action["dst_path"]))
            history_list.insert(
                "end", f"{status}  {src_name}  ->  {dst_name}"
            )

        def _undo_to_selected() -> None:
            sel = history_list.curselection()
            if not sel:
                return
            # Undo all actions from most recent up to (and including) selected
            idx = sel[0]
            actions_to_undo = recent[: idx + 1]
            undone_count = 0
            for action in actions_to_undo:
                if not action["undone"]:
                    result = self.history.undo_by_id(action["id"])
                    if result:
                        self.watcher.mark_self_moved(result[1])
                        undone_count += 1
            if undone_count:
                logger.info("Bulk undone %d action(s).", undone_count)
            # Refresh list
            history_list.delete(0, "end")
            refreshed = self.history.recent(50)
            for action in refreshed:
                status = "[undone]" if action["undone"] else "[done]"
                src_name = os.path.basename(action["src_path"])
                dst_name = os.path.basename(
                    os.path.dirname(action["dst_path"])
                )
                history_list.insert(
                    "end", f"{status}  {src_name}  ->  {dst_name}"
                )

        btn_frame = tk.Frame(root, bg=theme["bg"])
        btn_frame.pack(pady=8)
        tk.Button(
            btn_frame, text="Undo to selected",
            bg=theme["accent"], fg=theme["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat",
            command=_undo_to_selected,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame, text="Close",
            bg=theme["btn_bg"], fg=theme["btn_fg"],
            font=("Segoe UI", 10), relief="flat",
            command=root.destroy,
        ).pack(side="left", padx=4)

        root.mainloop()

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
            self._batch_list_window(queue)
        else:
            for filepath in queue:
                if os.path.exists(filepath):
                    self._on_file_detected(filepath)

    def _batch_list_window(self, queue: list[str]) -> None:
        """Show a batch processing window listing all pending files."""
        import tkinter as tk
        from tkinter import ttk

        theme = get_theme(self.config.get_setting("theme", "dark"))

        root = tk.Tk()
        root.title("Sort It Now -- Batch Processing")
        root.configure(bg=theme["bg"])
        root.geometry("600x400")

        tk.Label(
            root,
            text=f"Batch: {len(queue)} file(s) pending",
            bg=theme["bg"], fg=theme["accent"],
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(16, 8))

        # For each file, let user pick a destination
        canvas = tk.Canvas(root, bg=theme["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=theme["bg"])
        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw", width=560)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=16, pady=4)

        dest_vars: list[tuple[str, tk.StringVar]] = []

        # Collect all known destinations
        all_dests: list[str] = []
        for dests in self.config.monitored_folders.values():
            for d in dests:
                if d not in all_dests:
                    all_dests.append(d)

        if not all_dests:
            tk.Label(
                inner,
                text="No destinations configured. Add folders in Settings.",
                bg=theme["bg"], fg=theme["danger"], font=("Segoe UI", 10),
            ).pack(pady=8)

        for filepath in queue:
            if not os.path.exists(filepath):
                continue
            row = tk.Frame(inner, bg=theme["bg"])
            row.pack(fill="x", pady=2)

            tk.Label(
                row, text=os.path.basename(filepath),
                bg=theme["bg"], fg=theme["fg"], font=("Segoe UI", 9),
                width=30, anchor="w",
            ).pack(side="left")

            dest_var = tk.StringVar(value=all_dests[0] if all_dests else "")
            if all_dests:
                menu = ttk.Combobox(
                    row, textvariable=dest_var, values=all_dests,
                    state="readonly", width=30,
                )
                menu.pack(side="left", padx=4)
            dest_vars.append((filepath, dest_var))

        def _process_all() -> None:
            for filepath, var in dest_vars:
                dest = var.get()
                if dest and os.path.exists(filepath):
                    self._move_file(filepath, dest)
                    threshold = self.config.get_setting(
                        "auto_learn_threshold", 3
                    )
                    self.rules.record_action(
                        filepath, dest, threshold=threshold
                    )
            root.destroy()

        btn_frame = tk.Frame(root, bg=theme["bg"])
        btn_frame.pack(pady=8)
        tk.Button(
            btn_frame, text="Move All",
            bg=theme["accent"], fg=theme["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat",
            command=_process_all,
        ).pack(side="left", padx=4)
        tk.Button(
            btn_frame, text="Cancel",
            bg=theme["btn_bg"], fg=theme["btn_fg"],
            font=("Segoe UI", 10), relief="flat",
            command=root.destroy,
        ).pack(side="left", padx=4)

        root.mainloop()
