#!/usr/bin/env python3
"""Writes a resolved release version into every file that needs to carry
it, the same "one source of truth drives hand-synced copies" pattern
this repo already uses for the WebSocket protocol's MessageType
constants (see PLAN.md) - except here the copies are kept in sync by
this script instead of by hand.

Run by .github/workflows/release.yml only. Contributors should not
normally need to run this themselves - version bumps happen
automatically from Conventional Commit messages (see AGENTS.md).

Usage: bump_versions.py <version>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def version_code_for(version: str) -> int:
    """Android versionCode must strictly increase between installs. Deriving
    it from semver (major*10000 + minor*100 + patch) means every release
    ordering is automatically correct with no separate counter to track."""
    major, minor, patch = (int(part) for part in version.split("."))
    return major * 10000 + minor * 100 + patch


def write_root_version(version: str) -> None:
    (REPO_ROOT / "VERSION").write_text(f"{version}\n")


def write_linux_version(version: str) -> None:
    """Note: compare match count, not before/after text equality, to decide
    whether the pattern was found - a bump to the same version the file
    already has (e.g. this project's first release, where VERSION already
    contains the bootstrap version) is a legitimate no-op substitution and
    must not be mistaken for "pattern not found"."""
    path = REPO_ROOT / "linux/src/dashphone/__init__.py"
    text = path.read_text()
    pattern = re.compile(r'__version__ = "[^"]+"')
    if not pattern.search(text):
        raise SystemExit(f"Could not find __version__ to update in {path}")
    new_text = pattern.sub(f'__version__ = "{version}"', text)
    path.write_text(new_text)


def write_android_version(version: str, version_code: int) -> None:
    """See write_linux_version for why presence is checked independently of
    the substitutions instead of comparing before/after text."""
    path = REPO_ROOT / "android/app/build.gradle"
    text = path.read_text()
    code_pattern = re.compile(r"versionCode \d+")
    name_pattern = re.compile(r'versionName "[^"]+"')
    if not code_pattern.search(text) or not name_pattern.search(text):
        raise SystemExit(f"Could not find versionCode/versionName to update in {path}")
    new_text = code_pattern.sub(f"versionCode {version_code}", text)
    new_text = name_pattern.sub(f'versionName "{version}"', new_text)
    path.write_text(new_text)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: bump_versions.py <version>")
    version = sys.argv[1]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(f"Version must be X.Y.Z, got: {version!r}")

    version_code = version_code_for(version)
    write_root_version(version)
    write_linux_version(version)
    write_android_version(version, version_code)

    print(f"Bumped every version file to {version} (Android versionCode {version_code})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
