"""System tray icon for File Wayfinder (pystray-based)."""

from __future__ import annotations

import logging
import threading
from typing import Callable

from PIL import Image, ImageDraw, ImageFont
import pystray

logger = logging.getLogger(__name__)

# ── Icon drawing helpers ─────────────────────────────────────────────

def _create_icon_image(
    color: str = "#89b4fa",
    size: int = 64,
    badge_count: int = 0,
) -> Image.Image:
    """Draw a simple folder-shaped tray icon with optional badge."""
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
    # Badge with pending count
    if badge_count > 0:
        badge_r = 14
        badge_x = size - badge_r - 2
        badge_y = badge_r + 2
        draw.ellipse(
            [badge_x - badge_r, badge_y - badge_r,
             badge_x + badge_r, badge_y + badge_r],
            fill="#f38ba8",
        )
        label = str(badge_count) if badge_count <= 99 else "99+"
        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            (badge_x - tw // 2, badge_y - th // 2 - 1),
            label, fill="#ffffff", font=font,
        )
    return img


def _icon_idle() -> Image.Image:
    return _create_icon_image("#89b4fa")


def _icon_pending(count: int = 0) -> Image.Image:
    return _create_icon_image("#f38ba8", badge_count=count)


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
    on_open_settings:
        Called when the user clicks "Settings".
    on_open_rules:
        Called when the user clicks "Manage Rules".
    on_add_folder:
        Called when the user clicks "Add folder to watch...".
    on_quit:
        Called when the user clicks "Quit".
    """

    def __init__(
        self,
        on_open_dashboard: Callable[[], None] | None = None,
        on_toggle_focus: Callable[[], None] | None = None,
        on_undo: Callable[[], None] | None = None,
        on_open_settings: Callable[[], None] | None = None,
        on_open_rules: Callable[[], None] | None = None,
        on_add_folder: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        self._on_dashboard = on_open_dashboard or (lambda: None)
        self._on_focus = on_toggle_focus or (lambda: None)
        self._on_undo = on_undo or (lambda: None)
        self._on_settings = on_open_settings or (lambda: None)
        self._on_rules = on_open_rules or (lambda: None)
        self._on_add_folder = on_add_folder or (lambda: None)
        self._on_quit = on_quit or (lambda: None)
        self._icon: pystray.Icon | None = None
        self._pending = False
        self._pending_count = 0
        self._monitored_count = 0

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Dashboard", lambda: self._on_dashboard()),
            pystray.MenuItem("Add folder to watch...", lambda: self._on_add_folder()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Undo last", lambda: self._on_undo()),
            pystray.MenuItem(
                "Focus mode",
                lambda: self._on_focus(),
                checked=lambda _: self._pending,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Manage Rules", lambda: self._on_rules()),
            pystray.MenuItem("Settings", lambda: self._on_settings()),
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
            "file-wayfinder",
            _icon_idle(),
            "File Wayfinder",
            menu=self._build_menu(),
        )
        self._icon.run()

    def start_threaded(self) -> threading.Thread:
        """Start the tray icon in a background thread and return it."""
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
        return t

    def set_pending(self, pending: bool, count: int = 0) -> None:
        """Update the icon to reflect pending items with a badge count."""
        self._pending = pending
        self._pending_count = count
        if self._icon:
            if pending:
                self._icon.icon = _icon_pending(count)
                self._icon.title = f"File Wayfinder ({count} pending)"
            else:
                self._refresh_idle_icon()

    def set_monitored_count(self, count: int) -> None:
        """Update the tray tooltip to show how many folders are being monitored."""
        self._monitored_count = count
        if self._icon and not self._pending:
            self._refresh_idle_icon()

    def _refresh_idle_icon(self) -> None:
        """Refresh the icon and title to reflect the monitored folder count."""
        if self._icon:
            self._icon.icon = _icon_idle()
            n = self._monitored_count
            if n > 0:
                self._icon.title = f"File Wayfinder ({n} folder{'s' if n != 1 else ''} watched)"
            else:
                self._icon.title = "File Wayfinder"

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
