"""The existing-package mode file: gate first, fix each red step by its Standard section, then the optional parts."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODE = (ROOT / "skills" / "cli-builder" / "reference" / "existing-package.md").read_text()
STANDARD = (ROOT / "skills" / "cli-builder" / "reference" / "standard.md").read_text()

GATE = (
    'uvx --from "git+https://homeserver.tailee01ab.ts.net:3000/bolandeu/cli-generator.git'
    '@<template tag>#subdirectory=gate" gate check'
)
FORBIDDEN = [
    "adopt_core",
    "uv run rb-gate",
    "release.py --check",
    "rb-cli-core",
    "include_ci",
    "docs command",
    "<cli> docs",
]


def section(text: str, start: str) -> str:
    """The text from the heading line `start` up to the next heading of the same or a higher level."""
    level = len(start) - len(start.lstrip("#"))
    match = re.search(rf"^{re.escape(start)}.*?(?=^#{{1,{level}}} |\Z)", text, re.S | re.M)
    assert match, f"no section {start!r}"
    return match.group(0)


def test_the_first_step_is_the_uvx_gate_and_the_loop_fixes_red_steps_by_standard_section():
    loop = section(MODE, "## The loop")
    assert loop.index(GATE) < loop.index("Standard section")
    assert "release: gate passed" in loop
    assert "copier update" in loop and "not required" in loop


def test_the_update_part_reaches_the_uvx_gate():
    update = section(MODE, "## A package from the template that wants updates")
    order = [
        "git status",
        "copier update",
        "scripts/release.py",
        "cli-core",
        ".agents/antagor/antagor.toml",
        "pytest --snapshot-update",
        GATE,
        "release: gate passed",
    ]
    positions = [update.find(word) for word in order]
    assert -1 not in positions, dict(zip(order, positions))
    assert positions == sorted(positions)
    assert "copier_update_staged.py" in update


def test_every_linked_standard_section_exists():
    headings = set(re.findall(r"^#{2,3} (.+)$", STANDARD, re.M))
    cited = re.findall(r"Standard, ([^)`;:.|\n]+)", MODE)
    assert cited
    assert not [name for name in cited if name.strip() not in headings]


def test_the_mode_names_no_old_gate_or_removed_part():
    found = [word for word in FORBIDDEN if word in MODE]
    assert not found, f"existing-package.md names {found}"
