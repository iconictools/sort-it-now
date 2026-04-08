"""Autostart on login management for File Wayfinder.

On Windows this uses the ``HKCU\\...\\Run`` registry key.
On Linux this creates/removes a ``.desktop`` file in
``~/.config/autostart/`` (XDG autostart specification).
On other platforms this is a no-op with a logged warning.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

_APP_NAME = "FileWayfinder"
_DESKTOP_FILENAME = "file-wayfinder.desktop"


def _linux_desktop_path() -> str:
    """Return the XDG autostart .desktop file path."""
    autostart_dir = os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        "autostart",
    )
    return os.path.join(autostart_dir, _DESKTOP_FILENAME)


def _linux_exec_cmd() -> str:
    """Return the command used to launch the app on Linux."""
    if getattr(sys, "frozen", False):
        return sys.executable
    return f"{sys.executable} -m file_wayfinder"


def is_autostart_enabled() -> bool:
    """Return *True* if the app is registered to start on login."""
    if sys.platform == "win32":
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

    if sys.platform.startswith("linux"):
        return os.path.isfile(_linux_desktop_path())

    return False


def set_autostart(enabled: bool) -> bool:
    """Enable or disable autostart on login.

    Returns *True* on success.
    """
    if sys.platform == "win32":
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
                    logger.info("Autostart enabled (Windows registry).")
                else:
                    try:
                        winreg.DeleteValue(key, _APP_NAME)
                    except FileNotFoundError:
                        pass
                    logger.info("Autostart disabled (Windows registry).")
                return True
            finally:
                winreg.CloseKey(key)
        except Exception as exc:
            logger.error("Failed to set autostart: %s", exc)
            return False

    if sys.platform.startswith("linux"):
        desktop_path = _linux_desktop_path()
        try:
            if enabled:
                os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
                desktop_content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Name={_APP_NAME}\n"
                    f"Exec={_linux_exec_cmd()}\n"
                    "Hidden=false\n"
                    "NoDisplay=false\n"
                    "X-GNOME-Autostart-enabled=true\n"
                )
                with open(desktop_path, "w", encoding="utf-8") as fh:
                    fh.write(desktop_content)
                logger.info("Autostart enabled (XDG desktop: %s).", desktop_path)
            else:
                try:
                    os.remove(desktop_path)
                except FileNotFoundError:
                    pass
                logger.info("Autostart disabled (XDG desktop removed).")
            return True
        except OSError as exc:
            logger.error("Failed to set autostart: %s", exc)
            return False

    logger.warning("Autostart is not supported on this platform (%s).", sys.platform)
    return False
