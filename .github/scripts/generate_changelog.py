#!/usr/bin/env python3
"""Generates a Conventional-Commits changelog section for one release and
prepends it to the root CHANGELOG.md, so every auto-release documents
itself with zero manual writing - same "one source of truth" pattern as
compute_version.py/bump_versions.py (see AGENTS.md).

Groups commits since the last `vX.Y.Z` tag into Features / Fixes / Other,
skipping the bot's own "chore: release ..." commits and merge commits (no
useful subject for a changelog reader).

Usage: generate_changelog.py <new_version>
Prints the generated section's markdown to stdout as well, so the caller
can reuse the same text for the GitHub Release notes without re-deriving it.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date, timezone
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"

_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_TYPE_RE = re.compile(r"^(?P<type>\w+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$")
_COMMIT_SEP = "---dash-phonecon-commit-end---"

_SECTION_TITLES = {
    "feat": "### Features",
    "fix": "### Fixes",
    "perf": "### Performance",
    "docs": "### Docs",
    "other": "### Other",
}
_SECTION_ORDER = ["feat", "fix", "perf", "docs", "other"]


def _sh(*args: str) -> str:
    return subprocess.run(
        args, cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def latest_tag() -> str | None:
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


def commit_subjects_since(tag: str | None) -> list[str]:
    """One-line subjects only (changelog entries are the subject line, not
    the full body) - merges excluded (--no-merges) since they have no
    single meaningful subject for a changelog reader."""
    rev_range = f"{tag}..HEAD" if tag else "HEAD"
    log = _sh("git", "log", rev_range, "--no-merges", f"--pretty=format:%s{_COMMIT_SEP}")
    subjects = [chunk.strip() for chunk in log.split(_COMMIT_SEP) if chunk.strip()]
    return [s for s in subjects if not s.startswith("chore: release v")]


def classify(subject: str) -> tuple[str, str]:
    """Returns (bucket, display_text). Falls back to 'other' with the raw
    subject when it doesn't match the Conventional Commits shape at all."""
    match = _TYPE_RE.match(subject)
    if not match:
        return "other", subject
    ctype = match.group("type").lower()
    scope = match.group("scope")
    desc = match.group("desc").strip()
    display = f"**{scope}:** {desc}" if scope else desc
    if match.group("breaking"):
        display = f"{display} (BREAKING CHANGE)"
    bucket = ctype if ctype in _SECTION_TITLES else "other"
    return bucket, display


def build_section(version: str, subjects: list[str]) -> str:
    buckets: dict[str, list[str]] = {key: [] for key in _SECTION_ORDER}
    for subject in subjects:
        bucket, display = classify(subject)
        buckets[bucket].append(display)

    today = datetime.now(timezone.utc).date().isoformat()
    lines = [f"## v{version} - {today}", ""]
    wrote_any = False
    for bucket in _SECTION_ORDER:
        entries = buckets[bucket]
        if not entries:
            continue
        wrote_any = True
        lines.append(_SECTION_TITLES[bucket])
        lines.extend(f"- {entry}" for entry in entries)
        lines.append("")
    if not wrote_any:
        lines.append("- No user-facing changes.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_changelog.py <new_version>")
    version = sys.argv[1]

    tag = latest_tag()
    subjects = commit_subjects_since(tag)
    section = build_section(version, subjects)

    intro = (
        "# Changelog\n\n"
        "All notable changes to dash-phonecon are documented here, "
        "auto-generated from Conventional Commit messages on every release.\n"
    )
    if CHANGELOG_FILE.exists():
        existing = CHANGELOG_FILE.read_text()
        # Everything after the fixed intro block is prior release history;
        # keep it as-is and prepend the new section above it.
        marker = "release.\n"
        idx = existing.find(marker)
        history = existing[idx + len(marker):].lstrip("\n") if idx != -1 else existing
    else:
        history = ""

    new_content = f"{intro}\n{section}\n{history}".rstrip() + "\n"
    CHANGELOG_FILE.write_text(new_content)

    print(section)
    return 0


if __name__ == "__main__":
    sys.exit(main())
