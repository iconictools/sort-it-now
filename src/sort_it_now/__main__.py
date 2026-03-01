"""Entry point for Sort It Now.

Usage:
    python -m sort_it_now          # Run the app (GUI)
    python -m sort_it_now --help   # Show help
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys

from sort_it_now import __version__
from sort_it_now.constants import DEFAULT_CONFIG_DIR, DEFAULT_LOG_FILE


def _setup_logging(verbose: bool) -> None:
    """Configure logging to both console and a rotating log file."""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(fmt))
    root_logger.addHandler(console)

    # Rotating file handler — always active
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
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    from sort_it_now.config import Config
    from sort_it_now.app import App

    config = Config(args.config)
    app = App(config=config)
    app.run()


if __name__ == "__main__":
    main()
