#!/usr/bin/env python3
"""Local build script for Sort It Now.

Creates a standalone executable using PyInstaller.

Usage:
    python build.py              # Build for the current platform
    python build.py --onefile    # Single-file executable
"""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Sort It Now executable")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create a single-file executable instead of a directory bundle.",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=sort-it-now",
        "--windowed",
        "--noconfirm",
        "--clean",
        "src/sort_it_now/__main__.py",
    ]
    if args.onefile:
        cmd.append("--onefile")

    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    print("\n✅ Build complete! Output in dist/")


if __name__ == "__main__":
    main()
