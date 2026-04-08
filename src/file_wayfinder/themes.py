"""Theme management for File Wayfinder.

Supports dark and light themes for all tkinter / customtkinter windows.
"""

from __future__ import annotations

# ── Theme definitions ────────────────────────────────────────────────

_DARK: dict[str, str] = {
    "bg": "#1e1e2e",
    "fg": "#cdd6f4",
    "accent": "#89b4fa",
    "btn_bg": "#313244",
    "btn_fg": "#cdd6f4",
    "btn_active": "#89b4fa",
    "muted": "#6c7086",
    "danger": "#f38ba8",
    "success": "#a6e3a1",
    "entry_bg": "#313244",
    "entry_fg": "#cdd6f4",
    "list_bg": "#181825",
    "list_fg": "#cdd6f4",
    "list_select_bg": "#313244",
    "list_select_fg": "#89b4fa",
}

_LIGHT: dict[str, str] = {
    "bg": "#eff1f5",
    "fg": "#4c4f69",
    "accent": "#1e66f5",
    "btn_bg": "#ccd0da",
    "btn_fg": "#4c4f69",
    "btn_active": "#1e66f5",
    "muted": "#9ca0b0",
    "danger": "#d20f39",
    "success": "#40a02b",
    "entry_bg": "#e6e9ef",
    "entry_fg": "#4c4f69",
    "list_bg": "#dce0e8",
    "list_fg": "#4c4f69",
    "list_select_bg": "#ccd0da",
    "list_select_fg": "#1e66f5",
}

THEMES: dict[str, dict[str, str]] = {"dark": _DARK, "light": _LIGHT}


def get_theme(name: str) -> dict[str, str]:
    """Return the color dictionary for *name* (``'dark'`` or ``'light'``)."""
    return THEMES.get(name, _DARK)


def apply_ctk_appearance(theme_name: str) -> None:
    """Configure customtkinter global appearance to match *theme_name*.

    Safe to call even if customtkinter is not installed (no-op in that case).
    """
    try:
        import customtkinter as ctk  # type: ignore[import]

        mode = "Dark" if theme_name == "dark" else "Light"
        ctk.set_appearance_mode(mode)
        ctk.set_default_color_theme("blue")
    except Exception:
        pass
