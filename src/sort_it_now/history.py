"""Undo / action history backed by SQLite for Sort It Now."""

import os
import shutil
import sqlite3
import time

from sort_it_now.constants import DEFAULT_HISTORY_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   REAL    NOT NULL,
    src_path    TEXT    NOT NULL,
    dst_path    TEXT    NOT NULL,
    undone      INTEGER NOT NULL DEFAULT 0
);
"""


class History:
    """Records file-move actions and supports undo."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DEFAULT_HISTORY_DB
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, src_path: str, dst_path: str) -> int:
        """Record a file move and return the action id."""
        cur = self._conn.execute(
            "INSERT INTO actions (timestamp, src_path, dst_path) VALUES (?, ?, ?)",
            (time.time(), src_path, dst_path),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def undo_last(self) -> tuple[str, str] | None:
        """Undo the most recent non-undone action.

        Moves the file back and returns ``(dst_path, src_path)`` on success,
        or *None* if nothing to undo.
        """
        row = self._conn.execute(
            "SELECT id, src_path, dst_path FROM actions "
            "WHERE undone = 0 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None

        action_id, src_path, dst_path = row
        if os.path.exists(dst_path):
            os.makedirs(os.path.dirname(src_path) or ".", exist_ok=True)
            shutil.move(dst_path, src_path)

        self._conn.execute(
            "UPDATE actions SET undone = 1 WHERE id = ?", (action_id,)
        )
        self._conn.commit()
        return dst_path, src_path

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def recent(self, limit: int = 20) -> list[dict]:
        """Return the *limit* most recent actions."""
        rows = self._conn.execute(
            "SELECT id, timestamp, src_path, dst_path, undone "
            "FROM actions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "src_path": r[2],
                "dst_path": r[3],
                "undone": bool(r[4]),
            }
            for r in rows
        ]

    def pending_count(self) -> int:
        """Return the number of recorded but not-yet-undone actions."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM actions WHERE undone = 0"
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()
