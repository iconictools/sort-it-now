"""User prompt dialogs for File Wayfinder (tkinter-based)."""

from __future__ import annotations

import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable

from file_wayfinder.themes import get_theme

logger = logging.getLogger(__name__)


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
        """
        self._filepath = filepath
        self._destinations = destinations
        self._on_done = on_done
        self._always = False
        self._theme_name = theme
        self._on_whitelist = on_whitelist
        self._on_quick_add = on_quick_add

    def show(self) -> None:
        """Display the prompt (blocks until user responds)."""
        t = get_theme(self._theme_name)

        root = tk.Tk()
        root.title("File Wayfinder")
        root.configure(bg=t["bg"])
        root.attributes("-topmost", True)
        root.resizable(False, False)

        # Center on screen
        w, h = 420, 540
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

        # Header
        header_text = "New folder detected" if is_dir else "New file detected"
        tk.Label(
            root,
            text=header_text,
            bg=t["bg"],
            fg=t["accent"],
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(16, 4))
        tk.Label(
            root,
            text=basename,
            bg=t["bg"],
            fg=t["fg"],
            font=("Segoe UI", 11),
            wraplength=380,
        ).pack(pady=(0, 2))
        if size_str:
            tk.Label(
                root,
                text=size_str,
                bg=t["bg"],
                fg=t["muted"],
                font=("Segoe UI", 9),
            ).pack(pady=(0, 4))

        # -- File preview --
        _, ext_lower = os.path.splitext(self._filepath)
        ext_lower = ext_lower.lower()
        _IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        _TEXT_EXTS = {
            ".txt", ".md", ".py", ".js", ".json", ".xml", ".csv", ".log",
        }
        _TYPE_LABELS = {
            ".pdf": "PDF Document",
            ".zip": "ZIP Archive",
            ".rar": "RAR Archive",
            ".7z": "7z Archive",
            ".doc": "Word Document",
            ".docx": "Word Document",
            ".xls": "Excel Spreadsheet",
            ".xlsx": "Excel Spreadsheet",
            ".mp4": "Video File",
            ".mp3": "Audio File",
            ".exe": "Executable",
        }

        if ext_lower in _IMAGE_EXTS:
            try:
                from PIL import Image, ImageTk

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
                    tk.Label(
                        root,
                        text=preview_text,
                        bg=t["list_bg"],
                        fg=t["list_fg"],
                        font=("Consolas", 8),
                        justify="left",
                        anchor="w",
                        wraplength=380,
                    ).pack(pady=(0, 4), padx=24, fill="x")
            except Exception:
                pass
        elif ext_lower in _TYPE_LABELS:
            tk.Label(
                root,
                text=_TYPE_LABELS[ext_lower],
                bg=t["bg"],
                fg=t["muted"],
                font=("Segoe UI", 9),
            ).pack(pady=(0, 4))

        # -- Rename field --
        rename_frame = tk.Frame(root, bg=t["bg"])
        rename_frame.pack(fill="x", padx=24, pady=(0, 4))
        tk.Label(
            rename_frame, text="✎ Rename:",
            bg=t["bg"], fg=t["fg"], font=("Segoe UI", 9),
        ).pack(side="left")
        rename_var = tk.StringVar(value=basename)
        name_without_ext, _ = os.path.splitext(basename)
        # Use a slightly distinct background to signal editability
        rename_bg = t.get("accent_muted", t["list_bg"])
        rename_entry = tk.Entry(
            rename_frame, textvariable=rename_var,
            bg=rename_bg, fg=t["entry_fg"], font=("Segoe UI", 9),
        )
        rename_entry.pack(side="left", fill="x", expand=True, padx=(4, 0))

        def _select_filename_stem(_event: object = None) -> None:
            rename_entry.selection_range(0, len(name_without_ext))

        rename_entry.bind("<FocusIn>", _select_filename_stem)

        tk.Label(
            root,
            text="Where should it go?",
            bg=t["bg"],
            fg=t["fg"],
            font=("Segoe UI", 10),
        ).pack()

        # Scrollable destination buttons -- show ALL destinations
        canvas = tk.Canvas(root, bg=t["bg"], highlightthickness=0, height=180)
        scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
        btn_frame = tk.Frame(canvas, bg=t["bg"])

        btn_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=btn_frame, anchor="nw", width=370)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Only show scrollbar if there are many destinations
        if len(self._destinations) > 6:
            scrollbar.pack(side="right", fill="y", padx=(0, 8))
        canvas.pack(pady=8, fill="x", padx=24)

        chosen: list[str | None] = [None]

        def _choose(dest: str) -> None:
            chosen[0] = dest
            root.destroy()

        for dest in self._destinations:
            label = os.path.basename(dest) if os.path.sep in dest else dest
            btn = tk.Button(
                btn_frame,
                text=label,
                bg=t["btn_bg"],
                fg=t["btn_fg"],
                activebackground=t["btn_active"],
                relief="flat",
                font=("Segoe UI", 10),
                command=lambda d=dest: _choose(d),  # type: ignore[misc]
            )
            btn.pack(fill="x", pady=2)

        # "New folder..." button
        def _new_folder() -> None:
            folder = filedialog.askdirectory(
                title="Choose new destination folder", parent=root
            )
            if folder:
                _choose(folder)

        tk.Button(
            btn_frame,
            text="New folder...",
            bg=t["accent"],
            fg=t["bg"],
            activebackground=t["btn_active"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            command=_new_folder,
        ).pack(fill="x", pady=(6, 2))

        # Always checkbox
        always_var = tk.BooleanVar(value=False)
        _, ext = os.path.splitext(self._filepath)
        chk = tk.Checkbutton(
            root,
            text=f"Always send {ext} files here",
            variable=always_var,
            bg=t["bg"],
            fg=t["fg"],
            selectcolor=t["btn_bg"],
            activebackground=t["bg"],
            activeforeground=t["fg"],
            font=("Segoe UI", 9),
        )
        chk.pack(pady=(8, 4))

        # Bottom buttons row
        bottom_frame = tk.Frame(root, bg=t["bg"])
        bottom_frame.pack(pady=(0, 8))

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

            tk.Button(
                bottom_frame,
                text="Quick Add Folder",
                bg=t["accent"],
                fg=t["bg"],
                activebackground=t["btn_active"],
                relief="flat",
                font=("Segoe UI", 9, "bold"),
                command=_do_quick_add,
            ).pack(side="left", padx=4)

        # Add to whitelist button
        if self._on_whitelist is not None:
            def _add_to_whitelist() -> None:
                # Whitelist by exact filename
                name = os.path.basename(self._filepath)
                if self._on_whitelist is not None:
                    self._on_whitelist(name)
                whitelisted[0] = True
                root.destroy()

            tk.Button(
                bottom_frame,
                text="Add to whitelist",
                bg=t["btn_bg"],
                fg=t["btn_fg"],
                activebackground=t["btn_active"],
                relief="flat",
                font=("Segoe UI", 9),
                command=_add_to_whitelist,
            ).pack(side="left", padx=4)

        # Ignore button
        tk.Button(
            bottom_frame,
            text="Ignore",
            bg=t["bg"],
            fg=t["muted"],
            activebackground=t["btn_bg"],
            relief="flat",
            font=("Segoe UI", 9),
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


class SetupWizard:
    """First-run wizard to configure monitored folders and destinations."""

    def __init__(self, theme: str = "dark") -> None:
        self.result: dict[str, list[str]] = {}
        self._root: tk.Tk | None = None
        self._theme_name = theme

    def run(self) -> dict[str, list[str]]:
        """Show the wizard and return ``{folder: [destinations]}``."""
        t = get_theme(self._theme_name)

        root = tk.Tk()
        self._root = root
        root.title("File Wayfinder -- Setup")
        root.configure(bg=t["bg"])
        root.resizable(False, False)

        w, h = 520, 480
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        tk.Label(
            root,
            text="File Wayfinder -- Setup",
            bg=t["bg"],
            fg=t["accent"],
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(20, 4))
        tk.Label(
            root,
            text="Add folders to monitor and their destination folders.",
            bg=t["bg"],
            fg=t["fg"],
            font=("Segoe UI", 10),
        ).pack(pady=(0, 12))

        # Monitored folders list
        list_frame = tk.Frame(root, bg=t["bg"])
        list_frame.pack(fill="both", expand=True, padx=20, pady=4)

        tree = ttk.Treeview(
            list_frame, columns=("destinations",), show="headings", height=8
        )
        tree.heading("#0", text="Folder")
        tree.heading("destinations", text="Destinations")
        tree.column("destinations", width=320)
        tree.pack(fill="both", expand=True)

        folders_data: dict[str, list[str]] = {}

        def _refresh_tree() -> None:
            for item in tree.get_children():
                tree.delete(item)
            for folder, dests in folders_data.items():
                tree.insert(
                    "", "end", values=(f"{folder}  ->  {', '.join(dests)}",)
                )

        def _add_folder() -> None:
            folder = filedialog.askdirectory(
                title="Select folder to monitor", parent=root
            )
            if not folder:
                return
            dests: list[str] = []
            while True:
                dest = filedialog.askdirectory(
                    title=f"Add destination for {os.path.basename(folder)} (cancel to finish)",
                    parent=root,
                )
                if not dest:
                    break
                dests.append(dest)
            if dests:
                folders_data[folder] = dests
                _refresh_tree()

        def _done() -> None:
            self.result = folders_data
            root.destroy()

        btn_frame = tk.Frame(root, bg=t["bg"])
        btn_frame.pack(pady=12)
        tk.Button(
            btn_frame,
            text="+ Add Folder",
            bg=t["accent"],
            fg=t["bg"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            command=_add_folder,
        ).pack(side="left", padx=8)
        tk.Button(
            btn_frame,
            text="Done",
            bg=t["btn_bg"],
            fg=t["btn_fg"],
            font=("Segoe UI", 10),
            relief="flat",
            command=_done,
        ).pack(side="left", padx=8)

        root.mainloop()
        return self.result


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
