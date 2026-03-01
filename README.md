# Sort It Now 🗂️

> Tray-resident real-time file organizer assistant — put your files where you want, *right when they arrive*.

[![Build](https://github.com/trabalhefabricio/sort-it-now/actions/workflows/build.yml/badge.svg)](https://github.com/trabalhefabricio/sort-it-now/actions/workflows/build.yml)

## What it does

Sort It Now lives in your system tray and watches folders you choose (Downloads, Desktop, Screenshots, etc.). When a new file appears it asks you **"Where should this go?"** with a quick popup showing your configured destinations.

Instead of dumping files and cleaning up later, you make a micro-decision at the moment of action — building a tidy file system as a habit.

### Features

| Feature | Description |
|---|---|
| **Real-time monitoring** | Detects new, moved, and modified files instantly via `watchdog` |
| **Smart prompts** | Non-intrusive popup with context-aware destination suggestions |
| **Auto-learning rules** | After 3 consistent choices the app sorts that file type automatically |
| **Focus / Snooze mode** | Queues prompts during deep work, processes them when you're ready |
| **Undo** | One-click revert from the tray menu |
| **Dashboard** | Quick view of recent actions and pending files |
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
python -m sort_it_now

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

1. Runs the test suite
2. Builds executables for Linux, Windows, and macOS
3. Uploads them as workflow artifacts

You can also trigger a build manually via the **Run workflow** button on the Actions tab.

## Configuration

Config is stored in `~/.sort-it-now/config.json`. Example:

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
    "prompt_delay_seconds": 3.0
  },
  "ignore_patterns": [
    "~$*",
    ".~lock.*",
    "desktop.ini",
    ".DS_Store",
    "Thumbs.db"
  ]
}
```

## Architecture

```
src/sort_it_now/
├── __main__.py     # CLI entry point
├── app.py          # Main orchestrator
├── watcher.py      # File system monitoring (watchdog)
├── classifier.py   # File type classification
├── rules.py        # Auto-learning rules engine
├── history.py      # Undo history (SQLite)
├── prompt.py       # User prompt dialogs (tkinter)
├── tray.py         # System tray icon (pystray)
└── constants.py    # Defaults and settings
```

## Development

```bash
# Install everything
pip install -r requirements-dev.txt
pip install -e .

# Run tests
pytest

# Run with debug logging
python -m sort_it_now -v
```

## License

MIT
