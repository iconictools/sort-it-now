"""Conflict resolution UI for File Wayfinder.

When a file already exists at the destination, presents the user with
options to overwrite, rename, or skip.
"""

from __future__ import annotations

import datetime
import logging
import os
import tkinter as tk
from typing import TYPE_CHECKING

from file_wayfinder.themes import get_theme

if TYPE_CHECKING:
    from file_wayfinder.config import Config

logger = logging.getLogger(__name__)


def resolve_conflict(
    src: str,
    dst: str,
    config: Config,
) -> str | None:
    """Show a conflict dialog and return the resolved destination path.

    Returns *None* if the user chooses to skip.  Otherwise returns the
    final destination path (possibly renamed).
    """
    t = get_theme(config.get_setting("theme", "dark"))

    result: list[str | None] = [None]

    root = tk.Tk()
    root.title("File Wayfinder -- File Conflict")
    root.configure(bg=t["bg"])
    root.attributes("-topmost", True)
    root.resizable(False, False)

    w, h = 440, 300
    sx = root.winfo_screenwidth() // 2 - w // 2
    sy = root.winfo_screenheight() // 2 - h // 2
    root.geometry(f"{w}x{h}+{sx}+{sy}")

    basename = os.path.basename(dst)

    tk.Label(
        root,
        text="File already exists",
        bg=t["bg"], fg=t["danger"],
        font=("Segoe UI", 14, "bold"),
    ).pack(pady=(16, 4))
    tk.Label(
        root,
        text=f'"{basename}" already exists at the destination.',
        bg=t["bg"], fg=t["fg"],
        font=("Segoe UI", 10), wraplength=400,
    ).pack(pady=(0, 4))

    # File sizes
    try:
        src_size = os.path.getsize(src)
        dst_size = os.path.getsize(dst)

        def _fmt(s: int) -> str:
            if s < 1024:
                return f"{s} B"
            if s < 1024 * 1024:
                return f"{s / 1024:.1f} KB"
            return f"{s / (1024 * 1024):.1f} MB"

        tk.Label(
            root,
            text=f"New: {_fmt(src_size)}    Existing: {_fmt(dst_size)}",
            bg=t["bg"], fg=t["muted"], font=("Segoe UI", 9),
        ).pack(pady=(0, 12))
    except OSError:
        pass

    try:
        src_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(src))
        dst_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(dst))
        fmt = "%Y-%m-%d %H:%M"
        tk.Label(
            root,
            text=f"Modified — New: {src_mtime.strftime(fmt)}    Existing: {dst_mtime.strftime(fmt)}",
            bg=t["bg"], fg=t["muted"], font=("Segoe UI", 9),
        ).pack(pady=(0, 8))
    except OSError:
        pass

    btn_frame = tk.Frame(root, bg=t["bg"])
    btn_frame.pack(pady=8)

    def _overwrite() -> None:
        result[0] = dst
        root.destroy()

    def _rename() -> None:
        base, ext = os.path.splitext(basename)
        dest_dir = os.path.dirname(dst)
        counter = 1
        new_dst = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        while os.path.exists(new_dst):
            counter += 1
            new_dst = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        result[0] = new_dst
        root.destroy()

    def _skip() -> None:
        result[0] = None
        root.destroy()

    tk.Button(
        btn_frame, text="Overwrite", bg=t["danger"], fg="#ffffff",
        font=("Segoe UI", 10, "bold"), relief="flat",
        command=_overwrite, width=10,
    ).pack(side="left", padx=4)
    tk.Button(
        btn_frame, text="Rename", bg=t["accent"], fg=t["bg"],
        font=("Segoe UI", 10, "bold"), relief="flat",
        command=_rename, width=10,
    ).pack(side="left", padx=4)
    tk.Button(
        btn_frame, text="Skip", bg=t["btn_bg"], fg=t["btn_fg"],
        font=("Segoe UI", 10), relief="flat",
        command=_skip, width=10,
    ).pack(side="left", padx=4)

    root.mainloop()
    return result[0]
