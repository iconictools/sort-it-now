"""Autostart on login management for File Wayfinder.

On Windows this uses the ``HKCU\\...\\Run`` registry key.
On other platforms this is a no-op with a logged warning.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_APP_NAME = "FileWayfinder"


def is_autostart_enabled() -> bool:
    """Return *True* if the app is registered to start on login."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        try:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable autostart on login.

    Returns *True* on success.
    """
    if sys.platform != "win32":
        logger.warning("Autostart is only supported on Windows.")
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            if enabled:
                if getattr(sys, "frozen", False):
                    exe = sys.executable
                else:
                    exe = f'"{sys.executable}" -m file_wayfinder'
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, exe)
                logger.info("Autostart enabled.")
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                except FileNotFoundError:
                    pass
                logger.info("Autostart disabled.")
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as exc:
        logger.error("Failed to set autostart: %s", exc)
        return False
