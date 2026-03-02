"""Entry point for Sort It Now.

Usage:
    python -m sort_it_now          # Run the app (GUI)
    python -m sort_it_now --help   # Show help
    python -m sort_it_now --setup-cli  # CLI setup wizard
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

from sort_it_now import __version__  # noqa: E402
from sort_it_now.constants import DEFAULT_CONFIG_DIR, DEFAULT_LOG_FILE  # noqa: E402


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
        prog="sort-it-now",
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

    from sort_it_now.config import Config
    from sort_it_now.app import App

    config = Config(args.config)

    # CLI setup mode (Q2.1c)
    if args.setup_cli:
        from sort_it_now.prompt import cli_setup

        folders = cli_setup()
        for folder, dests in folders.items():
            config.add_monitored_folder(folder, dests)
        if not folders:
            return

    app = App(config=config)
    app.run()


if __name__ == "__main__":
    main()
