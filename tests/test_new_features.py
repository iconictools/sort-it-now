"""Tests for new feature modules: themes, autostart, history extensions."""

from __future__ import annotations

import os
import shutil
import tempfile
import time

from sort_it_now.history import History
from sort_it_now.themes import get_theme, THEMES


class TestThemes:
    def test_dark_theme_has_required_keys(self):
        theme = get_theme("dark")
        for key in ("bg", "fg", "accent", "btn_bg", "btn_fg", "muted",
                     "danger", "success", "entry_bg", "entry_fg"):
            assert key in theme

    def test_light_theme_has_required_keys(self):
        theme = get_theme("light")
        for key in ("bg", "fg", "accent", "btn_bg", "btn_fg", "muted",
                     "danger", "success", "entry_bg", "entry_fg"):
            assert key in theme

    def test_unknown_theme_falls_back_to_dark(self):
        theme = get_theme("nonexistent")
        assert theme == THEMES["dark"]

    def test_themes_have_distinct_backgrounds(self):
        assert get_theme("dark")["bg"] != get_theme("light")["bg"]


class TestHistoryExtensions:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db = os.path.join(self._tmpdir, "test_history.db")

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_total_count(self):
        h = History(self._db)
        assert h.total_count() == 0
        h.record("/src/a.txt", "/dst/a.txt")
        h.record("/src/b.txt", "/dst/b.txt")
        assert h.total_count() == 2
        h.close()

    def test_count_since(self):
        h = History(self._db)
        before = time.time() - 1
        h.record("/src/a.txt", "/dst/a.txt")
        assert h.count_since(before) == 1
        assert h.count_since(time.time() + 100) == 0
        h.close()

    def test_undo_by_id(self):
        h = History(self._db)
        # Create source and destination
        src = os.path.join(self._tmpdir, "src.txt")
        dst_dir = os.path.join(self._tmpdir, "dst")
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, "src.txt")
        with open(src, "w") as f:
            f.write("test")

        # Simulate a move
        shutil.move(src, dst)
        action_id = h.record(src, dst)

        # Undo by id
        result = h.undo_by_id(action_id)
        assert result is not None
        assert result == (dst, src)
        assert os.path.exists(src)
        assert not os.path.exists(dst)
        h.close()

    def test_undo_by_id_already_undone(self):
        h = History(self._db)
        action_id = h.record("/src/a.txt", "/dst/a.txt")
        # Mark as undone manually
        h._conn.execute(
            "UPDATE actions SET undone = 1 WHERE id = ?", (action_id,)
        )
        h._conn.commit()
        assert h.undo_by_id(action_id) is None
        h.close()

    def test_undo_by_id_nonexistent(self):
        h = History(self._db)
        assert h.undo_by_id(9999) is None
        h.close()
