"""User prompt dialogs for Sort It Now (tkinter-based)."""

import logging
import os
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable

logger = logging.getLogger(__name__)

# ── Colours / style ──────────────────────────────────────────────────
_BG = "#1e1e2e"
_FG = "#cdd6f4"
_ACCENT = "#89b4fa"
_BTN_BG = "#313244"
_BTN_FG = "#cdd6f4"


class SortPrompt:
    """Non-intrusive popup asking the user where to send a file."""

    def __init__(
        self,
        filepath: str,
        destinations: list[str],
        on_done: Callable[[str, str | None, bool], None],
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
        """
        self._filepath = filepath
        self._destinations = destinations
        self._on_done = on_done
        self._always = False

    def show(self) -> None:
        """Display the prompt (blocks until user responds)."""
        root = tk.Tk()
        root.title("Sort It Now")
        root.configure(bg=_BG)
        root.attributes("-topmost", True)
        root.resizable(False, False)

        # Center on screen
        w, h = 420, 360
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        basename = os.path.basename(self._filepath)

        # Header
        tk.Label(
            root,
            text="📥 New file detected",
            bg=_BG,
            fg=_ACCENT,
            font=("Segoe UI", 14, "bold"),
        ).pack(pady=(16, 4))
        tk.Label(
            root,
            text=basename,
            bg=_BG,
            fg=_FG,
            font=("Segoe UI", 11),
            wraplength=380,
        ).pack(pady=(0, 12))
        tk.Label(
            root,
            text="Where should it go?",
            bg=_BG,
            fg=_FG,
            font=("Segoe UI", 10),
        ).pack()

        # Destination buttons
        frame = tk.Frame(root, bg=_BG)
        frame.pack(pady=8, fill="x", padx=24)

        chosen: list[str | None] = [None]

        def _choose(dest: str) -> None:
            chosen[0] = dest
            root.destroy()

        for dest in self._destinations[:6]:  # Limit to 6 buttons
            label = os.path.basename(dest) if os.path.sep in dest else dest
            btn = tk.Button(
                frame,
                text=label,
                bg=_BTN_BG,
                fg=_BTN_FG,
                activebackground=_ACCENT,
                relief="flat",
                font=("Segoe UI", 10),
                command=lambda d=dest: _choose(d),
            )
            btn.pack(fill="x", pady=2)

        # Always checkbox
        always_var = tk.BooleanVar(value=False)
        _, ext = os.path.splitext(self._filepath)
        chk = tk.Checkbutton(
            root,
            text=f"Always send {ext} files here",
            variable=always_var,
            bg=_BG,
            fg=_FG,
            selectcolor=_BTN_BG,
            activebackground=_BG,
            activeforeground=_FG,
            font=("Segoe UI", 9),
        )
        chk.pack(pady=(8, 4))

        # Ignore button
        tk.Button(
            root,
            text="Ignore",
            bg=_BG,
            fg="#6c7086",
            activebackground=_BTN_BG,
            relief="flat",
            font=("Segoe UI", 9),
            command=root.destroy,
        ).pack(pady=(0, 8))

        root.mainloop()
        self._on_done(self._filepath, chosen[0], always_var.get())


class SetupWizard:
    """First-run wizard to configure monitored folders and destinations."""

    def __init__(self) -> None:
        self.result: dict[str, list[str]] = {}
        self._root: tk.Tk | None = None

    def run(self) -> dict[str, list[str]]:
        """Show the wizard and return ``{folder: [destinations]}``."""
        root = tk.Tk()
        self._root = root
        root.title("Sort It Now — Setup")
        root.configure(bg=_BG)
        root.resizable(False, False)

        w, h = 520, 480
        sx = root.winfo_screenwidth() // 2 - w // 2
        sy = root.winfo_screenheight() // 2 - h // 2
        root.geometry(f"{w}x{h}+{sx}+{sy}")

        tk.Label(
            root,
            text="🗂️ Sort It Now — Setup",
            bg=_BG,
            fg=_ACCENT,
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(20, 4))
        tk.Label(
            root,
            text="Add folders to monitor and their destination folders.",
            bg=_BG,
            fg=_FG,
            font=("Segoe UI", 10),
        ).pack(pady=(0, 12))

        # Monitored folders list
        list_frame = tk.Frame(root, bg=_BG)
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
                    "", "end", values=(f"{folder}  →  {', '.join(dests)}",)
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

        btn_frame = tk.Frame(root, bg=_BG)
        btn_frame.pack(pady=12)
        tk.Button(
            btn_frame,
            text="+ Add Folder",
            bg=_ACCENT,
            fg="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            command=_add_folder,
        ).pack(side="left", padx=8)
        tk.Button(
            btn_frame,
            text="Done",
            bg=_BTN_BG,
            fg=_BTN_FG,
            font=("Segoe UI", 10),
            relief="flat",
            command=_done,
        ).pack(side="left", padx=8)

        root.mainloop()
        return self.result
