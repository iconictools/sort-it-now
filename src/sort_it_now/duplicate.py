"""Duplicate file detection for Sort It Now."""

from __future__ import annotations

import hashlib
import logging
import os

logger = logging.getLogger(__name__)


def compute_file_hash(
    filepath: str,
    algorithm: str = "sha256",
    chunk_size: int = 8192,
) -> str:
    """Return the hex digest of *filepath* using *algorithm*."""
    h = hashlib.new(algorithm)
    with open(filepath, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def find_duplicate(src: str, dest_dir: str) -> str | None:
    """Check if an identical file exists in *dest_dir*.

    Returns the path of the duplicate if found, *None* otherwise.
    """
    if not os.path.isdir(dest_dir):
        return None

    try:
        src_hash = compute_file_hash(src)
    except OSError:
        return None

    src_size = os.path.getsize(src)

    for entry in os.scandir(dest_dir):
        if not entry.is_file():
            continue
        try:
            if entry.stat().st_size != src_size:
                continue
            if compute_file_hash(entry.path) == src_hash:
                return entry.path
        except OSError:
            continue

    return None
