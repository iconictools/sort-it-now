"""Tests for the rules module."""

import json
import os
import tempfile

from sort_it_now.rules import Rules


class TestRules:
    def setup_method(self):
        self._tmpdir = tempfile.mkdtemp()
        self._path = os.path.join(self._tmpdir, "test_rules.json")

    def teardown_method(self):
        if os.path.exists(self._path):
            os.remove(self._path)
        os.rmdir(self._tmpdir)

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

    def test_auto_learn_after_3(self):
        rules = Rules(self._path)
        rules.record_action("a.pdf", "/docs")
        rules.record_action("b.pdf", "/docs")
        assert ".pdf" not in rules.extension_map
        rules.record_action("c.pdf", "/docs")
        assert rules.extension_map[".pdf"] == "/docs"

    def test_auto_learn_most_common(self):
        rules = Rules(self._path)
        rules.record_action("a.jpg", "/photos")
        rules.record_action("b.jpg", "/photos")
        rules.record_action("c.jpg", "/memes")
        rules.record_action("d.jpg", "/photos")
        assert rules.extension_map[".jpg"] == "/photos"

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
