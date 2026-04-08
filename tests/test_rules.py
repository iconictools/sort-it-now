"""Tests for the rules module."""

import os
import tempfile

from file_wayfinder.rules import Rules


class TestRules:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._path = os.path.join(self._tmpdir, "test_rules.json")

    def teardown_method(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_empty_by_default(self):
        rules = Rules(self._path)
        assert rules.extension_map == {}

    def test_set_rule(self):
        rules = Rules(self._path)
        rules.set_rule(".pdf", "/docs")
        assert rules.extension_map[".pdf"] == "/docs"

    def test_remove_rule(self):
        rules = Rules(self._path)
        rules.set_rule(".pdf", "/docs")
        rules.remove_rule(".pdf")
        assert ".pdf" not in rules.extension_map

    def test_record_action_no_auto_promote(self):
        """record_action must NOT auto-promote to extension_map (no auto-learning)."""
        rules = Rules(self._path)
        for fname in ("a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"):
            rules.record_action(fname, "/docs")
        # No matter how many times, extension_map must stay empty.
        assert rules.extension_map == {}

    def test_record_action_history_is_logged(self):
        """record_action stores entries in the internal history list."""
        rules = Rules(self._path)
        rules.record_action("a.pdf", "/docs")
        rules.record_action("b.pdf", "/docs")
        history = rules._data.get("history", [])
        assert len(history) == 2
        assert all(h["ext"] == ".pdf" for h in history)

    def test_get_auto_destination(self):
        rules = Rules(self._path)
        rules.set_rule(".png", "/images")
        assert rules.get_auto_destination("screenshot.png") == "/images"

    def test_no_auto_destination(self):
        rules = Rules(self._path)
        assert rules.get_auto_destination("file.xyz") is None

    def test_persistence(self):
        rules1 = Rules(self._path)
        rules1.set_rule(".csv", "/data")

        rules2 = Rules(self._path)
        assert rules2.extension_map[".csv"] == "/data"

    def test_extension_normalization(self):
        rules = Rules(self._path)
        rules.set_rule("PDF", "/docs")
        assert ".pdf" in rules.extension_map

    def test_auto_learn_custom_threshold_not_applicable(self):
        """record_action never promotes regardless of call count (threshold removed)."""
        rules = Rules(self._path)
        for _ in range(10):
            rules.record_action("a.csv", "/data")
        assert ".csv" not in rules.extension_map

    def test_corrupt_json_resets(self):
        """Corrupted rules file should be backed up and reset."""
        with open(self._path, "w") as f:
            f.write("NOT VALID JSON {{{")
        rules = Rules(self._path)
        assert rules.extension_map == {}
        # A backup should exist
        backups = [
            f for f in os.listdir(self._tmpdir) if "bak" in f
        ]
        assert len(backups) >= 1
