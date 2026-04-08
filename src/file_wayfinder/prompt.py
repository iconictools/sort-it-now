"""User prompt dialogs for File Wayfinder (customtkinter-based)."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import filedialog
from typing import Any, Callable

import customtkinter as ctk

from file_wayfinder.themes import apply_ctk_appearance, get_theme

logger = logging.getLogger(__name__)

# ── Font helpers ──────────────────────────────────────────────────────

def _font(size: int = 12, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight=weight)


# ── SortPrompt ────────────────────────────────────────────────────────

class SortPrompt:
    """Non-intrusive popup asking the user where to send a file."""

    def __init__(
        self,
        filepath: str,
        destinations: list[str],
        on_done: Callable[[str, str | None, bool], None],
        theme: str = "dark",
        on_whitelist: Callable[[str], None] | None = None,
        on_quick_add: Callable[[str], None] | None = None,
        history: Any = None,
    ) -> None:
        """
        Parameters
        ----------
        filepath:
            Absolute path of the detected file.
        destinations:
            Ordered list of suggested destination folder paths.
        on_done:
            ``(filepath, chosen_destination_or_None, always_rule)``
        theme:
            Theme name (``'dark'`` or ``'light'``).
        on_whitelist:
            Called with a glob pattern when the user clicks "Add to whitelist".
        on_quick_add:
            Called with the folder path when the user clicks "Quick Add Folder"
            (only shown when the detected item is a directory).
        history:
            Optional History instance used for "Same as last time" suggestion.
        """
        self._filepath = filepath
        self._destinations = destinations
        self._on_done = on_done
        self._always = False
        self._theme_name = theme
        self._on_whitelist = on_whitelist
        self._on_quick_add = on_quick_add
        self._history = history

    def show(self) -> None:
        """Display the prompt (blocks until user responds)."""
        t = get_theme(self._theme_name)
        apply_ctk_appearance(self._theme_name)

        root = ctk.CTk()
        root.title("File Wayfinder")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        # Center on screen
        w, h = 460, 600
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        basename = os.path.basename(self._filepath)
        is_dir = os.path.isdir(self._filepath)

        # File size (skip for directories)
        size_str = ""
        if not is_dir:
            try:
                size_bytes = os.path.getsize(self._filepath)
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            except OSError:
                size_str = ""

        # ── Header ────────────────────────────────────────────────────
        header_text = "📁 New folder detected" if is_dir else "🗂 New file detected"
        ctk.CTkLabel(
            root,
            text=header_text,
            font=_font(16, "bold"),
            text_color=t["accent"],
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            root,
            text=basename,
            font=_font(12),
            wraplength=400,
        ).pack(pady=(0, 2))

        if size_str:
            ctk.CTkLabel(
                root,
                text=size_str,
                font=_font(10),
                text_color=t["muted"],
            ).pack(pady=(0, 4))

        # ── File preview ───────────────────────────────────────────────
        _, ext_lower = os.path.splitext(self._filepath)
        ext_lower = ext_lower.lower()
        _IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        _TEXT_EXTS = {
            ".txt", ".md", ".py", ".js", ".json", ".xml", ".csv", ".log",
        }
        _TYPE_LABELS = {
            ".pdf": "📄 PDF Document",
            ".zip": "🗜 ZIP Archive",
            ".rar": "🗜 RAR Archive",
            ".7z": "🗜 7z Archive",
            ".doc": "📝 Word Document",
            ".docx": "📝 Word Document",
            ".xls": "📊 Excel Spreadsheet",
            ".xlsx": "📊 Excel Spreadsheet",
            ".mp4": "🎬 Video File",
            ".mp3": "🎵 Audio File",
            ".exe": "⚙ Executable",
        }

        if ext_lower in _IMAGE_EXTS:
            try:
                from PIL import Image, ImageTk  # type: ignore[import]

                img = Image.open(self._filepath)
                try:
                    img.thumbnail((120, 120))
                    photo = ImageTk.PhotoImage(img)
                    lbl = tk.Label(root, image=photo, bg=t["bg"])
                    lbl.image = photo  # type: ignore[attr-defined]
                    lbl.pack(pady=(0, 4))
                finally:
                    img.close()
            except Exception:
                pass
        elif ext_lower in _TEXT_EXTS:
            try:
                with open(self._filepath, "r", encoding="utf-8",
                          errors="replace") as fh:
                    lines = []
                    for _ in range(3):
                        line = fh.readline()
                        if not line:
                            break
                        lines.append(line.rstrip())
                if lines:
                    preview_text = "\n".join(lines)
                    preview_box = ctk.CTkTextbox(
                        root, height=60, font=ctk.CTkFont(family="Courier", size=10),
                        state="normal",
                    )
                    preview_box.insert("end", preview_text)
                    preview_box.configure(state="disabled")
                    preview_box.pack(pady=(0, 4), padx=24, fill="x")
            except Exception:
                pass
        elif ext_lower in _TYPE_LABELS:
            ctk.CTkLabel(
                root,
                text=_TYPE_LABELS[ext_lower],
                font=_font(10),
                text_color=t["muted"],
            ).pack(pady=(0, 4))

        # ── Rename field ───────────────────────────────────────────────
        rename_frame = ctk.CTkFrame(root, fg_color="transparent")
        rename_frame.pack(fill="x", padx=24, pady=(0, 4))
        ctk.CTkLabel(
            rename_frame, text="✎ Rename:", font=_font(10),
        ).pack(side="left")
        rename_var = tk.StringVar(value=basename)
        name_without_ext, _ = os.path.splitext(basename)
        rename_entry = ctk.CTkEntry(
            rename_frame, textvariable=rename_var, font=_font(10),
            border_color=t["accent"],
        )
        rename_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))

        def _select_filename_stem(_event: object = None) -> None:
            rename_entry.select_range(0, len(name_without_ext))

        rename_entry.bind("<FocusIn>", _select_filename_stem)

        # ── Destination label ──────────────────────────────────────────
        ctk.CTkLabel(
            root,
            text="Where should it go?",
            font=_font(11, "bold"),
        ).pack(pady=(4, 0))

        # ── Scrollable destination buttons ─────────────────────────────
        scroll_frame = ctk.CTkScrollableFrame(root, height=180, fg_color="transparent")
        scroll_frame.pack(fill="x", padx=24, pady=8)

        chosen: list[str | None] = [None]

        def _choose(dest: str) -> None:
            chosen[0] = dest
            root.destroy()

        # "Same as last time" button
        last_dest: str | None = None
        if self._history is not None:
            _, ext = os.path.splitext(self._filepath)
            if ext:
                last_dest = self._history.last_dest_for_ext(ext)

        if last_dest is not None and os.path.isdir(last_dest) and last_dest in self._destinations:
            dest_name = os.path.basename(last_dest)
            _ld: str = last_dest
            ctk.CTkButton(
                scroll_frame,
                text=f"↑ Same as last ({dest_name})",
                fg_color=t["success"],
                text_color="#1e1e2e",
                hover_color=t["accent"],
                font=_font(11, "bold"),
                corner_radius=8,
                command=lambda d=_ld: _choose(d),  # type: ignore[misc]
            ).pack(fill="x", pady=(0, 6))

        for dest in self._destinations:
            label = os.path.basename(dest) if os.path.sep in dest else dest
            ctk.CTkButton(
                scroll_frame,
                text=label,
                fg_color=t["btn_bg"],
                text_color=t["btn_fg"],
                hover_color=t["accent"],
                font=_font(11),
                corner_radius=8,
                command=lambda d=dest: _choose(d),  # type: ignore[misc]
            ).pack(fill="x", pady=3)

        # "New folder..." button
        def _new_folder() -> None:
            folder = filedialog.askdirectory(
                title="Choose new destination folder"
            )
            if folder:
                _choose(folder)

        ctk.CTkButton(
            scroll_frame,
            text="📂 New folder…",
            fg_color=t["accent"],
            text_color="#1e1e2e",
            hover_color=t["btn_active"],
            font=_font(11, "bold"),
            corner_radius=8,
            command=_new_folder,
        ).pack(fill="x", pady=(8, 2))

        # ── Always checkbox ────────────────────────────────────────────
        always_var = tk.BooleanVar(value=False)
        _, ext = os.path.splitext(self._filepath)
        ctk.CTkCheckBox(
            root,
            text=f"Always send {ext} files here",
            variable=always_var,
            font=_font(10),
            fg_color=t["accent"],
            hover_color=t["btn_active"],
        ).pack(pady=(4, 4))

        # ── Bottom buttons ─────────────────────────────────────────────
        bottom_frame = ctk.CTkFrame(root, fg_color="transparent")
        bottom_frame.pack(pady=(0, 16))

        whitelisted = [False]
        quick_added = [False]

        # Quick Add Folder button — only shown when the detected item is a directory
        if is_dir and self._on_quick_add is not None:
            _fp = self._filepath
            _qa = self._on_quick_add

            def _do_quick_add() -> None:
                quick_added[0] = True
                root.destroy()
                _qa(_fp)

            ctk.CTkButton(
                bottom_frame,
                text="Quick Add Folder",
                fg_color=t["accent"],
                text_color="#1e1e2e",
                hover_color=t["btn_active"],
                font=_font(10, "bold"),
                corner_radius=8,
                command=_do_quick_add,
            ).pack(side="left", padx=4)

        # Add to whitelist button
        if self._on_whitelist is not None:
            def _add_to_whitelist() -> None:
                name = os.path.basename(self._filepath)
                if self._on_whitelist is not None:
                    self._on_whitelist(name)
                whitelisted[0] = True
                root.destroy()

            ctk.CTkButton(
                bottom_frame,
                text="Add to whitelist",
                fg_color=t["btn_bg"],
                text_color=t["btn_fg"],
                hover_color=t["muted"],
                font=_font(10),
                corner_radius=8,
                command=_add_to_whitelist,
            ).pack(side="left", padx=4)

        # Ignore button
        ctk.CTkButton(
            bottom_frame,
            text="Ignore",
            fg_color="transparent",
            text_color=t["muted"],
            hover_color=t["btn_bg"],
            font=_font(10),
            corner_radius=8,
            command=root.destroy,
        ).pack(side="left", padx=4)

        root.mainloop()

        # If quick-added, the on_quick_add callback handled everything
        if quick_added[0]:
            return

        # If whitelisted, skip callback — file stays in place
        if whitelisted[0]:
            self._on_done(self._filepath, None, False)
            return

        # If user renamed the file, apply the rename before callback
        new_name = rename_var.get().strip()
        if new_name and new_name != basename and os.path.exists(self._filepath):
            new_path = os.path.join(
                os.path.dirname(self._filepath), new_name
            )
            try:
                os.rename(self._filepath, new_path)
                self._filepath = new_path
            except OSError:
                pass

        self._on_done(self._filepath, chosen[0], always_var.get())


# ── SetupWizard ───────────────────────────────────────────────────────

class SetupWizard:
    """First-run wizard to configure monitored folders and destinations."""

    def __init__(self, theme: str = "dark") -> None:
        self.result: dict[str, list[str]] = {}
        self._root: ctk.CTk | None = None
        self._theme_name = theme

    def run(self) -> dict[str, list[str]]:
        """Show the wizard and return ``{folder: [destinations]}``."""
        t = get_theme(self._theme_name)
        apply_ctk_appearance(self._theme_name)

        root = ctk.CTk()
        self._root = root
        root.title("File Wayfinder — Setup")
        root.resizable(False, False)

        w, h = 560, 520
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        ctk.CTkLabel(
            root,
            text="🗂 File Wayfinder — Setup",
            font=_font(18, "bold"),
            text_color=t["accent"],
        ).pack(pady=(24, 4))
        ctk.CTkLabel(
            root,
            text="Choose folders to monitor and their destination folders.",
            font=_font(11),
            text_color=t["muted"],
        ).pack(pady=(0, 16))

        # Scrollable list of configured folders
        scroll_frame = ctk.CTkScrollableFrame(root, height=240)
        scroll_frame.pack(fill="x", padx=24, pady=4)
        scroll_frame.grid_columnconfigure(0, weight=1)

        folders_data: dict[str, list[str]] = {}
        row_labels: list[ctk.CTkLabel] = []

        def _refresh_list() -> None:
            for lbl in row_labels:
                lbl.destroy()
            row_labels.clear()
            for folder, dests in folders_data.items():
                dest_names = ", ".join(os.path.basename(d) for d in dests)
                text = f"  {os.path.basename(folder)}  →  {dest_names}\n  {folder}"
                lbl = ctk.CTkLabel(
                    scroll_frame,
                    text=text,
                    font=_font(11),
                    anchor="w",
                    justify="left",
                )
                lbl.pack(fill="x", pady=4, padx=4)
                row_labels.append(lbl)

        def _add_folder() -> None:
            folder = filedialog.askdirectory(title="Select folder to monitor")
            if not folder:
                return
            dests: list[str] = []
            while True:
                dest = filedialog.askdirectory(
                    title=f"Add destination for {os.path.basename(folder)} (cancel to finish)",
                )
                if not dest:
                    break
                dests.append(dest)
            if dests:
                folders_data[folder] = dests
                _refresh_list()

        def _done() -> None:
            self.result = folders_data
            root.destroy()

        btn_frame = ctk.CTkFrame(root, fg_color="transparent")
        btn_frame.pack(pady=16)
        ctk.CTkButton(
            btn_frame,
            text="+ Add Folder",
            fg_color=t["accent"],
            text_color="#1e1e2e",
            hover_color=t["btn_active"],
            font=_font(12, "bold"),
            corner_radius=10,
            command=_add_folder,
        ).pack(side="left", padx=10)
        ctk.CTkButton(
            btn_frame,
            text="Done ✓",
            fg_color=t["btn_bg"],
            text_color=t["btn_fg"],
            hover_color=t["accent"],
            font=_font(12),
            corner_radius=10,
            command=_done,
        ).pack(side="left", padx=10)

        root.mainloop()
        return self.result


# ── CLI setup ─────────────────────────────────────────────────────────

def cli_setup() -> dict[str, list[str]]:
    """CLI-based setup questionnaire (alternative to GUI wizard).

    Returns ``{folder: [destinations]}`` or empty dict if cancelled.
    """
    print("\n=== File Wayfinder -- CLI Setup ===\n")
    folders: dict[str, list[str]] = {}

    while True:
        folder = input(
            "Folder to monitor (press Enter to finish): "
        ).strip()
        if not folder:
            break
        if not os.path.isdir(folder):
            print(f"  Warning: '{folder}' does not exist.")
            cont = input("  Add anyway? (y/n): ").strip().lower()
            if cont != "y":
                continue

        dests: list[str] = []
        while True:
            dest = input(
                f"  Destination for '{os.path.basename(folder)}' "
                "(press Enter to finish): "
            ).strip()
            if not dest:
                break
            dests.append(dest)

        if dests:
            folders[folder] = dests
            print(f"  Added: {folder} -> {', '.join(dests)}")

    if folders:
        print(f"\nConfigured {len(folders)} folder(s).")
    else:
        print("\nNo folders configured.")
    return folders
