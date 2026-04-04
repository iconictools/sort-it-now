"""Tests for the classifier module."""


from file_wayfinder.classifier import (
    classify_by_extension,
    is_temp_file,
    matches_ignore_pattern,
    suggest_destinations,
)


class TestIsTempFile:
    def test_chrome_download(self):
        assert is_temp_file("movie.crdownload") is True

    def test_firefox_partial(self):
        assert is_temp_file("archive.part") is True

    def test_normal_pdf(self):
        assert is_temp_file("document.pdf") is False

    def test_no_extension(self):
        assert is_temp_file("README") is False

    def test_case_insensitive(self):
        assert is_temp_file("file.CRDOWNLOAD") is True


class TestMatchesIgnorePattern:
    def test_office_temp(self):
        assert matches_ignore_pattern("~$report.docx", ["~$*"]) is True

    def test_ds_store(self):
        assert matches_ignore_pattern(".DS_Store", [".DS_Store"]) is True

    def test_normal_file(self):
        assert matches_ignore_pattern("photo.jpg", ["~$*", ".DS_Store"]) is False

    def test_empty_patterns(self):
        assert matches_ignore_pattern("anything.txt", []) is False


class TestClassifyByExtension:
    def test_pdf(self):
        assert classify_by_extension("invoice.pdf") == "Documents"

    def test_jpg(self):
        assert classify_by_extension("photo.jpg") == "Images"

    def test_mp4(self):
        assert classify_by_extension("video.mp4") == "Videos"

    def test_exe(self):
        assert classify_by_extension("setup.exe") == "Installers"

    def test_unknown(self):
        assert classify_by_extension("file.xyz123") is None

    def test_case_insensitive(self):
        assert classify_by_extension("PHOTO.JPG") == "Images"


class TestSuggestDestinations:
    def test_learned_rule_first(self):
        dests = ["/docs", "/images", "/temp"]
        rules = {".pdf": "/docs"}
        result = suggest_destinations("file.pdf", dests, rules)
        assert result[0] == "/docs"

    def test_category_match(self):
        dests = ["/my-documents", "/images", "/temp"]
        result = suggest_destinations("file.pdf", dests)
        assert result[0] == "/my-documents"

    def test_all_destinations_returned(self):
        dests = ["/a", "/b", "/c"]
        result = suggest_destinations("file.xyz", dests)
        assert set(result) == set(dests)

    def test_no_duplicates(self):
        dests = ["/documents", "/temp"]
        rules = {".pdf": "/documents"}
        result = suggest_destinations("file.pdf", dests, rules)
        assert len(result) == len(set(result))

    def test_empty_destinations(self):
        result = suggest_destinations("file.pdf", [])
        assert result == []
