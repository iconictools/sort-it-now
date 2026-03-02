"""Tests for new feature modules: themes, autostart, history extensions."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time

import pytest

from sort_it_now.history import History
from sort_it_now.themes import get_theme, THEMES

# tkinter is not available in headless CI environments
_has_tkinter = True
try:
    import tkinter  # noqa: F401
except ModuleNotFoundError:
    _has_tkinter = False

skip_no_tkinter = pytest.mark.skipif(
    not _has_tkinter, reason="tkinter not available"
)

# pystray requires an X display on Linux; detect headless CI
_has_display = True
try:
    import pystray  # noqa: F401
except Exception:
    _has_display = False

skip_no_display = pytest.mark.skipif(
    not _has_display, reason="pystray requires a display (headless CI)"
)


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

    def test_dark_theme_has_list_keys(self):
        """Dashboard uses list_bg, list_fg, list_select_bg, list_select_fg."""
        theme = get_theme("dark")
        for key in ("list_bg", "list_fg", "list_select_bg", "list_select_fg"):
            assert key in theme

    def test_light_theme_has_list_keys(self):
        theme = get_theme("light")
        for key in ("list_bg", "list_fg", "list_select_bg", "list_select_fg"):
            assert key in theme

    def test_all_theme_values_are_strings(self):
        """All color values must be strings (hex codes)."""
        for name in THEMES:
            for key, value in THEMES[name].items():
                assert isinstance(value, str), f"THEMES[{name!r}][{key!r}]"


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


class TestAutostart:
    """Tests for autostart module (platform-independent logic)."""

    def test_is_autostart_returns_false_on_non_windows(self):
        from sort_it_now.autostart import is_autostart_enabled

        if sys.platform != "win32":
            assert is_autostart_enabled() is False

    def test_set_autostart_returns_false_on_non_windows(self):
        from sort_it_now.autostart import set_autostart

        if sys.platform != "win32":
            assert set_autostart(True) is False
            assert set_autostart(False) is False


class TestDndCheck:
    """Tests for the DND / Focus Assist helper."""

    @skip_no_display
    def test_dnd_returns_false_on_non_windows(self):
        from sort_it_now.app import _is_dnd_active

        if sys.platform != "win32":
            assert _is_dnd_active() is False


class TestModuleImports:
    """Verify all new modules can be imported without errors."""

    def test_import_themes(self):
        import sort_it_now.themes
        assert hasattr(sort_it_now.themes, "get_theme")

    def test_import_autostart(self):
        import sort_it_now.autostart
        assert hasattr(sort_it_now.autostart, "is_autostart_enabled")

    @skip_no_tkinter
    def test_import_conflict_ui(self):
        import sort_it_now.conflict_ui
        assert hasattr(sort_it_now.conflict_ui, "resolve_conflict")

    @skip_no_tkinter
    def test_import_settings_ui(self):
        import sort_it_now.settings_ui
        assert hasattr(sort_it_now.settings_ui, "SettingsDialog")

    @skip_no_tkinter
    def test_import_rules_ui(self):
        import sort_it_now.rules_ui
        assert hasattr(sort_it_now.rules_ui, "RulesDialog")

    @skip_no_display
    def test_import_app_dnd(self):
        from sort_it_now.app import _is_dnd_active
        assert callable(_is_dnd_active)

    @skip_no_tkinter
    def test_import_prompt_cli_setup(self):
        from sort_it_now.prompt import cli_setup
        assert callable(cli_setup)
