"""Smart file classification for File Wayfinder.

Suggests destination folders based on file extension, name patterns,
and learned rules.
"""

from __future__ import annotations

import os
from fnmatch import fnmatch

from file_wayfinder.constants import FILE_TYPE_MAP, TEMP_EXTENSIONS


def is_temp_file(filepath: str) -> bool:
    """Return *True* if the file looks like an incomplete download."""
    _, ext = os.path.splitext(filepath)
    return ext.lower() in TEMP_EXTENSIONS


def matches_ignore_pattern(filename: str, patterns: list[str]) -> bool:
    """Return *True* if *filename* matches any of the ignore *patterns*."""
    for pattern in patterns:
        if fnmatch(filename, pattern):
            return True
    return False


def classify_by_extension(filepath: str) -> str | None:
    """Return a suggested category based on the file extension, or *None*."""
    _, ext = os.path.splitext(filepath)
    return FILE_TYPE_MAP.get(ext.lower())


def suggest_destinations(
    filepath: str,
    available_destinations: list[str],
    learned_rules: dict[str, str] | None = None,
) -> list[str]:
    """Return an ordered list of suggested destination folders.

    1. Exact match from *learned_rules* (extension → destination).
    2. Category-based match against *available_destinations*.
    3. Remaining destinations as-is.
    """
    suggestions: list[str] = []

    _, ext = os.path.splitext(filepath)
    ext_lower = ext.lower()

    # 1. Learned rule
    if learned_rules and ext_lower in learned_rules:
        rule_dest = learned_rules[ext_lower]
        if rule_dest in available_destinations:
            suggestions.append(rule_dest)

    # 2. Category hint
    category = classify_by_extension(filepath)
    if category:
        for dest in available_destinations:
            if dest not in suggestions and category.lower() in dest.lower():
                suggestions.append(dest)

    # 3. Fill with remaining
    for dest in available_destinations:
        if dest not in suggestions:
            suggestions.append(dest)

    return suggestions
