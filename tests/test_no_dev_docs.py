"""What packages receive (template, gate code, skill) cites no cli-generator development docs."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEARCHED = ["template", "gate/rb_gate", "gate/standard", "skills"]
FORBIDDEN = re.compile(
    r"architecture\.md|conventions\.md|help-standard\.md|refactor-checklist\.md|§ ?\d|docs/adr/\d|docs/plans"
    r"|\bADR[ -]?\d|\bCG-\d|\bIDEA-\d|\(Human, 20"
)


def _hits():
    files = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", *SEARCHED],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split("\n")
    for name in filter(None, files):
        try:
            text = (ROOT / name).read_text()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            match = FORBIDDEN.search(line)
            if match:
                yield f"{name}:{number}: {line.strip()}"


def test_no_development_docs_cited():
    assert list(_hits()) == []


def test_gate_external_dependency_message_names_section():
    source = (ROOT / "gate/rb_gate/gate.py").read_text()
    assert "doesn't match the code (the Standard, Technology)" in source
