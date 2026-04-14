"""In-app manual and welcome UI for Iconic File Filer."""

from __future__ import annotations

import customtkinter as ctk

from iconic_filer.themes import apply_ctk_appearance, get_theme


def _font(size: int = 12, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight=weight)


def show_manual(theme_name: str = "dark") -> None:
    """Show a compact in-app manual."""
    t = get_theme(theme_name)
    apply_ctk_appearance(theme_name)

    root = ctk.CTk()
    root.title("Iconic File Filer — Manual")
    root.geometry("640x560")
    root.minsize(540, 460)
    root.attributes("-topmost", True)
    root.lift()
    root.after(300, lambda: root.attributes("-topmost", False))

    ctk.CTkLabel(
        root,
        text="📘 Iconic File Filer Manual",
        font=_font(18, "bold"),
        text_color=t["accent"],
    ).pack(pady=(18, 6))
    ctk.CTkLabel(
        root,
        text="How to set up and use the app from start to finish.",
        font=_font(11),
        text_color=t["muted"],
    ).pack(pady=(0, 10))

    body = ctk.CTkScrollableFrame(root)
    body.pack(fill="both", expand=True, padx=16, pady=(0, 10))

    sections = [
        (
            "First 2 minutes (quick start)",
            "1) Tray → Folder setup...  2) Add a watched folder  3) Add one or more destinations  "
            "4) Drop a test file into the watched folder and choose a destination in the prompt.",
        ),
        (
            "1) Folder setup",
            "Use Tray → Folder setup... to configure watched folders on the left and destination folders on the right.",
        ),
        (
            "2) Sorting flow",
            "When files arrive, you get a prompt with destination suggestions. Pick one destination to move the file quickly.",
        ),
        (
            "3) Pause / resume",
            "Double-click the tray icon (or use the menu) to pause sorting prompts globally. The tray icon turns red while paused.",
        ),
        (
            "4) Activity & queue",
            "Open Activity & Queue from the tray to review recent activity and pending files collected while paused.",
        ),
        (
            "5) Sorting rules",
            "Open Sorting Rules... to set extension/pattern routing. Matching files are auto-sorted before prompts appear.",
        ),
        (
            "6) Troubleshooting",
            "If a folder disappears, the app skips it and keeps running. Re-open Folder setup... to update watched folders.",
        ),
    ]

    for title, text in sections:
        card = ctk.CTkFrame(body, corner_radius=8)
        card.pack(fill="x", padx=4, pady=4)
        ctk.CTkLabel(
            card,
            text=title,
            anchor="w",
            justify="left",
            font=_font(13, "bold"),
            text_color=t["accent"],
        ).pack(fill="x", padx=12, pady=(10, 3))
        ctk.CTkLabel(
            card,
            text=text,
            anchor="w",
            justify="left",
            wraplength=580,
            font=_font(11),
            text_color=t["btn_fg"],
        ).pack(fill="x", padx=12, pady=(0, 10))

    ctk.CTkButton(
        root,
        text="Close",
        width=90,
        height=34,
        command=root.destroy,
        fg_color=t["btn_bg"],
        text_color=t["btn_fg"],
        hover_color=t["btn_active"],
    ).pack(pady=(0, 14))

    root.mainloop()


def show_welcome(theme_name: str = "dark", monitored_count: int = 0) -> str:
    """Show startup welcome screen and return chosen action.

    Returns one of: ``"setup"``, ``"manual"``, ``"tray"``.
    """
    t = get_theme(theme_name)
    apply_ctk_appearance(theme_name)

    action = {"value": "tray"}
    root = ctk.CTk()
    root.title("Iconic File Filer — Welcome")
    root.geometry("560x340")
    root.resizable(False, False)

    ctk.CTkLabel(
        root,
        text="👋 Welcome to Iconic File Filer",
        font=_font(19, "bold"),
        text_color=t["accent"],
    ).pack(pady=(22, 8))

    status = (
        f"You're currently watching {monitored_count} folder{'s' if monitored_count != 1 else ''}."
        if monitored_count
        else "No folders are currently configured."
    )
    ctk.CTkLabel(
        root,
        text=status,
        font=_font(12),
        text_color=t["btn_fg"],
    ).pack(pady=(0, 6))
    ctk.CTkLabel(
        root,
        text="Open setup to configure watched folders and destinations, or start directly in tray.",
        font=_font(10),
        text_color=t["muted"],
        wraplength=510,
    ).pack(pady=(0, 16))

    def _set_action(name: str) -> None:
        action["value"] = name
        root.destroy()

    btns = ctk.CTkFrame(root, fg_color="transparent")
    btns.pack(pady=8)

    ctk.CTkButton(
        btns,
        text="Folder setup",
        command=lambda: _set_action("setup"),
        fg_color=t["accent"],
        text_color=t["bg"],
        hover_color=t["btn_active"],
        width=140,
    ).pack(side="left", padx=8)
    ctk.CTkButton(
        btns,
        text="Open manual",
        command=lambda: _set_action("manual"),
        fg_color=t["btn_bg"],
        text_color=t["btn_fg"],
        hover_color=t["btn_active"],
        width=120,
    ).pack(side="left", padx=8)
    ctk.CTkButton(
        btns,
        text="Start in tray",
        command=lambda: _set_action("tray"),
        fg_color=t["btn_bg"],
        text_color=t["btn_fg"],
        hover_color=t["btn_active"],
        width=120,
    ).pack(side="left", padx=8)

    root.mainloop()
    return action["value"]
