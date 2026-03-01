"""Tests for the watcher module (unit-level, no I/O waiting)."""

import os
import tempfile
import time
import threading

from sort_it_now.classifier import is_temp_file, matches_ignore_pattern


class TestWatcherHelpers:
    """Test the helper functions used by the watcher."""

    def test_temp_file_ignored(self):
        assert is_temp_file("video.crdownload") is True

    def test_normal_file_not_ignored(self):
        assert is_temp_file("report.pdf") is False

    def test_ignore_pattern_match(self):
        assert matches_ignore_pattern("~$doc.docx", ["~$*"]) is True

    def test_ignore_pattern_no_match(self):
        assert matches_ignore_pattern("readme.md", ["~$*", ".DS_Store"]) is False
