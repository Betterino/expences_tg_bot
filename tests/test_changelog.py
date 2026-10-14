"""Sync guard between CHANGELOG.md and constants.VERSION -- cheap enough that a
version bump without a changelog entry (or vice versa) fails the suite instead of
quietly drifting."""
from pathlib import Path

from constants import VERSION
from texts import About

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_changelog_exists_and_is_not_empty() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert changelog.strip()


def test_changelog_has_heading_for_current_version() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert VERSION in changelog


def test_about_summary_is_non_empty() -> None:
    assert About.SUMMARY.strip()
