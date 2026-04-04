# File Wayfinder 🗂️

> Tray-resident real-time file organizer assistant — put your files where you want, *right when they arrive*.

[![Build](https://github.com/trabalhefabricio/sort-it-now/actions/workflows/build.yml/badge.svg)](https://github.com/trabalhefabricio/sort-it-now/actions/workflows/build.yml)

## What it does

File Wayfinder lives in your system tray and watches folders you choose (Downloads, Desktop, Screenshots, etc.). When a new file appears it asks you **"Where should this go?"** with a quick popup showing your configured destinations.

Instead of dumping files and cleaning up later, you make a micro-decision at the moment of action — building a tidy file system as a habit.

### Features

| Feature | Description |
|---|---|
| **Real-time monitoring** | Detects new, moved, and modified files instantly via `watchdog` |
| **Smart prompts** | Non-intrusive popup with context-aware destination suggestions |
| **File preview** | Image thumbnails, text file previews, and file type labels in the prompt |
| **Auto-learning rules** | After consistent choices the app sorts that file type automatically |
| **Pattern rules** | Glob and regex rules (e.g. `invoice*.pdf` → Finances) |
| **Rename on move** | Configurable rename patterns with date tokens |
| **Duplicate detection** | SHA256-based duplicate check before moving |
| **Native notifications** | Toast notifications via plyer (cross-platform) |
| **Focus / Snooze mode** | Queues prompts during deep work, processes them when you're ready |
| **DND integration** | Pauses when Windows Focus Assist is active |
| **Undo** | One-click revert from the tray menu, plus clickable history |
| **Dashboard** | Quick view of recent actions, stats, and pending files |
| **Batch processing** | Process queued files one-by-one or via batch list |
| **Settings UI** | Full settings dialog — no JSON editing required |
| **Rule management UI** | View, add, edit, and delete rules visually |
| **Dark / Light theme** | Catppuccin-inspired themes |
| **Whitelist** | Control exactly which files to ignore |
| **Catch folders** | Optionally detect and sort entire directories |
| **Config import/export** | Backup and restore your setup as a zip |
| **Autostart** | Start on login (Windows) |
| **Download awareness** | Waits for `.crdownload` / `.part` files to finish before prompting |
| **Self-loop prevention** | Files the app moves won't re-trigger the watcher |
| **Cross-platform** | Works on Windows, macOS, and Linux |
| **Self-building CI** | GitHub Actions builds executables on every push |
| **Manual build** | `python build.py` creates a standalone executable locally |

## Quick start

### Run from source

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run
python -m file_wayfinder

# First launch opens a Setup Wizard where you pick
# folders to monitor and their destination folders.
```

### Build a standalone executable

```bash
# Install build deps
pip install -r requirements-dev.txt

# Build
python build.py            # directory bundle
python build.py --onefile  # single-file executable

# Output lands in dist/
```

### CI / CD

Every push triggers the **Build** workflow (`.github/workflows/build.yml`) which:

1. Runs the test suite (Python 3.9–3.12 matrix)
2. Runs ruff lint and mypy type checking
3. Builds executables for Linux, Windows, and macOS
4. Uploads them as workflow artifacts

Tag pushes (`v*`) trigger the **Release** workflow which creates a GitHub Release with built binaries.

## Configuration

Config is stored in `~/.file-wayfinder/config.json`. Example:

```json
{
  "monitored_folders": {
    "/home/user/Downloads": [
      "/home/user/Documents",
      "/home/user/Images",
      "/home/user/Installers",
      "/home/user/Temporary"
    ],
    "/home/user/Desktop": [
      "/home/user/Projects",
      "/home/user/Documents"
    ]
  },
  "global_settings": {
    "focus_mode": false,
    "snooze_minutes": 0,
    "batch_mode": false,
    "auto_learn": true,
    "auto_learn_threshold": 3,
    "prompt_delay_seconds": 3.0,
    "theme": "dark",
    "native_notifications": true,
    "duplicate_detection": false,
    "scan_existing_enabled": false,
    "catch_folders": false,
    "pattern_rules_enabled": true,
    "pause_on_dnd": false,
    "batch_mode_style": "one-by-one"
  },
  "ignore_patterns": [
    "~$*",
    ".~lock.*",
    "desktop.ini",
    ".DS_Store",
    "Thumbs.db"
  ],
  "whitelist": []
}
```

## Architecture

```
src/file_wayfinder/
├── __main__.py       # CLI entry point
├── app.py            # Main orchestrator
├── watcher.py        # File system monitoring (watchdog)
├── classifier.py     # File type classification
├── rules.py          # Auto-learning rules engine + pattern rules
├── history.py        # Undo history (SQLite)
├── prompt.py         # User prompt dialogs (tkinter)
├── tray.py           # System tray icon (pystray)
├── constants.py      # Defaults and settings
├── config.py         # Configuration management (JSON, atomic writes)
├── themes.py         # Dark/light theme support
├── notifications.py  # Native toast notifications (plyer)
├── duplicate.py      # SHA256 duplicate detection
├── autostart.py      # Start on login (Windows)
├── settings_ui.py    # Settings dialog
├── rules_ui.py       # Rule management dialog
├── dashboard_ui.py   # Dashboard & batch processing windows
└── conflict_ui.py    # File conflict resolution dialog
```

## Development

```bash
# Install everything
pip install -r requirements-dev.txt
pip install -e .

# Run tests
pytest

# Run with debug logging
python -m file_wayfinder -v

# Lint
ruff check src/ tests/
```

## License

MIT
