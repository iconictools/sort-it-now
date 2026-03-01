"""Tests for the history module."""

import os
import shutil
import tempfile

from sort_it_now.history import History


class TestHistory:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "test_history.db")

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_record_returns_id(self):
        hist = History(self._db_path)
        action_id = hist.record("/src/a.txt", "/dst/a.txt")
        assert isinstance(action_id, int)
        assert action_id >= 1
        hist.close()

    def test_recent(self):
        hist = History(self._db_path)
        hist.record("/a", "/b")
        hist.record("/c", "/d")
        recent = hist.recent(10)
        assert len(recent) == 2
        assert recent[0]["src_path"] == "/c"  # most recent first
        hist.close()

    def test_undo_last(self):
        hist = History(self._db_path)
        # Create actual files for undo
        src = os.path.join(self._tmpdir, "source.txt")
        dst = os.path.join(self._tmpdir, "dest.txt")
        with open(src, "w") as f:
            f.write("test")
        shutil.move(src, dst)
        hist.record(src, dst)

        result = hist.undo_last()
        assert result is not None
        assert result == (dst, src)
        assert os.path.exists(src)
        assert not os.path.exists(dst)
        hist.close()

    def test_undo_nothing(self):
        hist = History(self._db_path)
        assert hist.undo_last() is None
        hist.close()

    def test_pending_count(self):
        hist = History(self._db_path)
        hist.record("/a", "/b")
        hist.record("/c", "/d")
        assert hist.pending_count() == 2
        hist.close()

    def test_undo_marks_as_undone(self):
        hist = History(self._db_path)
        src = os.path.join(self._tmpdir, "s.txt")
        dst = os.path.join(self._tmpdir, "d.txt")
        with open(src, "w") as f:
            f.write("x")
        shutil.move(src, dst)
        hist.record(src, dst)

        hist.undo_last()
        recent = hist.recent(1)
        assert recent[0]["undone"] is True
        hist.close()

    def test_prune_keeps_max_actions(self):
        """History should prune to HISTORY_MAX_ACTIONS (Q7.3)."""
        from sort_it_now.constants import HISTORY_MAX_ACTIONS

        hist = History(self._db_path)
        for i in range(HISTORY_MAX_ACTIONS + 50):
            hist.record(f"/src/{i}.txt", f"/dst/{i}.txt")
        count = hist._conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
        assert count <= HISTORY_MAX_ACTIONS
        hist.close()
