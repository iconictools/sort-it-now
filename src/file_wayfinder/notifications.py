"""Native toast notifications for File Wayfinder."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


def notify(title: str, message: str, timeout: int = 5) -> None:
    """Show a native toast notification (non-blocking).

    Falls back to logging if plyer is unavailable or fails.
    """

    def _send() -> None:
        try:
            from plyer import notification

            notification.notify(
                title=title,
                message=message,
                timeout=timeout,
                app_name="File Wayfinder",
            )
        except Exception as exc:
            logger.debug("Native notification failed: %s", exc)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()
