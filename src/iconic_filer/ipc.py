"""Simple socket-based IPC for Iconic File Filer multi-instance support.

Protocol
--------
The primary instance opens a TCP server on ``localhost:PORT``.
When a second instance detects the server is already running it sends a
command (a UTF-8 line) and exits.  The primary instance reads the command
and acts on it — currently only ``ADD_FOLDER:<path>`` is supported.

The port is fixed (not random) so instances can always find each other.
Choosing a fixed port means we don't need a lock file, PID file, or any
OS-specific mechanism.  The port is unlikely to conflict with other apps;
it was chosen from the IANA unassigned range.
"""

from __future__ import annotations

import logging
import socket
import threading
from typing import Callable

logger = logging.getLogger(__name__)

IPC_PORT = 47890  # Iconic File Filer IPC port (arbitrary, unregistered)
IPC_HOST = "127.0.0.1"
IPC_TIMEOUT = 1.0  # seconds


def is_running() -> bool:
    """Return *True* if another instance is already listening on the IPC port."""
    try:
        with socket.create_connection((IPC_HOST, IPC_PORT), timeout=IPC_TIMEOUT):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def send_command(command: str) -> bool:
    """Send *command* (a single line, no newline needed) to the running instance.

    Returns *True* on success.
    """
    try:
        with socket.create_connection(
            (IPC_HOST, IPC_PORT), timeout=IPC_TIMEOUT
        ) as sock:
            sock.sendall((command + "\n").encode("utf-8"))
        return True
    except OSError as exc:
        logger.debug("IPC send failed: %s", exc)
        return False


class IPCServer:
    """Runs a background TCP server that accepts commands from other instances."""

    def __init__(self, on_command: Callable[[str], None]) -> None:
        self._on_command = on_command
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start listening in a background daemon thread."""
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((IPC_HOST, IPC_PORT))
            self._server.listen(5)
            self._server.settimeout(1.0)
            self._thread = threading.Thread(
                target=self._serve, daemon=True, name="ipc-server"
            )
            self._thread.start()
            logger.debug("IPC server listening on port %d", IPC_PORT)
        except OSError as exc:
            logger.warning("IPC server could not start: %s", exc)

    def stop(self) -> None:
        self._stop_event.set()
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass

    def _serve(self) -> None:
        assert self._server is not None
        while not self._stop_event.is_set():
            try:
                conn, _ = self._server.accept()
            except OSError:
                continue
            threading.Thread(
                target=self._handle, args=(conn,), daemon=True
            ).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            with conn:
                data = b""
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                command = data.decode("utf-8", errors="replace").strip()
                if command:
                    self._on_command(command)
        except OSError as exc:
            logger.debug("IPC handle error: %s", exc)
