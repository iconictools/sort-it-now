"""Achievement system for File Wayfinder."""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    emoji: str
    unlocked: bool = False
    unlocked_at: float = 0.0


_ALL_ACHIEVEMENTS = [
    Achievement("first_sort",     "First Sort",        "Sort your first file.",                        "🎉"),
    Achievement("ten_sorts",      "Sorting Spree",     "Sort 10 files.",                               "📦"),
    Achievement("hundred_sorts",  "Century Club",      "Sort 100 files.",                              "💯"),
    Achievement("thousand_sorts", "Sorting Machine",   "Sort 1,000 files.",                            "🤖"),
    Achievement("streak_3",       "3-Day Streak",      "Sort at least one file every day for 3 days.", "🔥"),
    Achievement("streak_7",       "Week Warrior",      "Sort at least one file every day for 7 days.", "⚡"),
    Achievement("streak_30",      "Month Master",      "Sort at least one file every day for 30 days.", "🏆"),
    Achievement("night_owl",      "Night Owl",         "Sort a file between midnight and 5 AM.",       "🦉"),
    Achievement("early_bird",     "Early Bird",        "Sort a file before 7 AM.",                     "🐦"),
    Achievement("speed_demon",    "Speed Demon",       "Sort 10 files in under 60 seconds.",           "💨"),
    Achievement("neat_freak",     "Neat Freak",        "Sort files into 5 different destinations.",    "✨"),
    Achievement("variety",        "Variety Pack",      "Sort 5 different file types.",                 "🎨"),
]


class Achievements:
    """Persists and evaluates achievements against the action history."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS achievements (
                id          TEXT PRIMARY KEY,
                unlocked_at REAL NOT NULL DEFAULT 0
            );
        """)

    def evaluate(self, history_conn: sqlite3.Connection) -> list[Achievement]:
        """Evaluate all achievements against history. Returns newly unlocked ones."""
        newly_unlocked: list[Achievement] = []
        already = {
            row[0] for row in
            self._conn.execute("SELECT id FROM achievements WHERE unlocked_at > 0").fetchall()
        }

        total = history_conn.execute(
            "SELECT COUNT(*) FROM actions WHERE undone=0"
        ).fetchone()[0]

        # Milestone counts
        for ach_id, threshold in [
            ("first_sort", 1), ("ten_sorts", 10),
            ("hundred_sorts", 100), ("thousand_sorts", 1000),
        ]:
            if ach_id not in already and total >= threshold:
                newly_unlocked.append(self._unlock(ach_id))

        # Streak
        days_with_activity: set[int] = set()
        rows = history_conn.execute(
            "SELECT timestamp FROM actions WHERE undone=0 ORDER BY timestamp DESC"
        ).fetchall()
        for row in rows:
            day = int(row[0] // 86400)
            days_with_activity.add(day)

        today = int(time.time() // 86400)
        for streak_len, ach_id in [(3, "streak_3"), (7, "streak_7"), (30, "streak_30")]:
            if ach_id not in already:
                consecutive = sum(
                    1 for i in range(streak_len)
                    if (today - i) in days_with_activity
                )
                if consecutive >= streak_len:
                    newly_unlocked.append(self._unlock(ach_id))

        # Night owl / early bird (local hour)
        for row in rows:
            hour = time.localtime(row[0]).tm_hour
            if "night_owl" not in already and 0 <= hour < 5:
                newly_unlocked.append(self._unlock("night_owl"))
                already.add("night_owl")
            if "early_bird" not in already and 5 <= hour < 7:
                newly_unlocked.append(self._unlock("early_bird"))
                already.add("early_bird")

        # Speed demon: 10 sorts in 60 seconds
        if "speed_demon" not in already and len(rows) >= 10:
            timestamps = [r[0] for r in rows[:10]]
            if max(timestamps) - min(timestamps) <= 60:
                newly_unlocked.append(self._unlock("speed_demon"))

        # Neat freak: 5 distinct destinations
        dests = history_conn.execute(
            "SELECT DISTINCT dst_path FROM actions WHERE undone=0"
        ).fetchall()
        unique_dirs = {os.path.dirname(d[0]) for d in dests}
        if "neat_freak" not in already and len(unique_dirs) >= 5:
            newly_unlocked.append(self._unlock("neat_freak"))

        # Variety: 5 distinct extensions
        srcs = history_conn.execute(
            "SELECT src_path FROM actions WHERE undone=0"
        ).fetchall()
        exts = {os.path.splitext(s[0])[1].lower() for s in srcs if os.path.splitext(s[0])[1]}
        if "variety" not in already and len(exts) >= 5:
            newly_unlocked.append(self._unlock("variety"))

        return newly_unlocked

    def _unlock(self, ach_id: str) -> Achievement:
        now = time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO achievements (id, unlocked_at) VALUES (?, ?)",
            (ach_id, now),
        )
        self._conn.commit()
        ach = next(a for a in _ALL_ACHIEVEMENTS if a.id == ach_id)
        return Achievement(ach.id, ach.name, ach.description, ach.emoji,
                           unlocked=True, unlocked_at=now)

    def all_status(self) -> list[Achievement]:
        """Return all achievements with their unlock status."""
        unlocked_map = {
            row[0]: row[1]
            for row in self._conn.execute(
                "SELECT id, unlocked_at FROM achievements WHERE unlocked_at > 0"
            ).fetchall()
        }
        result = []
        for a in _ALL_ACHIEVEMENTS:
            unlocked = a.id in unlocked_map
            result.append(Achievement(
                a.id, a.name, a.description, a.emoji,
                unlocked=unlocked,
                unlocked_at=unlocked_map.get(a.id, 0.0),
            ))
        return result

    def close(self) -> None:
        self._conn.close()
