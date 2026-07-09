#!/usr/bin/env python3
"""Computes the next semantic version for dash-phonecon's auto-release
pipeline, based on Conventional Commit messages since the last `vX.Y.Z`
git tag.

Bump rules (highest wins across all commits since the last tag):
  - a `!` after the type/scope (e.g. `feat!:`), or a `BREAKING CHANGE:`
    footer anywhere in the commit body -> major
  - any `feat:` commit                                                -> minor
  - anything else (`fix:`, `perf:`, `refactor:`, `chore:`, `docs:`,
    `ci:`, `test:`, or no recognized prefix at all)                   -> patch

Bootstrap case: if no `v*` tag exists yet, this is the project's first
automated release - use the version already committed in the root
VERSION file as-is (no bump needed), so the first release is
predictable instead of guessed from the entire pre-CI commit history.

Prints two lines to stdout:
  <next_version>
  <bump_type>      (one of: initial, none, patch, minor, major)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = REPO_ROOT / "VERSION"

_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_BREAKING_SUBJECT_RE = re.compile(r"^\w+(\([^)]*\))?!:")
_FEAT_SUBJECT_RE = re.compile(r"^feat(\([^)]*\))?:")
_COMMIT_SEP = "---dash-phonecon-commit-end---"


def _sh(*args: str) -> str:
    return subprocess.run(
        args, cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def latest_tag() -> str | None:
    """Highest vX.Y.Z tag reachable in this checkout, or None if none exist."""
    try:
        raw_tags = _sh("git", "tag", "-l", "v*")
    except subprocess.CalledProcessError:
        return None

    versions: list[tuple[tuple[int, int, int], str]] = []
    for tag in raw_tags.splitlines():
        tag = tag.strip()
        match = _TAG_RE.match(tag)
        if match:
            versions.append((tuple(int(part) for part in match.groups()), tag))  # type: ignore[arg-type]

    if not versions:
        return None
    versions.sort()
    return versions[-1][1]


def commit_messages_since(tag: str | None) -> list[str]:
    """Full commit messages (subject + body) since `tag` (or all history if None)."""
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    log = _sh("git", "log", rev_range, f"--pretty=format:%s%n%b{_COMMIT_SEP}")
    return [chunk.strip() for chunk in log.split(_COMMIT_SEP) if chunk.strip()]


def classify_bump(messages: list[str]) -> str:
    bump = "patch"
    for message in messages:
        subject = message.splitlines()[0] if message else ""
        if "BREAKING CHANGE" in message or _BREAKING_SUBJECT_RE.match(subject):
            return "major"  # highest possible - short-circuit
        if _FEAT_SUBJECT_RE.match(subject):
            bump = "minor"
    return bump


def bump_version(version: str, bump: str) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    current_version = VERSION_FILE.read_text().strip()
    tag = latest_tag()

    if tag is None:
        print(current_version)
        print("initial")
        return 0

    messages = commit_messages_since(tag)
    if not messages:
        print(current_version)
        print("none")
        return 0

    bump = classify_bump(messages)
    next_version = bump_version(tag.lstrip("v"), bump)
    print(next_version)
    print(bump)
    return 0


if __name__ == "__main__":
    sys.exit(main())
