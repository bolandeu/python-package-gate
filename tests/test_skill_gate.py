"""SKILL.md, the new-package mode and README.md name the gate as the uvx command at the template tag (ADR 0013),
never the old forms."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = (ROOT / "skills" / "cli-builder" / "SKILL.md").read_text()
NEW_PACKAGE = (ROOT / "skills" / "cli-builder" / "reference" / "new-package.md").read_text()
README = (ROOT / "README.md").read_text()

GATE = (
    'uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git'
    '@<template tag>#subdirectory=gate" gate check'
)
FORBIDDEN = ["rb-cli-core", "adopt_core", "uv run rb-gate", "release.py --check"]
FORBIDDEN_IN_SKILL = [*FORBIDDEN, "docs command", "include_ci"]


def test_skill_files_do_not_name_the_old_gate_or_removed_parts():
    for name, text in (("SKILL.md", SKILL), ("new-package.md", NEW_PACKAGE)):
        found = [word for word in FORBIDDEN_IN_SKILL if word in text]
        assert not found, f"{name} names {found}"


def test_readme_does_not_name_the_old_gate():
    found = [word for word in FORBIDDEN if word in README]
    assert not found, f"README.md names {found}"


def test_new_package_runs_the_gate_through_uvx():
    assert GATE in NEW_PACKAGE
