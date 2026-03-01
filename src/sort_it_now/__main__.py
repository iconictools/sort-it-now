"""Entry point for Sort It Now.

Usage:
    python -m sort_it_now          # Run the app (GUI)
    python -m sort_it_now --help   # Show help
"""

import argparse
import logging
import sys

from sort_it_now import __version__


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

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from sort_it_now.config import Config
    from sort_it_now.app import App

    config = Config(args.config)
    app = App(config=config)
    app.run()


if __name__ == "__main__":
    main()
