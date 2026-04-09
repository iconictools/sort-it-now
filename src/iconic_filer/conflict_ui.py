"""Conflict resolution UI for Iconic File Filer.

When a file already exists at the destination, presents the user with
options to overwrite, rename, or skip.
"""

from __future__ import annotations

import datetime
import logging
import os
from typing import TYPE_CHECKING

import customtkinter as ctk

from iconic_filer.themes import apply_ctk_appearance, get_theme

if TYPE_CHECKING:
    from iconic_filer.config import Config

logger = logging.getLogger(__name__)


def resolve_conflict(
    src: str,
    dst: str,
    config: Config,
) -> str | None:
    """Show a conflict dialog and return the resolved destination path.

    The behaviour is controlled by the ``conflict_resolution`` setting:
    - ``"rename"``    — silently rename the incoming file (adds `` (N)`` suffix)
    - ``"overwrite"`` — silently overwrite the existing file
    - ``"skip"``      — silently skip the move (returns *None*)
    - ``"ask"``       — show an interactive dialog (original behaviour)

    Returns *None* if the file should be skipped.  Otherwise returns the
    final destination path (possibly renamed).
    """
    resolution = config.get_setting("conflict_resolution", "rename")

    if resolution == "rename":
        base, ext = os.path.splitext(os.path.basename(dst))
        dest_dir = os.path.dirname(dst)
        counter = 1
        new_dst = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        while os.path.exists(new_dst):
            counter += 1
            new_dst = os.path.join(dest_dir, f"{base} ({counter}){ext}")
        return new_dst

    if resolution == "overwrite":
        return dst

    if resolution == "skip":
        return None

    # "ask" — fall through to the interactive dialog below.
    theme_name = config.get_setting("theme", "dark")
    t = get_theme(theme_name)
    apply_ctk_appearance(theme_name)

    result: list[str | None] = [None]

    root = ctk.CTk()
    root.title("Iconic File Filer — File Conflict")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    w, h = 460, 320
    sx = root.winfo_screenwidth() // 2 - w // 2
    sy = root.winfo_screenheight() // 2 - h // 2
    root.geometry(f"{w}x{h}+{sx}+{sy}")

    basename = os.path.basename(dst)

    ctk.CTkLabel(
        root,
        text="⚠ File already exists",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color=t["danger"],
    ).pack(pady=(20, 4))

    ctk.CTkLabel(
        root,
        text=f'"{basename}" already exists at the destination.',
        font=ctk.CTkFont(size=11),
        wraplength=420,
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

        ctk.CTkLabel(
            root,
            text=f"New: {_fmt(src_size)}    Existing: {_fmt(dst_size)}",
            font=ctk.CTkFont(size=10),
            text_color=t["muted"],
        ).pack(pady=(0, 4))
    except OSError:
        pass

    try:
        src_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(src))
        dst_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(dst))
        fmt = "%Y-%m-%d %H:%M"
        ctk.CTkLabel(
            root,
            text=f"Modified — New: {src_mtime.strftime(fmt)}    Existing: {dst_mtime.strftime(fmt)}",
            font=ctk.CTkFont(size=10),
            text_color=t["muted"],
        ).pack(pady=(0, 12))
    except OSError:
        pass

    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(pady=12)

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

    ctk.CTkButton(
        btn_frame,
        text="Overwrite",
        fg_color=t["danger"],
        text_color="#ffffff",
        hover_color="#c9374a",
        font=ctk.CTkFont(size=11, weight="bold"),
        corner_radius=8,
        width=110,
        command=_overwrite,
    ).pack(side="left", padx=6)

    ctk.CTkButton(
        btn_frame,
        text="Rename",
        fg_color=t["accent"],
        text_color="#1e1e2e",
        hover_color=t["btn_active"],
        font=ctk.CTkFont(size=11, weight="bold"),
        corner_radius=8,
        width=110,
        command=_rename,
    ).pack(side="left", padx=6)

    ctk.CTkButton(
        btn_frame,
        text="Skip",
        fg_color=t["btn_bg"],
        text_color=t["btn_fg"],
        hover_color=t["muted"],
        font=ctk.CTkFont(size=11),
        corner_radius=8,
        width=110,
        command=_skip,
    ).pack(side="left", padx=6)

    root.mainloop()
    return result[0]
