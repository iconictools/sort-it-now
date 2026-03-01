"""Constants and default settings for Sort It Now."""

import os

# Temporary/incomplete download extensions to ignore
TEMP_EXTENSIONS = frozenset({
    ".crdownload",  # Chrome
    ".part",        # Firefox / wget
    ".download",    # Safari
    ".tmp",
    ".temp",
    ".partial",
    ".opdownload",  # Opera
    ".unconfirmed",
})

# Default file-type to category mapping
FILE_TYPE_MAP = {
    # Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".odt": "Documents",
    ".rtf": "Documents",
    ".txt": "Documents",
    ".md": "Documents",
    ".tex": "Documents",
    # Spreadsheets
    ".xls": "Spreadsheets",
    ".xlsx": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".ods": "Spreadsheets",
    # Presentations
    ".ppt": "Presentations",
    ".pptx": "Presentations",
    ".odp": "Presentations",
    # Images
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
    ".bmp": "Images",
    ".svg": "Images",
    ".webp": "Images",
    ".ico": "Images",
    ".tiff": "Images",
    ".heic": "Images",
    # Videos
    ".mp4": "Videos",
    ".avi": "Videos",
    ".mkv": "Videos",
    ".mov": "Videos",
    ".wmv": "Videos",
    ".flv": "Videos",
    ".webm": "Videos",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".aac": "Audio",
    ".ogg": "Audio",
    ".wma": "Audio",
    ".m4a": "Audio",
    # Archives
    ".zip": "Archives",
    ".rar": "Archives",
    ".7z": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".bz2": "Archives",
    ".xz": "Archives",
    # Installers
    ".exe": "Installers",
    ".msi": "Installers",
    ".dmg": "Installers",
    ".deb": "Installers",
    ".rpm": "Installers",
    ".appimage": "Installers",
    # Code
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".java": "Code",
    ".c": "Code",
    ".cpp": "Code",
    ".h": "Code",
    ".cs": "Code",
    ".go": "Code",
    ".rs": "Code",
    ".rb": "Code",
    ".php": "Code",
    ".html": "Code",
    ".css": "Code",
    ".json": "Code",
    ".xml": "Code",
    ".yaml": "Code",
    ".yml": "Code",
}

# Default ignore patterns (filenames or prefixes)
DEFAULT_IGNORE_PATTERNS = [
    "~$*",       # Office temp files
    ".~lock.*",  # LibreOffice lock files
    "desktop.ini",
    ".DS_Store",
    "Thumbs.db",
]

# File stability check: seconds to wait before considering a file "finished"
FILE_STABLE_DELAY_SECONDS = 3.0

# Maximum number of size checks for stability
FILE_STABLE_MAX_CHECKS = 5

# Interval between size checks (seconds)
FILE_STABLE_CHECK_INTERVAL = 1.0

# Default config file location
DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".sort-it-now")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.json")
DEFAULT_HISTORY_DB = os.path.join(DEFAULT_CONFIG_DIR, "history.db")
DEFAULT_RULES_FILE = os.path.join(DEFAULT_CONFIG_DIR, "rules.json")
DEFAULT_LOG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "sort-it-now.log")
DEFAULT_UNSORTED_DIR = os.path.join(DEFAULT_CONFIG_DIR, "unsorted")

# Maximum number of actions to keep in history
HISTORY_MAX_ACTIONS = 1000
