"""Entry point for File Wayfinder.

Usage:
    python -m file_wayfinder          # Run the app (GUI)
    python -m file_wayfinder --help   # Show help
    python -m file_wayfinder --setup-cli  # CLI setup wizard
"""

from __future__ import annotations

import sys

# Reconfigure stdout/stderr to UTF-8 early, before any other imports or
# print/log calls.  On Windows the default encoding is cp1252 which cannot
# represent many Unicode characters and causes UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse  # noqa: E402
import logging  # noqa: E402
import logging.handlers  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402

from file_wayfinder import __version__  # noqa: E402
from file_wayfinder.constants import DEFAULT_CONFIG_DIR, DEFAULT_LOG_FILE  # noqa: E402


def _setup_logging(verbose: bool) -> None:
    """Configure logging to both console and a rotating log file."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console handler -- sys.stderr is already reconfigured to UTF-8 at
    # module level, so we can attach directly.
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(console)

    # Rotating file handler -- always active
    os.makedirs(DEFAULT_CONFIG_DIR, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        DEFAULT_LOG_FILE,
        maxBytes=2 * 1024 * 1024,  # 2 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(file_handler)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="file-wayfinder",
        description="Tray-resident real-time file organizer assistant.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to config JSON file.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging."
    )
    parser.add_argument(
        "--setup-cli",
        action="store_true",
        help="Run the CLI setup wizard instead of the GUI wizard.",
    )
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    # ── Auto-migrate old config dir ───────────────────────────────────
    _old_dir = os.path.join(os.path.expanduser("~"), ".sort-it-now")
    _new_dir = DEFAULT_CONFIG_DIR
    if os.path.isdir(_old_dir) and not os.path.exists(
        os.path.join(_new_dir, "config.json")
    ):
        try:
            shutil.copytree(_old_dir, _new_dir, dirs_exist_ok=True)
            logging.getLogger(__name__).info(
                "Auto-migrated config from %s to %s", _old_dir, _new_dir
            )
        except Exception as _exc:
            logging.getLogger(__name__).warning(
                "Could not migrate old config: %s", _exc
            )

    from file_wayfinder.config import Config
    from file_wayfinder.app import App

    config = Config(args.config)

    # CLI setup mode (Q2.1c)
    if args.setup_cli:
        from file_wayfinder.prompt import cli_setup

        folders = cli_setup()
        for folder, dests in folders.items():
            config.add_monitored_folder(folder, dests)
        if not folders:
            return

    # ── Apply customtkinter appearance early ─────────────────────────
    try:
        from file_wayfinder.themes import apply_ctk_appearance
        apply_ctk_appearance(config.get_setting("theme", "dark"))
    except Exception:
        pass

    # ── Multi-instance handling ──────────────────────────────────────
    from file_wayfinder.ipc import is_running, send_command

    if is_running():
        behavior = config.get_setting("multi_instance_behavior", "prompt")

        if behavior == "ignore":
            # Start a completely independent second instance (no merge).
            pass

        else:
            # "always-merge" or "prompt" — try to merge into the running instance.
            merge = True
            if behavior == "prompt":
                import tkinter as tk
                from tkinter import messagebox

                _root = tk.Tk()
                _root.withdraw()
                merge = messagebox.askyesno(
                    "File Wayfinder is already running",
                    "Another instance is already running.\n\n"
                    "Do you want to add a new folder to the running instance?\n\n"
                    "(Choose No to open a separate, independent instance.)",
                )
                _root.destroy()

            if merge:
                # Ask the user which folder to add, then send it via IPC.
                import tkinter as tk
                from tkinter import filedialog

                _root = tk.Tk()
                _root.withdraw()
                folder = filedialog.askdirectory(
                    title="Choose a folder for the running File Wayfinder to watch"
                )
                _root.destroy()
                if folder:
                    send_command(f"ADD_FOLDER:{folder}")
                    logging.getLogger(__name__).info(
                        "Sent ADD_FOLDER command to running instance: %s", folder
                    )
                return  # second instance exits after delegating

    # ── Normal startup ────────────────────────────────────────────────
    app = App(config=config)
    app.run()


if __name__ == "__main__":
    main()
