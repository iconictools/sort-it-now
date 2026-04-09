#!/usr/bin/env python3
"""Local build script for Iconic File Filer.

Creates a standalone executable using PyInstaller, and optionally packages it
as a Linux AppImage.

Usage:
    python build.py              # Build onefile for the current platform
    python build.py --onefile    # Explicit single-file executable
    python build.py --onedir     # Directory bundle (needed for AppImage)
    python build.py --appimage   # Build onedir then package as AppImage (Linux only)
"""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys


# Path to icon assets relative to this script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ASSETS_DIR = os.path.join(_SCRIPT_DIR, "assets")
_ICON_PNG = os.path.join(_ASSETS_DIR, "iconic-filer.png")
_ICON_ICO = os.path.join(_ASSETS_DIR, "iconic-filer.ico")
_ICON_512 = os.path.join(_ASSETS_DIR, "iconic-filer-512.png")


def _pyinstaller_cmd(onefile: bool) -> list[str]:
    """Build the base PyInstaller command for the current platform."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=iconic-filer",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--distpath={os.path.join(_SCRIPT_DIR, 'dist')}",
    ]

    # Embed platform-appropriate icon
    system = platform.system()
    if system == "Windows" and os.path.isfile(_ICON_ICO):
        cmd.append(f"--icon={_ICON_ICO}")
    elif system == "Darwin" and os.path.isfile(_ICON_512):
        # PyInstaller accepts PNG on macOS (converts to .icns automatically)
        cmd.append(f"--icon={_ICON_512}")
    elif system == "Linux" and os.path.isfile(_ICON_PNG):
        cmd.append(f"--icon={_ICON_PNG}")

    if onefile:
        cmd.append("--onefile")

    cmd.append(os.path.join(_SCRIPT_DIR, "src", "iconic_filer", "__main__.py"))
    return cmd


def _build_appimage(dist_dir: str) -> None:
    """Create an AppImage from the PyInstaller onedir output.

    Requires appimagetool to be available (downloaded automatically on Linux CI).
    """
    if platform.system() != "Linux":
        print("AppImage packaging is only supported on Linux.")
        sys.exit(1)

    binary_dir = os.path.join(dist_dir, "iconic-filer")
    if not os.path.isdir(binary_dir):
        print(
            f"Directory bundle not found at {binary_dir!r}. "
            "Run 'python build.py --onedir' first."
        )
        sys.exit(1)

    app_dir = os.path.join(_SCRIPT_DIR, "AppDir")
    usr_bin = os.path.join(app_dir, "usr", "bin")
    os.makedirs(usr_bin, exist_ok=True)

    # Copy the onedir bundle into AppDir/usr/bin/
    import shutil
    bundle_dest = os.path.join(usr_bin, "iconic-filer")
    if os.path.exists(bundle_dest):
        shutil.rmtree(bundle_dest)
    shutil.copytree(binary_dir, bundle_dest)

    # AppRun script
    apprun_path = os.path.join(app_dir, "AppRun")
    with open(apprun_path, "w", encoding="utf-8") as fh:
        fh.write(
            '#!/bin/bash\n'
            'HERE="$(dirname "$(readlink -f "${0}")")"\n'
            'exec "${HERE}/usr/bin/iconic-filer/iconic-filer" "$@"\n'
        )
    os.chmod(apprun_path, 0o755)

    # .desktop file (AppImage spec requires one at the root of AppDir)
    desktop_path = os.path.join(app_dir, "iconic-filer.desktop")
    with open(desktop_path, "w", encoding="utf-8") as fh:
        fh.write(
            "[Desktop Entry]\n"
            "Name=Iconic File Filer\n"
            "Exec=iconic-filer\n"
            "Icon=iconic-filer\n"
            "Type=Application\n"
            "Categories=Utility;FileManager;\n"
            "Comment=Real-time file organizer assistant\n"
            "StartupNotify=false\n"
        )

    # Copy icon to AppDir root (AppImage spec: <Name>.png at root)
    icon_dst = os.path.join(app_dir, "iconic-filer.png")
    if os.path.isfile(_ICON_PNG):
        shutil.copy2(_ICON_PNG, icon_dst)
    else:
        # Generate a placeholder icon if assets/ doesn't exist
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (256, 256), "#1e1e2e")
            ImageDraw.Draw(img).ellipse([8, 8, 248, 248], outline="#89b4fa", width=8)
            img.save(icon_dst)
        except Exception:
            pass

    # Find or download appimagetool
    appimagetool = _find_appimagetool()
    if not appimagetool:
        print(
            "appimagetool not found. Download it from:\n"
            "  https://github.com/AppImage/AppImageKit/releases\n"
            "and make it executable, then re-run."
        )
        sys.exit(1)

    out_appimage = os.path.join(dist_dir, "IconicFiler-x86_64.AppImage")
    env = dict(os.environ, ARCH="x86_64")
    subprocess.check_call(
        [appimagetool, app_dir, out_appimage],
        env=env,
    )
    print(f"\nAppImage built: {out_appimage}")


def _find_appimagetool() -> str | None:
    """Return the path to appimagetool if it exists, else None."""
    import shutil as _shutil
    # Check common locations
    candidates = [
        "appimagetool",
        "appimagetool-x86_64.AppImage",
        os.path.join(_SCRIPT_DIR, "appimagetool"),
        os.path.join(_SCRIPT_DIR, "appimagetool-x86_64.AppImage"),
    ]
    for candidate in candidates:
        found = _shutil.which(candidate) or (
            os.path.isfile(candidate) and os.access(candidate, os.X_OK) and candidate
        )
        if found:
            return found
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Iconic File Filer executable")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Create a single-file executable (default).",
    )
    mode.add_argument(
        "--onedir",
        action="store_true",
        help="Create a directory bundle instead of a single file.",
    )
    mode.add_argument(
        "--appimage",
        action="store_true",
        help="Build a directory bundle then package as an AppImage (Linux only).",
    )
    args = parser.parse_args()

    dist_dir = os.path.join(_SCRIPT_DIR, "dist")

    if args.appimage:
        # Build onedir first, then package
        cmd = _pyinstaller_cmd(onefile=False)
        print(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        print("\nBuilding AppImage…")
        _build_appimage(dist_dir)
    else:
        onefile = not args.onedir
        cmd = _pyinstaller_cmd(onefile=onefile)
        print(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        print("\nBuild complete! Output in dist/")


if __name__ == "__main__":
    main()
