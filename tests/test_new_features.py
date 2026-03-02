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


class TestDashboardUI:
    """Test that dashboard_ui functions are importable."""

    @skip_no_tkinter
    def test_show_dashboard_exists(self):
        from sort_it_now.dashboard_ui import show_dashboard
        assert callable(show_dashboard)

    @skip_no_tkinter
    def test_show_batch_list_exists(self):
        from sort_it_now.dashboard_ui import show_batch_list
        assert callable(show_batch_list)


class TestPatternRules:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._rules_file = os.path.join(self._tmpdir, "rules.json")

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_set_and_get_pattern_rule(self):
        from sort_it_now.rules import Rules
        r = Rules(self._rules_file)
        r.set_pattern_rule("*.pdf", "/dest/docs", "glob")
        assert len(r.pattern_rules) == 1
        assert r.pattern_rules[0]["pattern"] == "*.pdf"

    def test_remove_pattern_rule(self):
        from sort_it_now.rules import Rules
        r = Rules(self._rules_file)
        r.set_pattern_rule("*.pdf", "/dest/docs", "glob")
        r.remove_pattern_rule("*.pdf")
        assert len(r.pattern_rules) == 0

    def test_get_pattern_destination_glob(self):
        from sort_it_now.rules import Rules
        r = Rules(self._rules_file)
        r.set_pattern_rule("invoice*.pdf", "/dest/invoices", "glob")
        result = r.get_pattern_destination("/tmp/invoice_2024.pdf")
        assert result == "/dest/invoices"

    def test_get_pattern_destination_regex(self):
        from sort_it_now.rules import Rules
        r = Rules(self._rules_file)
        r.set_pattern_rule(r"report_\d+\.csv", "/dest/reports", "regex")
        result = r.get_pattern_destination("/tmp/report_123.csv")
        assert result == "/dest/reports"

    def test_get_pattern_destination_no_match(self):
        from sort_it_now.rules import Rules
        r = Rules(self._rules_file)
        r.set_pattern_rule("*.pdf", "/dest/docs", "glob")
        result = r.get_pattern_destination("/tmp/file.txt")
        assert result is None


class TestAtomicSave:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_config_save_creates_valid_file(self):
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.set_setting("test_key", "test_value")
        # File should exist and be valid JSON
        import json
        with open(path, "r") as f:
            data = json.load(f)
        assert data["global_settings"]["test_key"] == "test_value"

    def test_config_save_no_tmp_leftover(self):
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.set_setting("key", "val")
        assert not os.path.exists(path + ".tmp")

    def test_rules_save_creates_valid_file(self):
        from sort_it_now.rules import Rules
        path = os.path.join(self._tmpdir, "rules.json")
        r = Rules(path)
        r.set_rule(".txt", "/dest")
        import json
        with open(path, "r") as f:
            data = json.load(f)
        assert ".txt" in data["extension_map"]


class TestDuplicateDetection:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_compute_file_hash(self):
        from sort_it_now.duplicate import compute_file_hash
        path = os.path.join(self._tmpdir, "test.txt")
        with open(path, "w") as f:
            f.write("hello world")
        h = compute_file_hash(path)
        assert isinstance(h, str)
        assert len(h) == 64  # sha256 hex digest length

    def test_find_duplicate_found(self):
        from sort_it_now.duplicate import find_duplicate
        src = os.path.join(self._tmpdir, "src.txt")
        dest_dir = os.path.join(self._tmpdir, "dest")
        os.makedirs(dest_dir)
        content = "duplicate content"
        with open(src, "w") as f:
            f.write(content)
        dup = os.path.join(dest_dir, "existing.txt")
        with open(dup, "w") as f:
            f.write(content)
        result = find_duplicate(src, dest_dir)
        assert result == dup

    def test_find_duplicate_not_found(self):
        from sort_it_now.duplicate import find_duplicate
        src = os.path.join(self._tmpdir, "src.txt")
        dest_dir = os.path.join(self._tmpdir, "dest")
        os.makedirs(dest_dir)
        with open(src, "w") as f:
            f.write("unique content")
        with open(os.path.join(dest_dir, "other.txt"), "w") as f:
            f.write("different content")
        result = find_duplicate(src, dest_dir)
        assert result is None


class TestWhitelist:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_add_and_get_whitelist(self):
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.add_to_whitelist("*.log")
        assert "*.log" in c.get_whitelist()

    def test_remove_from_whitelist(self):
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.add_to_whitelist("*.log")
        c.remove_from_whitelist("*.log")
        assert "*.log" not in c.get_whitelist()

    def test_whitelist_no_duplicates(self):
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.add_to_whitelist("*.log")
        c.add_to_whitelist("*.log")
        assert c.get_whitelist().count("*.log") == 1


class TestRenamePattern:
    @skip_no_tkinter
    def test_apply_rename_pattern_with_date_and_name(self):
        import datetime
        from sort_it_now.app import _apply_rename_pattern
        result = _apply_rename_pattern("/tmp/report.pdf", "{date}_{name}")
        today = datetime.date.today().isoformat()
        assert result == f"{today}_report.pdf"

    @skip_no_tkinter
    def test_apply_rename_pattern_preserves_ext(self):
        from sort_it_now.app import _apply_rename_pattern
        result = _apply_rename_pattern("/tmp/file.txt", "{name}_copy")
        assert result.endswith(".txt")

    @skip_no_tkinter
    def test_apply_rename_pattern_with_ext_token(self):
        from sort_it_now.app import _apply_rename_pattern
        result = _apply_rename_pattern("/tmp/data.csv", "{name}{ext}")
        assert result == "data.csv"


class TestConfigExportImport:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_export_import_roundtrip(self):
        from sort_it_now.config import Config
        from sort_it_now.rules import Rules

        config_path = os.path.join(self._tmpdir, "config.json")
        rules_path = os.path.join(self._tmpdir, "rules.json")
        export_path = os.path.join(self._tmpdir, "backup.zip")

        c = Config(config_path)
        c.set_setting("theme", "light")
        r = Rules(rules_path)
        r.set_rule(".txt", "/dest/text")

        c.export_config(export_path)
        assert os.path.exists(export_path)

        # Modify and re-import
        c.set_setting("theme", "dark")
        c.import_config(export_path)
        assert c.get_setting("theme") == "light"


class TestConfigSaveMany:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_many_batches_writes(self):
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.save_many({
            "theme": "light",
            "auto_learn": False,
            "auto_learn_threshold": 5,
        })
        assert c.get_setting("theme") == "light"
        assert c.get_setting("auto_learn") is False
        assert c.get_setting("auto_learn_threshold") == 5

    def test_save_many_persists_to_disk(self):
        import json
        from sort_it_now.config import Config
        path = os.path.join(self._tmpdir, "config.json")
        c = Config(path)
        c.save_many({"key1": "val1", "key2": "val2"})
        with open(path, "r") as f:
            data = json.load(f)
        assert data["global_settings"]["key1"] == "val1"
        assert data["global_settings"]["key2"] == "val2"


class TestNotifications:
    def test_notify_function_exists(self):
        from sort_it_now.notifications import notify
        assert callable(notify)

    def test_notify_does_not_crash(self):
        from sort_it_now.notifications import notify
        # Should not raise even if plyer fails
        notify("Test", "Message", timeout=1)


class TestCatchFolders:
    """Tests for the catch_folders option in FolderWatcher."""

    def test_watcher_accepts_catch_folders(self):
        from sort_it_now.watcher import FolderWatcher

        w = FolderWatcher(callback=lambda p: None, catch_folders=True)
        assert w._catch_folders is True

    def test_watcher_default_no_catch_folders(self):
        from sort_it_now.watcher import FolderWatcher

        w = FolderWatcher(callback=lambda p: None)
        assert w._catch_folders is False

    def test_scan_existing_includes_dirs_when_enabled(self):
        from sort_it_now.watcher import FolderWatcher

        tmpdir = tempfile.mkdtemp()
        try:
            # Create a file and a subdirectory
            open(os.path.join(tmpdir, "file.txt"), "w").close()
            os.makedirs(os.path.join(tmpdir, "subdir"))

            collected: list[str] = []
            w = FolderWatcher(callback=lambda p: None, catch_folders=True)
            w.scan_existing(tmpdir, collected.append)
            basenames = [os.path.basename(p) for p in collected]
            assert "file.txt" in basenames
            assert "subdir" in basenames
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_scan_existing_skips_dirs_when_disabled(self):
        from sort_it_now.watcher import FolderWatcher

        tmpdir = tempfile.mkdtemp()
        try:
            open(os.path.join(tmpdir, "file.txt"), "w").close()
            os.makedirs(os.path.join(tmpdir, "subdir"))

            collected: list[str] = []
            w = FolderWatcher(callback=lambda p: None, catch_folders=False)
            w.scan_existing(tmpdir, collected.append)
            basenames = [os.path.basename(p) for p in collected]
            assert "file.txt" in basenames
            assert "subdir" not in basenames
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestSortPromptWhitelist:
    """Tests for the on_whitelist parameter in SortPrompt."""

    @skip_no_tkinter
    def test_sort_prompt_accepts_whitelist_callback(self):
        from sort_it_now.prompt import SortPrompt

        called: list[str] = []
        prompt = SortPrompt(
            filepath="/tmp/test.txt",
            destinations=["/tmp/dest"],
            on_done=lambda *a: None,
            on_whitelist=called.append,
        )
        assert prompt._on_whitelist is not None

    @skip_no_tkinter
    def test_sort_prompt_works_without_whitelist(self):
        from sort_it_now.prompt import SortPrompt

        prompt = SortPrompt(
            filepath="/tmp/test.txt",
            destinations=["/tmp/dest"],
            on_done=lambda *a: None,
        )
        assert prompt._on_whitelist is None
