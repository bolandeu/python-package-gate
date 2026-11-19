"""`gate check`: the release gate, run against the package in the cwd (fixture packages: conftest.py)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from typer.core import TyperGroup, TyperOption
from typer.main import get_command
from typer.testing import CliRunner

from conftest import PYPROJECT, git
from rb_gate.cli import app
from rb_gate.gate import Gate, Step, StepFailed, changed_existing_tests, contract_summary, external_programs

CLI = "rb-gate"
STEPS = [
    "secret scan",
    "uv lock --check",
    "ruff check",
    "ruff format --check",
    "ty check",
    "pytest",
    "contracts",
    "existing tests",
    "install section",
    "external dependencies",
    "build + install wheel",
    "fresh install",
    "standard: commands",
    "standard: json",
    "standard: errors",
    "standard: health",
    "standard: docs",
    "standard: params",
    "standard: ci",
    "vulnerability audit",
]


def _check():
    return CliRunner().invoke(app, ["check"], prog_name=CLI)


def test_a_passing_package_passes_every_step(in_package) -> None:
    in_package('"""A demo package."""\n')

    result = _check()

    lines = result.stdout.splitlines()
    assert [line.split(" ... ")[0] for line in lines[:-1]] == [f"release: {step}" for step in STEPS], result.output
    assert all(line.split(" ... ")[1].startswith("ok") for line in lines[:-1])
    assert lines[-1] == "release: gate passed"
    assert result.exit_code == 0


def test_a_test_that_fails_under_the_ci_variables_fails_the_pytest_step(in_package, monkeypatch) -> None:
    root = in_package('"""A demo package."""\n')
    for name in ("GITHUB_ACTIONS", "FORCE_COLOR", "PY_COLORS"):
        monkeypatch.delenv(name, raising=False)
    (root / "tests" / "test_ci.py").write_text(
        'import os\n\n\ndef test_runs_outside_ci() -> None:\n    assert "GITHUB_ACTIONS" not in os.environ\n'
    )

    result = _check()

    assert result.stdout.splitlines()[-1] == "release: pytest ... FAILED"
    assert "test_runs_outside_ci" in result.stderr
    assert result.exit_code == 1


def test_a_ruff_error_stops_the_gate_at_ruff_check(in_package) -> None:
    in_package("import os\n")

    result = _check()

    lines = result.stdout.splitlines()
    assert [line.split(" ... ")[0] for line in lines] == [f"release: {step}" for step in STEPS[:3]]
    assert lines[-1] == "release: ruff check ... FAILED"
    assert "release: gate step 'ruff check' failed:" in result.stderr
    assert "F401" in result.stderr
    assert result.stderr.strip().splitlines()[-1] == "release: code failed"
    assert result.exit_code == 1


# --- --keep-going: every step runs, the failed ones are listed at the end -------------------------------------------


def _fake_steps(monkeypatch: pytest.MonkeyPatch, *steps: Step) -> None:
    monkeypatch.setattr(Gate, "steps", lambda self: list(steps))


def _pass() -> str:
    return ""


def _fail() -> str:
    raise StepFailed("it broke")


def _keep_going():
    return CliRunner().invoke(app, ["check", "--keep-going"], prog_name=CLI)


def test_keep_going_runs_every_step_and_lists_the_failed_ones(in_package, monkeypatch) -> None:
    in_package('"""A demo package."""\n')
    _fake_steps(monkeypatch, Step("one", _fail), Step("two", _pass), Step("three", _fail), Step("four", _pass))

    result = _keep_going()

    assert result.stdout.splitlines() == [
        "release: one ... FAILED",
        "release: two ... ok",
        "release: three ... FAILED",
        "release: four ... ok",
    ]
    assert result.stderr.strip().splitlines()[-2:] == ["release: failed steps: one, three", "release: code failed"]
    assert result.exit_code == 1


def test_keep_going_lists_a_step_that_needs_a_failed_step_as_skipped(in_package, monkeypatch) -> None:
    in_package('"""A demo package."""\n')
    _fake_steps(monkeypatch, Step("build", _fail), Step("install", _pass, needs="build"), Step("lint", _pass))

    result = _keep_going()

    assert result.stdout.splitlines() == [
        "release: build ... FAILED",
        "release: install ... skipped (needs 'build')",
        "release: lint ... ok",
    ]
    stderr_end = result.stderr.strip().splitlines()[-3:]
    assert stderr_end == ["release: failed steps: build", "release: skipped steps: install", "release: code failed"]
    assert result.exit_code == 1


def test_keep_going_with_only_the_audit_failed_exits_3(in_package, monkeypatch) -> None:
    in_package('"""A demo package."""\n')
    _fake_steps(monkeypatch, Step("lint", _pass), Step("vulnerability audit", _fail))

    result = _keep_going()

    assert result.stderr.strip().splitlines()[-2:] == [
        "release: failed steps: vulnerability audit",
        "release: audit failed",
    ]
    assert result.exit_code == 3


def test_keep_going_with_every_step_passing_passes(in_package, monkeypatch) -> None:
    in_package('"""A demo package."""\n')
    _fake_steps(monkeypatch, Step("lint", _pass), Step("tests", _pass))

    result = _keep_going()

    assert result.stdout.splitlines()[-1] == "release: gate passed"
    assert result.exit_code == 0


def test_without_keep_going_the_gate_stops_at_the_first_failed_step(in_package, monkeypatch) -> None:
    in_package('"""A demo package."""\n')
    _fake_steps(monkeypatch, Step("one", _pass), Step("two", _fail), Step("three", _pass))

    result = _check()

    assert result.stdout.splitlines() == ["release: one ... ok", "release: two ... FAILED"]
    assert result.stderr.splitlines() == ["", "release: gate step 'two' failed:", "it broke", "release: code failed"]
    assert result.exit_code == 1


def test_the_help_names_keep_going_and_when_to_use_it() -> None:
    # The option as Click holds it, not the Rich help page: CI forces colour codes and panel borders into that page.
    group = get_command(app)
    assert isinstance(group, TyperGroup)
    (keep_going,) = (param for param in group.commands["check"].params if "--keep-going" in param.opts)
    assert isinstance(keep_going, TyperOption)

    assert "first run on an old package" in (keep_going.help or "")


def test_outside_a_package_is_a_usage_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = _check()

    assert result.exit_code == 2
    assert "pyproject.toml" in result.stderr
    assert result.stdout == ""
    assert list(tmp_path.iterdir()) == []


def test_project_option_runs_the_gate_against_that_package(in_package, tmp_path: Path, monkeypatch) -> None:
    root = in_package('"""A demo package."""\n')
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    result = CliRunner().invoke(app, ["--project", str(root), "check"], prog_name=CLI)

    assert result.stdout.splitlines()[-1] == "release: gate passed", result.output
    assert result.exit_code == 0


def test_project_option_without_pyproject_is_a_usage_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["--project", str(empty), "check"], prog_name=CLI)

    assert result.exit_code == 2
    assert "pyproject.toml" in result.stderr
    assert str(empty) in result.stderr.replace("\n", "")  # the error panel wraps a long path


# --- the steps, one at a time ------------------------------------------------------------------------------------


OLD_TESTS = """
LIMIT = 3


def helper():
    return 1


def test_a():
    assert helper() == 1


def test_b():
    assert True


class TestGroup:
    def test_c(self):
        assert LIMIT
"""

NEW_TESTS = """
LIMIT = 4


def test_b():
    assert True


def test_a():
    assert helper() == 2


class TestGroup:
    def test_c(self):
        assert LIMIT


def test_new():
    assert True
"""


CONTRACT_RUN = """
tests/test_contracts.py::test_contract[tools-catalog:describe-json] PASSED [ 25%]
tests/test_contracts.py::test_contract[windmill:search-json] FAILED [ 50%]
tests/test_contracts.py::test_contract[windmill:old-field] SKIPPED (windmill:old-field: provider <0.7) [ 75%]
tests/test_contracts.py::test_contract[astro:pages-view] PASSED [100%]
"""

# pytest-xdist -vv writes a `[gwN] [ NN%]` prefix and the status before the node id (semkit, 2026-10-24).
CONTRACT_RUN_XDIST = """
[gw0] [ 25%] PASSED tests/test_contracts.py::test_contract[tools-catalog:describe-json]
[gw0] [ 50%] FAILED tests/test_contracts.py::test_contract[windmill:search-json]
[gw1] [ 75%] SKIPPED tests/test_contracts.py::test_contract[windmill:old-field]
[gw1] [100%] PASSED tests/test_contracts.py::test_contract[astro:pages-view]
"""


# Split in two: the literal would trip gitleaks on this very file.
FAKE_AWS_KEY = "AKIA" + "QYLPMN7RT2X4WB3K"


INDEXES = Path(__file__).resolve().parent / "data" / "index"  # rb-x 0.1.0 in gitea/, a higher rb-x 0.9.0 in pypi/


def _project_with_rb_x_from_gitea(root: Path) -> None:
    (root / "pyproject.toml").write_text(f"""
[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["rb-x>=0.1"]

[[tool.uv.index]]
name = "pypi"  # stands in for PyPI, which has a higher rb-x
url = "{INDEXES / "pypi"}"
format = "flat"
default = true

[[tool.uv.index]]
name = "gitea"
url = "{INDEXES / "gitea"}"
format = "flat"
explicit = true

[tool.uv.sources]
rb-x = {{ index = "gitea" }}
""")
    subprocess.run(["uv", "lock", "--offline", "--quiet"], cwd=root, check=True)  # noqa: S607


def _venv(path: Path) -> Path:
    subprocess.run(["uv", "venv", "--offline", "--quiet", str(path)], check=True)  # noqa: S603, S607
    return path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _rb_x_index(python: Path) -> str:
    code = "import rb_x; print(rb_x.INDEX)"
    return subprocess.run([str(python), "-c", code], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603


def _pyproject(root: Path, text: str) -> Gate:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(text)
    return Gate(root)


def test_gate_extras_come_from_the_package_pyproject(tmp_path: Path) -> None:
    assert _pyproject(tmp_path / "a", '[project]\nname = "a"\n').gate_extras() == []
    configured = _pyproject(tmp_path / "b", '[tool.cli-generator]\ngate_extras = ["browser"]\n')
    assert configured.gate_extras() == ["browser"]
    assert configured.run_command(("uv", "--version")) == ""


def test_external_programs_found_by_literal_name() -> None:
    source = """
import shutil, subprocess
from .core import deps
exe = deps.require_cli("serp", "0.3.0")
shutil.which("ffmpeg")
subprocess.run(["npx", "-y", "lighthouse"], check=True)
subprocess.check_output(("git", "rev-parse", "HEAD"))
subprocess.run([exe, "search"])  # built at runtime: covered by require_cli above
"""
    assert external_programs(source) == {"serp", "ffmpeg", "npx", "git"}


def test_external_registry_must_match_code(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text('import shutil\nshutil.which("ffmpeg")\n')

    gate = _pyproject(tmp_path, "")
    with pytest.raises(StepFailed, match=re.escape("`ffmpeg` is run in src/mod.py but not declared")):
        gate.check_external_deps()

    ffmpeg = '[[tool.rb.external]]\nname = "ffmpeg"\nwhy = "video"\n'
    node = '[[tool.rb.external]]\nname = "node"\nwhy = "{why}"\n'
    _pyproject(tmp_path, ffmpeg + node.format(why="unused"))
    with pytest.raises(StepFailed, match=re.escape("`node` is declared but nothing in src/ runs it")):
        gate.check_external_deps()

    _pyproject(tmp_path, ffmpeg + node.format(why="unused") + "detect = false\n")  # an injected runner: on trust
    assert gate.check_external_deps() == "2 declared, all used (1 with detect = false)"

    _pyproject(tmp_path, ffmpeg + node.format(why="") + "detect = false\n")
    with pytest.raises(StepFailed, match="needs `name` and `why`"):
        gate.check_external_deps()

    (tmp_path / "src" / "mod.py").write_text("")
    _pyproject(tmp_path, "")
    assert gate.check_external_deps() == "none used, none declared"


def test_existing_tests_that_changed() -> None:
    """Changed or removed tests are listed; moved, untouched and new ones aren't."""
    assert changed_existing_tests("tests/t.py", OLD_TESTS, NEW_TESTS) == [
        "tests/t.py: module-level code changed",
        "tests/t.py::helper removed",
        "tests/t.py::test_a changed",
    ]
    assert changed_existing_tests("tests/t.py", OLD_TESTS, None) == ["tests/t.py removed"]
    assert changed_existing_tests("tests/t.py", OLD_TESTS, OLD_TESTS) == []
    assert changed_existing_tests("tests/t.py", "def broken(:\n", NEW_TESTS) == ["tests/t.py changed"]


def test_existing_tests_step_reports_against_the_last_tag(tmp_path: Path) -> None:
    gate = _pyproject(tmp_path, "")
    assert gate.check_existing_tests() == "no release tag yet"

    (tmp_path / "tests" / "snapshots").mkdir(parents=True)
    (tmp_path / "tests" / "test_x.py").write_text(OLD_TESTS)
    (tmp_path / "tests" / "snapshots" / "help.txt").write_text("old\n")
    (tmp_path / "README.md").write_text("old\n")
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "i")
    git(tmp_path, "tag", "-a", "v0.1.0", "-m", "v0.1.0")
    assert gate.check_existing_tests() == "none changed since v0.1.0"

    (tmp_path / "tests" / "test_x.py").write_text(NEW_TESTS)
    (tmp_path / "tests" / "snapshots" / "help.txt").write_text("new\n")
    (tmp_path / "tests" / "test_added.py").write_text("def test_z():\n    pass\n")
    (tmp_path / "README.md").write_text("new\n")
    detail = gate.check_existing_tests()
    assert detail.startswith("4 changed since v0.1.0")
    assert "tests/test_x.py::test_a changed" in detail
    assert "tests/snapshots/help.txt changed" in detail
    assert "test_added" not in detail
    assert "README" not in detail


def test_contract_summary() -> None:
    assert contract_summary(CONTRACT_RUN) == "4 cases from 3 consumers: 1 failed, 1 skipped (provider version)"
    assert contract_summary("") == "0 cases"
    passed = CONTRACT_RUN.replace("FAILED", "PASSED").replace("SKIPPED (windmill:old-field: provider <0.7)", "PASSED")
    assert contract_summary(passed) == "4 cases from 3 consumers"
    assert contract_summary(CONTRACT_RUN_XDIST) == contract_summary(CONTRACT_RUN)


CONTRACTS = """import pytest


@pytest.mark.parametrize("case", ["windmill:search", "astro:pages"])
def test_contract(case: str) -> None:
    assert case != "{failing}"
"""


def test_contracts_run_as_their_own_step(in_package) -> None:
    root = in_package('"""A demo package."""\n')
    gate = Gate(root)
    assert gate.check_contracts() == "none (tests/test_contracts.py doesn't exist)"

    (root / "tests" / "test_contracts.py").write_text(CONTRACTS.format(failing=""))
    assert gate.check_contracts() == "2 cases from 2 consumers"

    (root / "tests" / "test_contracts.py").write_text(CONTRACTS.format(failing="astro:pages"))
    with pytest.raises(StepFailed) as raised:
        gate.check_contracts()
    assert raised.value.output.splitlines()[0] == "2 cases from 2 consumers: 1 failed"
    assert "test_contract[astro:pages]" in raised.value.output


def test_install_section_missing_prints_the_default(tmp_path: Path) -> None:
    with pytest.raises(StepFailed) as raised:
        _pyproject(tmp_path, '[project]\nname = "x"\n').check_install_section()
    assert "tool.rb.install" in raised.value.output
    assert '[tool.rb.install]\nhomeserver = ["rbtools"]\nmac = true' in raised.value.output


@pytest.mark.parametrize(
    ("body", "named"),
    [
        ('homeserver = []\nmac = "yes"', ("mac", "bool")),
        ('homeserver = "rbtools"\nmac = true', ("homeserver", "list of user names")),
        ("homeserver = [1]\nmac = true", ("homeserver", "list of user names")),
        ('homeserver = [""]\nmac = true', ("homeserver", "list of user names")),
        ("homeserver = []", ("mac", "bool")),
        ("mac = true", ("homeserver", "list of user names")),
        ("homeserver = []\nmac = true\nextras = 'x'", ("extras", "list of strings")),
        ("homeserver = []\nmac = true\ntarget = 1", ("target", "unknown")),
    ],
)
def test_install_section_malformed_names_the_key(tmp_path: Path, body: str, named: tuple[str, str]) -> None:
    with pytest.raises(StepFailed) as raised:
        _pyproject(tmp_path, f"[tool.rb.install]\n{body}\n").check_install_section()
    assert all(word in raised.value.output for word in named)
    assert len(raised.value.output.splitlines()) == 1


def test_install_section_not_a_table_names_the_key(tmp_path: Path) -> None:
    with pytest.raises(StepFailed) as raised:
        _pyproject(tmp_path, '[tool.rb]\ninstall = "x"\n').check_install_section()
    assert all(word in raised.value.output for word in ("tool.rb.install", "table"))
    assert len(raised.value.output.splitlines()) == 1


@pytest.mark.parametrize(
    ("body", "ok"),
    [
        ("homeserver = []\nmac = false", "homeserver = [], mac = false"),
        (
            'homeserver = ["rbtools"]\nmac = true\nextras = ["x"]',
            "homeserver = ['rbtools'], mac = true, extras = ['x']",
        ),
    ],
)
def test_install_section_valid_passes(tmp_path: Path, body: str, ok: str) -> None:
    assert _pyproject(tmp_path, f"[tool.rb.install]\n{body}\n").check_install_section() == ok


@pytest.mark.skipif(shutil.which("gitleaks") is None, reason="gitleaks not installed")
def test_gate_stops_at_a_committed_secret(in_package) -> None:
    root = in_package('"""A demo package."""\n')
    (root / "settings.py").write_text(f'AWS_ACCESS_KEY_ID = "{FAKE_AWS_KEY}"\n')
    git(root, "add", "-A")
    git(root, "commit", "-qm", "settings")

    result = _check()

    assert result.exit_code == 1
    assert result.stdout.splitlines() == ["release: secret scan ... FAILED"]
    assert "release: gate step 'secret scan' failed" in result.stderr
    assert "aws-access-token" in result.stderr
    assert "settings.py" in result.stderr
    assert FAKE_AWS_KEY not in result.output
    assert result.stderr.strip().splitlines()[-1] == "release: code failed"


def test_scanners_skipped_when_not_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))  # neither gitleaks nor osv-scanner on it
    gate = Gate(tmp_path)
    assert gate.check_secrets() == "skipped: gitleaks not installed (brew install gitleaks)"
    assert gate.check_vulnerabilities() == "skipped: osv-scanner not installed (brew install osv-scanner)"


def test_a_vulnerable_lock_fails_the_audit_with_exit_3(
    in_package, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    in_package('"""A demo package."""\n')
    scanner = tmp_path / "bin" / "osv-scanner"  # a stand-in for the real scanner: it finds a vulnerability
    scanner.parent.mkdir()
    scanner.write_text("#!/bin/sh\necho 'GHSA-xxxx in demo-dep'\nexit 1\n")
    scanner.chmod(0o755)
    monkeypatch.setenv("PATH", f"{scanner.parent}{os.pathsep}{os.environ['PATH']}")

    result = _check()

    assert result.stdout.splitlines()[-1] == "release: vulnerability audit ... FAILED"
    assert "GHSA-xxxx in demo-dep" in result.stderr
    assert result.stderr.strip().splitlines()[-1] == "release: audit failed"
    assert result.exit_code == 3


SCRIPT = """
[project.scripts]
demo = "demo:main"
"""
SCRIPT_MODULE = '''"""A demo CLI."""

import importlib.metadata
import sys


def main() -> None:
    sys.stdout.write(importlib.metadata.version("demo") if "--version" in sys.argv else "usage: demo\\n")
'''


def test_the_built_wheel_runs_its_console_script(in_package) -> None:
    root = in_package(SCRIPT_MODULE, pyproject=PYPROJECT + SCRIPT)
    assert Gate(root).check_installed_wheel() == (
        "demo-0.1.0-py3-none-any.whl; `demo --version` = 0.1.0; `demo --help` ok"
    )

    (root / "src" / "demo" / "__init__.py").write_text(
        SCRIPT_MODULE.replace('importlib.metadata.version("demo")', '"9.9"')
    )
    with pytest.raises(StepFailed, match=re.escape("`demo --version` printed '9.9', but the wheel is version 0.1.0")):
        Gate(root).check_installed_wheel()


# --- fresh install: a new host resolves the dependencies from an index, never from uv.lock ------------------------

# Hand-built wheels: `uv tool install .` takes a dependency from a flat, explicit index offline (checked against
# uv 0.10), so the test needs neither the network nor a registry.
FAKEDEP_PYPROJECT = """[project]
name = "demo"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["fakedep>=1.0"]

[project.scripts]
demo = "demo:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[[tool.uv.index]]
name = "local"
url = "{index}"
format = "flat"
explicit = true

[tool.uv.sources]
fakedep = {{ index = "local" }}

[tool.rb.install]
homeserver = []
mac = false
"""
FAKEDEP_MODULE = '''"""A demo CLI that imports its dependency when it loads: `describe --json` answers its envelope."""

import importlib.metadata
import json
import sys

from fakedep import kept

def main() -> None:
    if "--version" in sys.argv:
        sys.stdout.write(importlib.metadata.version("demo"))
    elif "describe" in sys.argv:
        sys.stdout.write(json.dumps({"ok": True, "command": {"name": "demo"}, "kept": kept()}))
    else:
        sys.stdout.write(kept())
'''

# A CLI whose `describe --json` imports its dependency only when the command runs: the locked wheel keeps it working
# while the next minor of the dependency breaks it.
DESCRIBE_MODULE = '''"""A demo CLI whose `describe --json` imports its dependency when the command runs."""

import importlib.metadata
import json
import sys

def describe() -> str:
    from fakedep import kept

    return json.dumps({"ok": True, "command": {"name": "demo"}, "kept": kept()})

def main() -> None:
    if "--version" in sys.argv:
        sys.stdout.write(importlib.metadata.version("demo"))
    elif "describe" in sys.argv:
        sys.stdout.write(describe())
    else:
        sys.stdout.write("Usage: demo [OPTIONS] COMMAND [ARGS]...\\n")
'''

# A CLI without the Describe part: under --json the root group turns typer's "No such command" usage error into the
# INVALID_ARGUMENTS error envelope on stdout, exit 2 — stderr stays empty.
NO_DESCRIBE_MODULE = '''"""A demo CLI without the Describe part: `describe --json` is the INVALID_ARGUMENTS usage error."""

import importlib.metadata
import json
import sys

NO_SUCH_COMMAND = {
    "ok": False,
    "error": {"code": "INVALID_ARGUMENTS", "message": "No such command 'describe'."},
}

def main() -> None:
    if "--version" in sys.argv:
        sys.stdout.write(importlib.metadata.version("demo"))
    elif "describe" in sys.argv:
        sys.stdout.write(json.dumps(NO_SUCH_COMMAND))
        raise SystemExit(2)
    else:
        sys.stdout.write("Usage: demo [OPTIONS] COMMAND [ARGS]...\\n")
'''

# The same package as a library: no console script, so the fresh install has no tool to run.
FAKEDEP_LIBRARY_PYPROJECT = FAKEDEP_PYPROJECT.replace('[project.scripts]\ndemo = "demo:main"\n\n', "")
FAKEDEP_LIBRARY_MODULE = '''"""A demo library that imports its dependency when it loads."""

from fakedep import kept

VALUE = kept()
'''
# The library without an explicit index: a plain flat index keeps `uv lock` offline, and the library branch takes
# the dependency from UV_FIND_LINKS — `uv pip` reads none of the pyproject's index tables.
FAKEDEP_LIBRARY_PLAIN_PYPROJECT = FAKEDEP_LIBRARY_PYPROJECT.replace(
    'explicit = true\n\n[tool.uv.sources]\nfakedep = {{ index = "local" }}\n\n', ""
)


def _fake_dependency(index: Path, version: str, keeps_the_name: bool) -> None:
    """A fakedep wheel in the flat index `index`; 2.0.0 drops `kept`, which the demo CLI imports."""
    body = "def kept() -> str:\n    return 'kept'\n" if keeps_the_name else "VALUE = 2\n"
    with zipfile.ZipFile(index / f"fakedep-{version}-py3-none-any.whl", "w") as archive:
        archive.writestr("fakedep/__init__.py", body)
        metadata = f"Metadata-Version: 2.1\nName: fakedep\nVersion: {version}\n"
        archive.writestr(f"fakedep-{version}.dist-info/METADATA", metadata)
        wheel = "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        archive.writestr(f"fakedep-{version}.dist-info/WHEEL", wheel)
        archive.writestr(f"fakedep-{version}.dist-info/RECORD", "")


def test_a_dependency_minor_that_drops_an_imported_name_fails_the_fresh_install(
    in_package, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = tmp_path / "index"
    index.mkdir()
    _fake_dependency(index, "1.0.0", keeps_the_name=True)
    root = in_package(FAKEDEP_MODULE, pyproject=FAKEDEP_PYPROJECT.format(index=index))
    monkeypatch.setenv("UV_OFFLINE", "1")
    gate = Gate(root)
    assert gate.check_installed_wheel().startswith("demo-0.1.0-py3-none-any.whl; `demo --version` = 0.1.0")
    assert gate.check_fresh_install() == (
        "resolved from the index; `demo --version` = 0.1.0; `demo --help` ok; `demo describe --json` ok"
    )

    _fake_dependency(index, "2.0.0", keeps_the_name=False)  # the next minor drops what the CLI imports

    next_release = Gate(root)  # its own scratch: the locked wheel step still installs fakedep 1.0.0
    assert next_release.check_installed_wheel().startswith("demo-0.1.0-")
    with pytest.raises(StepFailed) as raised:
        next_release.check_fresh_install()
    assert "ImportError: cannot import name 'kept'" in raised.value.output


def test_a_describe_that_breaks_only_under_a_fresh_resolution_fails_the_fresh_install(
    in_package, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = tmp_path / "index"
    index.mkdir()
    _fake_dependency(index, "1.0.0", keeps_the_name=True)
    root = in_package(DESCRIBE_MODULE, pyproject=FAKEDEP_PYPROJECT.format(index=index))
    monkeypatch.setenv("UV_OFFLINE", "1")
    gate = Gate(root)
    assert gate.check_installed_wheel().startswith("demo-0.1.0-py3-none-any.whl; `demo --version` = 0.1.0")
    assert gate.check_fresh_install().endswith("`demo describe --json` ok")

    _fake_dependency(index, "2.0.0", keeps_the_name=False)  # the next minor drops what describe imports

    next_release = Gate(root)  # the locked wheel still carries fakedep 1.0.0, so its describe keeps working
    assert next_release.check_installed_wheel().startswith("demo-0.1.0-py3-none-any.whl; `demo --version` = 0.1.0")
    with pytest.raises(StepFailed) as raised:
        next_release.check_fresh_install()
    assert "`demo describe --json` gave no envelope" in raised.value.output
    assert "ImportError: cannot import name 'kept'" in raised.value.output


def test_the_fresh_install_names_an_absent_describe_and_stays_green(
    in_package, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = tmp_path / "index"
    index.mkdir()
    _fake_dependency(index, "1.0.0", keeps_the_name=True)
    root = in_package(NO_DESCRIBE_MODULE, pyproject=FAKEDEP_PYPROJECT.format(index=index))
    monkeypatch.setenv("UV_OFFLINE", "1")
    gate = Gate(root)
    gate.check_installed_wheel()
    assert gate.check_fresh_install() == (
        "resolved from the index; `demo --version` = 0.1.0; `demo --help` ok; "
        "`demo describe --json` absent (the Describe part is off)"
    )


def test_a_dependency_minor_that_drops_an_imported_name_fails_the_fresh_install_of_a_library(
    in_package, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = tmp_path / "index"
    index.mkdir()
    _fake_dependency(index, "1.0.0", keeps_the_name=True)
    root = in_package(FAKEDEP_LIBRARY_MODULE, pyproject=FAKEDEP_LIBRARY_PLAIN_PYPROJECT.format(index=index))
    # `uv pip install .` ignores the pyproject's index tables: this branch takes the dependency from find-links.
    monkeypatch.setenv("UV_FIND_LINKS", str(index))
    monkeypatch.setenv("UV_OFFLINE", "1")
    gate = Gate(root)
    assert gate.check_installed_wheel().startswith("demo-0.1.0-py3-none-any.whl; imports demo")
    assert gate.check_fresh_install().startswith("resolved from the index; imports demo")

    _fake_dependency(index, "2.0.0", keeps_the_name=False)

    next_release = Gate(root)
    assert next_release.check_installed_wheel().startswith("demo-0.1.0-")  # the lock still gives fakedep 1.0.0
    with pytest.raises(StepFailed) as raised:
        next_release.check_fresh_install()
    assert "ImportError: cannot import name 'kept'" in raised.value.output


def test_the_fresh_install_of_a_library_from_an_explicit_index_is_skipped_with_a_notice(
    in_package, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    index = tmp_path / "index"
    index.mkdir()
    _fake_dependency(index, "1.0.0", keeps_the_name=True)
    root = in_package(FAKEDEP_LIBRARY_MODULE, pyproject=FAKEDEP_LIBRARY_PYPROJECT.format(index=index))
    monkeypatch.setenv("UV_OFFLINE", "1")  # uv pip would reach PyPI, where a same-named package may live
    gate = Gate(root)
    gate.check_installed_wheel()
    assert gate.check_fresh_install() == (
        "skipped: `uv pip install .` cannot honour [tool.uv.sources] for fakedep from `local`"
    )


def test_our_package_installs_only_from_its_explicit_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _project_with_rb_x_from_gitea(tmp_path)
    monkeypatch.setenv("UV_OFFLINE", "1")

    python = _venv(tmp_path / "venv")
    Gate(tmp_path).install_locked(python)
    assert _rb_x_index(python) == "gitea"


def test_our_package_installed_from_pypi_fails(tmp_path: Path) -> None:
    _project_with_rb_x_from_gitea(tmp_path)
    python = _venv(tmp_path / "venv")
    pypi = ("--no-index", "--find-links", str(INDEXES / "pypi"))
    subprocess.run(["uv", "pip", "install", "--offline", "--quiet", "--python", str(python), *pypi, "rb-x"], check=True)  # noqa: S603, S607
    assert _rb_x_index(python) == "pypi"

    with pytest.raises(StepFailed) as raised:
        Gate(tmp_path).check_index_sources(python)
    assert raised.value.output == (
        "installed from a package index other than their explicit index: rb-x 0.9.0 (uv.lock: 0.1.0 from `gitea`)"
    )


def test_the_gate_ignores_its_own_virtualenv(monkeypatch) -> None:
    """Installed as a tool, the gate runs inside its own venv; the package's commands must not inherit it."""
    from rb_gate.gate import _clean_env

    monkeypatch.setenv("VIRTUAL_ENV", "/gate/venv")
    monkeypatch.setenv("PYTHONHOME", "/gate/python")
    monkeypatch.setenv("KEEP_ME", "1")
    env = _clean_env()
    assert "VIRTUAL_ENV" not in env and "PYTHONHOME" not in env
    assert env["KEEP_ME"] == "1"


def test_a_warning_on_stderr_is_not_the_version(tmp_path: Path) -> None:
    """A dependency that warns while importing must not make the release fail: the version comes from stdout."""
    script = tmp_path / "noisy"
    script.write_text('#!/bin/sh\necho "warn: deprecated" >&2\necho "1.2.3"\n', encoding="utf-8")
    script.chmod(0o755)
    gate = Gate(tmp_path)
    assert gate._printed_version(script) == "1.2.3"
