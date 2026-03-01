"""System tray icon for Sort It Now (pystray-based)."""

import logging
import os
import threading
from typing import Callable

from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)

# ── Icon drawing helpers ─────────────────────────────────────────────

def _create_icon_image(color: str = "#89b4fa", size: int = 64) -> Image.Image:
    """Draw a simple folder-shaped tray icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Folder body
    draw.rounded_rectangle(
        [4, 16, size - 4, size - 8], radius=6, fill=color
    )
    # Folder tab
    draw.rounded_rectangle(
        [4, 10, size // 2, 22], radius=4, fill=color
    )
    return img


def _icon_idle() -> Image.Image:
    return _create_icon_image("#89b4fa")


def _icon_pending() -> Image.Image:
    return _create_icon_image("#f38ba8")


# ── TrayIcon wrapper ─────────────────────────────────────────────────

class TrayIcon:
    """Manages the system-tray icon and its context menu.

    Parameters
    ----------
    on_open_dashboard:
        Called when the user clicks "Dashboard".
    on_toggle_focus:
        Called when the user toggles focus/snooze mode.
    on_undo:
        Called when the user clicks "Undo last".
    on_quit:
        Called when the user clicks "Quit".
    """

    def __init__(
        self,
        on_open_dashboard: Callable[[], None] | None = None,
        on_toggle_focus: Callable[[], None] | None = None,
        on_undo: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        self._on_dashboard = on_open_dashboard or (lambda: None)
        self._on_focus = on_toggle_focus or (lambda: None)
        self._on_undo = on_undo or (lambda: None)
        self._on_quit = on_quit or (lambda: None)
        self._icon: pystray.Icon | None = None
        self._pending = False

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Dashboard", lambda: self._on_dashboard()),
            pystray.MenuItem("Undo last", lambda: self._on_undo()),
            pystray.MenuItem(
                "Focus mode",
                lambda: self._on_focus(),
                checked=lambda _: self._pending,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", lambda: self._quit()),
        )

    def _quit(self) -> None:
        self._on_quit()
        if self._icon:
            self._icon.stop()

    def start(self) -> None:
        """Create and run the tray icon (blocks the calling thread)."""
        self._icon = pystray.Icon(
            "sort-it-now",
            _icon_idle(),
            "Sort It Now",
            menu=self._build_menu(),
        )
        self._icon.run()

    def start_threaded(self) -> threading.Thread:
        """Start the tray icon in a background thread and return it."""
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
        return t

    def set_pending(self, pending: bool) -> None:
        """Update the icon colour to reflect pending items."""
        self._pending = pending
        if self._icon:
            self._icon.icon = _icon_pending() if pending else _icon_idle()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
