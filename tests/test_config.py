"""Tests for the config module."""

import os
import tempfile

from file_wayfinder.config import Config


class TestConfig:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._path = os.path.join(self._tmpdir, "test_config.json")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_creates_default_on_missing(self):
        cfg = Config(self._path)
        assert os.path.exists(self._path)
        assert cfg.monitored_folders == {}

    def test_add_monitored_folder(self):
        cfg = Config(self._path)
        cfg.add_monitored_folder("/tmp/downloads", ["/tmp/docs", "/tmp/images"])
        assert "/tmp/downloads" in cfg.monitored_folders
        assert cfg.monitored_folders["/tmp/downloads"] == ["/tmp/docs", "/tmp/images"]

    def test_remove_monitored_folder(self):
        cfg = Config(self._path)
        cfg.add_monitored_folder("/tmp/downloads", ["/tmp/docs"])
        cfg.remove_monitored_folder("/tmp/downloads")
        assert "/tmp/downloads" not in cfg.monitored_folders

    def test_persistence(self):
        cfg1 = Config(self._path)
        cfg1.add_monitored_folder("/tmp/test", ["/tmp/dest"])
        cfg1.set_setting("focus_mode", True)

        cfg2 = Config(self._path)
        assert "/tmp/test" in cfg2.monitored_folders
        assert cfg2.get_setting("focus_mode") is True

    def test_ignore_patterns(self):
        cfg = Config(self._path)
        cfg.add_ignore_pattern("*.log")
        assert "*.log" in cfg.ignore_patterns

        cfg.remove_ignore_pattern("*.log")
        assert "*.log" not in cfg.ignore_patterns

    def test_set_destinations(self):
        cfg = Config(self._path)
        cfg.add_monitored_folder("/tmp/test", ["/tmp/a"])
        cfg.set_destinations("/tmp/test", ["/tmp/b", "/tmp/c"])
        assert cfg.monitored_folders["/tmp/test"] == ["/tmp/b", "/tmp/c"]

    def test_get_setting_default(self):
        cfg = Config(self._path)
        assert cfg.get_setting("nonexistent", 42) == 42

    def test_corrupt_json_resets_to_default(self):
        """Config with invalid JSON should back up and reset (Q8.2)."""
        with open(self._path, "w") as f:
            f.write("{invalid json!!!")
        cfg = Config(self._path)
        assert cfg.monitored_folders == {}
        # Backup file should exist
        assert any("bak" in f for f in os.listdir(self._tmpdir))

    def test_auto_learn_threshold_default(self):
        """Default auto-learn threshold should be 3 (Q5.1)."""
        cfg = Config(self._path)
        assert cfg.get_setting("auto_learn_threshold", 3) == 3
