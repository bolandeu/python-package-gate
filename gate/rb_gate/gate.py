"""The release gate (`gate check`), run against any package.

Gate steps, in order — the first failure stops everything and prints that
step's name and output, then `release: code failed` (exit 1) or, when only
the vulnerability audit failed, `release: audit failed` (exit 3). With
`--keep-going` every step runs: a step that needs a failed step is skipped,
and after the last step the failed and skipped steps are listed before the
same verdict:

    secret scan (gitleaks over the git history; skipped with a notice when
    gitleaks isn't installed) · uv lock --check · ruff check ·
    ruff format --check · ty check · pytest ·
    contracts (tests/test_contracts.py: the consumers' cases from
    tests/contracts/<consumer>/*.yaml, run apart from pytest — a failing case
    stops the release and is named with its consumer) ·
    existing tests (never fails: lists every test that existed at the last tag
    and has since changed or gone — a changed or removed test function, changed
    module-level code of a test file, a changed snapshot or data file; each goes
    into the release report with its reason, the review rejects it without one) ·
    install section ([tool.rb.install] exists and is valid: homeserver a list
    of user names, mac a bool, extras an optional list of strings, no other key) ·
    external dependencies (every program src/ runs is declared in
    [[tool.rb.external]] and vice versa) ·
    build the wheel and install
    it into a throwaway venv with exactly the uv.lock dependency set (`uv sync
    --frozen`, then the wheel with --no-deps, then `uv pip check` — never
    resolving from an index, and every dependency [tool.uv.sources] takes from
    an explicit index must be installed as locked from there, so our
    packages can't be swapped for a same-named PyPI package),
    `<cli> --version` must print the version being
    built, `<cli> --help` must work (a library without a console script:
    every top-level package imports and importlib.metadata reports that
    version) ·
    fresh install (what a new host does tomorrow: `uv tool install .` into an
    empty tool directory of the gate's own, so the dependencies are resolved
    from the package index and never from uv.lock — `<cli> --version` must print
    the version being released, `<cli> --help` must work and `<cli> describe
    --json` must give its envelope (a package without the Describe part answers
    "No such command", which the step names and accepts); a library without a
    console script: `uv pip install .` into an empty venv, every top-level
    package must import — skipped with a notice when a dependency comes from
    an explicit index, which `uv pip` does not read from [tool.uv.sources]) · the Standard's mandatory rules (standard/: `standard: commands`,
    `json`, `errors`, `health` probe that installed console script, skipped for
    a library; `params` reads its `describe --json`; `docs`, `ci` read the package's files — a failure names the
    Standard's section) · osv-scanner over uv.lock (skipped with a
    notice when osv-scanner isn't installed)

Settings in the package's pyproject.toml `[tool.cli-generator]`:
`gate_extras = ["x"]` runs ruff/ty/pytest with those extras installed.
"""

from __future__ import annotations

import ast
import functools
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import standard
from standard import CI_ENV, probe_env

CONTRACT_TESTS = "tests/test_contracts.py"
COMMANDS = (
    ("uv lock --check", ("uv", "lock", "--check")),
    ("ruff check", ("uv", "run", "ruff", "check", ".")),
    ("ruff format --check", ("uv", "run", "ruff", "format", "--check", ".")),
    ("ty check", ("uv", "run", "ty", "check")),
    ("pytest", ("uv", "run", "pytest", f"--ignore={CONTRACT_TESTS}")),  # contracts: their own step
)
AUDIT_STEP = "vulnerability audit"
WHEEL_STEP = "build + install wheel"  # the Standard's steps that probe the CLI run its installed script
FRESH_INSTALL_STEP = "fresh install"  # the dependencies come from the index, as on a new host
EXIT_PASSED = 0
EXIT_CODE_FAILED = 1  # any code/packaging step: lock, lint, types, tests, wheel
EXIT_AUDIT_FAILED = 3  # only the osv-scanner audit: the code is fine, a dependency has a known vulnerability
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
DESCRIBE = ("describe", "--json")  # the consumer contract: a broken describe must not reach a tag
NO_SUCH_COMMAND = "No such command"  # typer's usage error (exit 2) for a package without the Describe part

Echo = Callable[..., None]  # typer.echo: (message, nl=True, err=False)


# What a package must not carry: somebody's machine, spelled as an address or as a path (Standard, Addresses and paths).
ADDRESS_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[a-z][a-z0-9+.-]*://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b"), "a local address"),
    (re.compile(r"[a-z][a-z0-9+.-]*://(?:[^/@\s]+@)?(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d"), "a private network address"),
    (re.compile(r"[a-z][a-z0-9+.-]*://[A-Za-z0-9.-]+\.(?:ts\.net|tailscale\.net|local)\b"), "a tailnet or LAN host"),
    (re.compile(r"""["'](?:/Users/[^"']+|/home/[^"']+|[A-Za-z]:\\\\Users[^"']*)["']"""), "an absolute path"),
)

class NotAPackage(Exception):
    """The gate was pointed at a directory without pyproject.toml: a usage error."""


class Step(NamedTuple):
    """One gate step: its name, what it runs, and the step whose success it needs (None: none)."""

    name: str
    run: Callable[[], str]
    needs: str | None = None


class StepFailed(Exception):
    def __init__(self, output: str) -> None:
        super().__init__(output)
        self.output = output


# --- what a step reads from its input alone ---------------------------------------


_PROCESS_CALLS = {"run", "Popen", "check_output", "check_call", "call"}


def external_programs(source: str) -> set[str]:
    """Programs a module runs or looks up by a literal name.

    `require_cli("x", ...)`, `shutil.which("x")`, and `subprocess.run(["x", ...])`
    (also Popen/check_output/check_call/call). A name built at runtime isn't
    seen — call `require_cli` with the literal name first, then run its path.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
        first = node.args[0]
        if func in ("require_cli", "which") and isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.add(first.value)
        elif func in _PROCESS_CALLS and isinstance(first, ast.List | ast.Tuple) and first.elts:
            head = first.elts[0]
            if isinstance(head, ast.Constant) and isinstance(head.value, str):
                found.add(head.value)
    return found


def _top_level(source: str) -> tuple[dict[str, str], list[str]]:
    """A test module's top-level functions and classes by name, and its other statements (imports aside)."""
    defs: dict[str, str] = {}
    rest: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            defs[node.name] = ast.dump(node)  # no line numbers: a moved test is not a changed one
        elif not isinstance(node, ast.Import | ast.ImportFrom):
            rest.append(ast.dump(node))
    return defs, rest


def changed_existing_tests(path: str, old: str, new: str | None) -> list[str]:
    """What of `path` as it was (`old`) is changed or gone in `new` (None: the file is deleted). New tests don't count."""
    if new is None:
        return [f"{path} removed"]
    if old == new:
        return []
    if not path.endswith(".py"):  # a snapshot, test data: the file as a whole
        return [f"{path} changed"]
    try:
        old_defs, old_rest = _top_level(old)
        new_defs, new_rest = _top_level(new)
    except SyntaxError:
        return [f"{path} changed"]
    found = [f"{path}: module-level code changed"] if any(stmt not in new_rest for stmt in old_rest) else []
    for name in sorted(old_defs):
        if name not in new_defs:
            found.append(f"{path}::{name} removed")
        elif new_defs[name] != old_defs[name]:
            found.append(f"{path}::{name} changed")
    return found


_CONTRACT_RESULT = re.compile(r"::test_contract\[([^\]]+)\] (PASSED|FAILED|SKIPPED|ERROR)")
# pytest-xdist -vv writes the status before the node id: `[gw0] [ 50%] PASSED tests/test_contracts.py::test_contract[x]`
_CONTRACT_RESULT_XDIST = re.compile(r"(PASSED|FAILED|SKIPPED|ERROR) \S*::test_contract\[([^\]]+)\]")


def contract_summary(output: str) -> str:
    """'N cases from K consumers' (+ failed / skipped) from a `pytest -vv` run of tests/test_contracts.py."""
    results = dict(_CONTRACT_RESULT.findall(output))
    results.update({case: status for status, case in _CONTRACT_RESULT_XDIST.findall(output)})
    if not results:
        return "0 cases"
    consumers = {case.split(":", 1)[0] for case in results}
    cases, sources = len(results), len(consumers)
    summary = f"{cases} case{'s' * (cases != 1)} from {sources} consumer{'s' * (sources != 1)}"
    failed = sum(status in ("FAILED", "ERROR") for status in results.values())
    skipped = sum(status == "SKIPPED" for status in results.values())
    notes = [f"{failed} failed"] * bool(failed) + [f"{skipped} skipped (provider version)"] * bool(skipped)
    return f"{summary}: {', '.join(notes)}" if notes else summary


def _json_object(text: str) -> dict | None:
    """`text` as a JSON object, or None: the envelope is an object, never a list or a bare value."""
    try:
        payload = json.loads(text)
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _names_no_such_command(output: str) -> bool:
    """A package without the Describe part: the usage error names no such command, whatever else the CLI does.

    Under `--json` the root group turns that usage error into the INVALID_ARGUMENTS envelope on stdout, so stderr
    stays empty; without the guard the same message goes to stderr. Either way the command is absent, not broken.
    The exit code is not read: a wrong one is the errors step's finding, not this step's.
    """
    return NO_SUCH_COMMAND in output


def _wheel_version(wheel: Path) -> str:
    """`Version:` from the wheel's METADATA — what importlib.metadata (and so `--version`) reports.

    Not the file name: it normalizes the local part (`+0814724` -> `+814724`).
    """
    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = archive.read(name).decode()
    return next(line.split(":", 1)[1].strip() for line in metadata.splitlines() if line.startswith("Version:"))


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# The defaults of copier.yml's `install_homeserver_users` and `install_mac`.
INSTALL_DEFAULT = """[tool.rb.install]
homeserver = ["rbtools"]
mac = true"""
INSTALL_KEYS = ("homeserver", "mac", "extras")


# --- the gate over one package ----------------------------------------------------


# The gate runs from its own tool environment (`uv tool install`): the package's commands must not inherit it,
# or `uv run` inside the package would pick the gate's venv instead of the project's.
_OWN_ENV = ("VIRTUAL_ENV", "VIRTUAL_ENV_PROMPT", "PYTHONHOME", "CONDA_PREFIX")


_UNREACHABLE = (
    "i/o timeout",
    "dial tcp",
    "connection refused",
    "connection reset",
    "no such host",
    "temporary failure in name resolution",
)


def _unreachable(output: str) -> bool:
    """The scanner could not reach its database: the release is not at fault."""
    return any(marker in output for marker in _UNREACHABLE)


def _clean_env() -> dict[str, str]:
    """The environment for the package's commands, without the gate's own interpreter."""
    return {key: value for key, value in os.environ.items() if key not in _OWN_ENV}


class Gate:
    """The gate steps over the package at `root`: the directory with its pyproject.toml."""

    def __init__(self, root: Path) -> None:
        self.root = root
        # The built wheel and its venv, kept for the whole run: the Standard's steps run the installed script.
        self._scratch = tempfile.TemporaryDirectory(prefix="rb-gate-")
        self.console_script: Path | None = None
        # What the wheel step built: the fresh install asks a new host's environment for the same version.
        self.wheel: Path | None = None
        self.release_version: str | None = None

    @classmethod
    def at(cls, root: Path) -> Gate:
        """The gate of the package at `root`; a directory without pyproject.toml is a usage error."""
        if not (root / "pyproject.toml").is_file():
            raise NotAPackage(f"No pyproject.toml in '{root}': run 'gate check' in the root directory of a package.")
        return cls(root)

    def _pyproject(self) -> dict:
        return tomllib.loads((self.root / "pyproject.toml").read_text())

    def _tool(self, name: str) -> dict:
        return self._pyproject().get("tool", {}).get(name, {})

    def gate_extras(self) -> list[str]:
        """`[tool.cli-generator] gate_extras`: optional-dependency extras the gate installs, so their tests run."""
        return list(self._tool("cli-generator").get("gate_extras", []))

    def _extra_args(self) -> list[str]:
        return [arg for extra in self.gate_extras() for arg in ("--extra", extra)]

    def git_output(self, *args: str) -> str:
        result = subprocess.run(args, cwd=self.root, check=True, text=True, capture_output=True)
        return result.stdout.strip()

    def step_output(self, *args: str, env: dict[str, str] | None = None) -> str:
        """Run one gate command; raise StepFailed with its combined output if it fails."""
        result = subprocess.run(
            args, cwd=self.root, text=True, capture_output=True, env=env or _clean_env(), check=False
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode:
            raise StepFailed(f"$ {' '.join(args)}\n{output}")
        return output

    def tags(self) -> list[tuple[int, int, int]]:
        result = subprocess.run(
            ["git", "tag", "--list", "v*"], cwd=self.root, text=True, capture_output=True, check=False
        )
        listed = result.stdout.split()  # not a git repo yet (fresh scaffold): no tags
        return sorted((int(m[1]), int(m[2]), int(m[3])) for t in listed if (m := TAG_RE.match(t)))

    # --- gate steps ------------------------------------------------------------

    def run_command(self, argv: tuple[str, ...]) -> str:
        if argv[:2] == ("uv", "run"):  # run lint/types/tests with the configured extras installed
            argv = ("uv", "run", *self._extra_args(), *argv[2:])
        env = {**_clean_env(), **CI_ENV} if "pytest" in argv else None
        self.step_output(*argv, env=env)
        return ""

    def _changed_since(self, tag: str) -> list[str]:
        """Files that differ from `tag`: committed, staged, unstaged and untracked."""
        tracked = self.git_output("git", "diff", "--name-only", tag).splitlines()
        untracked = self.git_output("git", "ls-files", "--others", "--exclude-standard").splitlines()
        return sorted(set(tracked + untracked))

    def check_external_deps(self) -> str:
        """Every external program used in src/ is declared in [[tool.rb.external]], and every declared one is used."""
        entries = self._tool("rb").get("external", [])
        problems = [
            f"entry #{i + 1} needs `name` and `why`"
            for i, e in enumerate(entries)
            if not (e.get("name") and e.get("why"))
        ]
        declared = {entry.get("name") for entry in entries}
        used: dict[str, list[str]] = {}
        for path in sorted((self.root / "src").rglob("*.py")):
            for name in external_programs(path.read_text()):
                used.setdefault(name, []).append(str(path.relative_to(self.root)))
        problems += [
            f"`{name}` is run in {', '.join(files)} but not declared"
            for name, files in used.items()
            if name not in declared
        ]
        # detect = false: run in a way this scan can't see (an injected runner, an
        # absolute path) — declared on trust, but still with a `why`.
        hidden = {entry.get("name") for entry in entries if entry.get("detect", True) is False}
        unseen = sorted(declared - used.keys() - hidden)
        problems += [
            f"`{name}` is declared but nothing in src/ runs it (set detect = false if it's run in a way the gate "
            "can't see, e.g. an injected runner or an absolute path)"
            for name in unseen
        ]
        if problems:
            raise StepFailed(
                "pyproject.toml [[tool.rb.external]] doesn't match the code (the Standard, Technology):\n  - "
                + "\n  - ".join(problems)
                + '\nDeclare: [[tool.rb.external]] name = "x", required = true, min_version = "1.0", check = "x --version", why = "..."'
            )
        if not declared:
            return "none used, none declared"
        return f"{len(declared)} declared, all used" + (f" ({len(hidden)} with detect = false)" if hidden else "")

    def check_install_section(self) -> str:
        """`[tool.rb.install]` exists and is valid: no package is released without an install declaration."""
        install = self._tool("rb").get("install")
        if install is None:
            raise StepFailed(f"pyproject.toml has no [tool.rb.install]; add:\n{INSTALL_DEFAULT}")
        if not isinstance(install, dict):
            raise StepFailed(f"pyproject.toml [tool.rb.install] must be a table, not {type(install).__name__}")
        users, mac, extras = install.get("homeserver"), install.get("mac"), install.get("extras", [])
        problems = [
            f"`{key}` is unknown (allowed: {', '.join(INSTALL_KEYS)})" for key in install if key not in INSTALL_KEYS
        ]
        if not (isinstance(users, list) and all(isinstance(user, str) and user for user in users)):
            problems.append("`homeserver` must be a list of user names (non-empty strings, may be empty)")
        if not isinstance(mac, bool):
            problems.append("`mac` must be a bool (true or false)")
        if not (isinstance(extras, list) and all(isinstance(extra, str) for extra in extras)):
            problems.append("`extras` must be a list of strings")
        if problems:
            raise StepFailed(f"pyproject.toml [tool.rb.install]: {problems[0]}")
        return f"homeserver = {users}, mac = {str(mac).lower()}" + (f", extras = {extras}" if extras else "")

    def check_addresses(self) -> str:
        """`src/` names no machine of a person: such an address comes from a setting, not from the package.

        An occurrence that is right on purpose — an OAuth loopback redirect, a pattern that looks for such links in
        crawled pages, an example in the help — is listed in `[tool.rb.gate] addresses_allow` with its reason:
        `{ pattern = "http://localhost:", reason = "OAuth loopback redirect" }`. The reason is what a reviewer reads.
        """
        found: list[str] = []
        waived = 0
        scanned = 0
        allowed = self._allowed_addresses()
        for path in sorted(self.root.glob("src/**/*.py")):
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                for pattern, kind in ADDRESS_PATTERNS:
                    match = pattern.search(line)
                    if not match:
                        continue
                    if any(snippet in line for snippet in allowed):
                        waived += 1
                        continue
                    found.append(f"{path.relative_to(self.root)}:{number}: {kind} {match.group(0)[:100]}")
                    break
        if found:
            hint = (
                "Name it in a setting instead: <TOOL>_<NAME>_URL or <TOOL>_<NAME>_PATH, and fail with a clear "
                "INVALID_ARGUMENTS naming it when the value is missing (Standard, Addresses and paths)."
            )
            raise StepFailed("\n".join([*found, "", hint]))
        return f"{scanned} files scanned" + (f", {waived} allowed by [tool.rb.gate]" if waived else "")

    def _allowed_addresses(self) -> list[str]:
        """The snippets `[tool.rb.gate] addresses_allow` lets through, each one with a reason next to it."""
        entries = self._tool("rb").get("gate", {}).get("addresses_allow", [])
        if not isinstance(entries, list):
            raise StepFailed("pyproject.toml [tool.rb.gate] addresses_allow must be a list of { pattern, reason }")
        patterns = []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("pattern"), str) or not entry.get("reason"):
                raise StepFailed(
                    f"pyproject.toml [tool.rb.gate] addresses_allow: {entry!r} needs a `pattern` and a `reason`"
                )
            patterns.append(entry["pattern"])
        return patterns

    def check_existing_tests(self) -> str:
        """Tests the last release had that are changed or gone now: a test is not edited to fit the code.

        Never fails — a requirement can change. The list goes into the release
        report, each entry with its reason (TDD).
        """
        versions = self.tags()
        if not versions:
            return "no release tag yet"
        last = "v{}.{}.{}".format(*versions[-1])
        found: list[str] = []
        for path in self._changed_since(last):
            if not path.startswith("tests/"):
                continue
            old = subprocess.run(["git", "show", f"{last}:{path}"], cwd=self.root, capture_output=True, check=False)
            if old.returncode:  # added since the tag
                continue
            current = self.root / path
            new = current.read_text(errors="replace") if current.is_file() else None
            found += changed_existing_tests(path, old.stdout.decode(errors="replace"), new)
        if not found:
            return f"none changed since {last}"
        listed = "\n  ".join(found)
        return f"{len(found)} changed since {last} — put each in the release report with its reason:\n  {listed}"

    def check_contracts(self) -> str:
        """The consumers' contract cases, as their own gate step: any failure stops the release."""
        if not (self.root / CONTRACT_TESTS).is_file():
            return f"none ({CONTRACT_TESTS} doesn't exist)"
        argv = ["uv", "run", *self._extra_args(), "pytest", CONTRACT_TESTS]
        argv += ["-vv", "--no-cov", "-p", "no:cacheprovider", "-rfE", "--tb=no"]  # -vv: the reason is not cut off
        result = subprocess.run(argv, cwd=self.root, text=True, capture_output=True, check=False, env=probe_env())
        output = (result.stdout + result.stderr).strip()
        summary = contract_summary(output)
        if result.returncode not in (0, 5):  # 5: no case collected
            failures = [line for line in output.splitlines() if line.startswith(("FAILED", "ERROR"))]
            raise StepFailed(f"{summary}\n" + "\n".join(failures or [output]))
        return summary

    def check_secrets(self) -> str:
        """No key, token or password anywhere in the git history (gitleaks; `--redact`: the value is never printed)."""
        scanner = shutil.which("gitleaks")
        if scanner is None:
            return "skipped: gitleaks not installed (brew install gitleaks)"
        self.step_output(scanner, "git", "--redact", "--verbose", "--no-banner", "--no-color", str(self.root))
        return "no secrets in the git history"

    def check_vulnerabilities(self) -> str:
        scanner = shutil.which("osv-scanner")
        if scanner is None:
            return "skipped: osv-scanner not installed (brew install osv-scanner)"
        for attempt in (1, 2):
            try:
                self.step_output(scanner, "--lockfile=uv.lock")
                return "no known vulnerabilities in uv.lock"
            except StepFailed as exc:
                # The scanner asks api.osv.dev: a timeout is the network, not a finding, and one retry
                # keeps a flaky resolver from blocking a release that has nothing to fix.
                if attempt == 1 and _unreachable(str(exc)):
                    time.sleep(2)
                    continue
                raise
        return "no known vulnerabilities in uv.lock"  # unreachable: the loop returns or raises

    def _wheel_tops(self, wheel: Path) -> list[str]:
        """The top-level packages a wheel carries: one per module or package directory."""
        with zipfile.ZipFile(wheel) as archive:
            return sorted(
                {
                    name.split("/")[0].removesuffix(".py")
                    for name in archive.namelist()
                    if not name.split("/")[0].endswith((".dist-info", ".data"))
                    and (name.endswith(".py") or "/" in name)
                }
            )

    def _check_library(self, python: Path, tops: list[str], dist: str, built: str) -> str:
        """No console script (a library): import every top-level package, compare importlib.metadata's version."""
        code = (
            "import importlib, importlib.metadata as m\n"
            f"for name in {tops!r}: importlib.import_module(name)\n"
            f"print(m.version({dist!r}))"
        )
        reported = self.step_output(str(python), "-c", code).splitlines()[-1].strip()
        if reported != built:
            raise StepFailed(f"importlib.metadata.version({dist!r}) is {reported!r}, but the wheel is version {built}")
        return f"imports {', '.join(tops)}; importlib.metadata version = {reported}"

    def _printed_version(self, exe: Path) -> str:
        """What a console script prints for `--version`: the last line of stdout, where Typer prints it.

        Only stdout: a dependency may warn on stderr while importing (pandas does), and that warning is
        not the version. A warning must not turn a correct install into a failed release.
        """
        result = subprocess.run([str(exe), "--version"], env=probe_env(), capture_output=True, text=True, check=False)
        if result.returncode:
            raise StepFailed(f"$ {exe} --version\n{(result.stdout + result.stderr).strip()}")
        printed = result.stdout.splitlines()
        return printed[-1].strip() if printed else ""

    def _fresh_describe(self, script: str, exe: Path) -> str:
        """`<cli> describe --json` on the installed script: its envelope, or the command being absent.

        describe is the consumers' contract (they build their schemas from it), so a describe that only
        the fresh resolution breaks fails this step. A package without the Describe part answers typer's
        "No such command" usage error, which is not a failure: the command is absent, not broken.
        """
        result = subprocess.run(
            [str(exe), *DESCRIBE],
            env=probe_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        command = f"`{script} {' '.join(DESCRIBE)}`"
        if _names_no_such_command(result.stdout + result.stderr):
            return f"{command} absent (the Describe part is off)"
        payload = _json_object(result.stdout)
        if payload is None or payload.get("ok") is False or not isinstance(payload.get("command"), dict):
            output = (result.stdout + result.stderr).strip()
            raise StepFailed(f"{command} gave no envelope (a JSON object with `ok` and `command`):\n{output}")
        return f"{command} ok"

    def _explicit_sources(self) -> dict[str, str]:
        """The dependencies [tool.uv.sources] takes from an index marked explicit, by name, with that index."""
        uv = self._tool("uv")
        explicit = {index["name"] for index in uv.get("index", []) if index.get("explicit")}
        return {
            _normalized(name): source["index"]
            for name, source in uv.get("sources", {}).items()
            if isinstance(source, dict) and source.get("index") in explicit
        }

    def check_index_sources(self, python: Path) -> None:
        """Every dependency [tool.uv.sources] takes from an explicit index is installed as uv.lock locked it from there."""
        pinned = self._explicit_sources()
        if not pinned:
            return
        lock = tomllib.loads((self.root / "uv.lock").read_text())
        locked = {package["name"]: package["version"] for package in lock["package"] if package["name"] in pinned}
        code = (
            "import importlib.metadata as m\n"
            f"for name in {sorted(pinned)!r}:\n"
            "    try: print(name, m.version(name))\n"
            "    except m.PackageNotFoundError: pass"  # not in the installed set (an extra): nothing to check
        )
        installed = dict(line.split() for line in self.step_output(str(python), "-c", code).splitlines())
        wrong = [
            f"{name} {version} (uv.lock: {locked.get(name)} from `{pinned[name]}`)"
            for name, version in sorted(installed.items())
            if version != locked.get(name)
        ]
        if wrong:
            raise StepFailed(f"installed from a package index other than their explicit index: {', '.join(wrong)}")

    def install_locked(self, python: Path) -> None:
        """Install exactly uv.lock's dependency set into the venv of `python`, each package from its locked source.

        Never `uv pip install <wheel>` or an exported requirements file: neither
        carries [tool.uv.sources], so our packages (rb-x from the explicit Gitea
        index) would be resolved from PyPI — where an unrelated package of the
        same name may live (dependency confusion).
        """
        env = {**_clean_env(), "UV_PROJECT_ENVIRONMENT": str(python.parent.parent)}
        self.step_output("uv", "sync", "--frozen", "--no-dev", "--no-install-project", "--quiet", env=env)
        self.check_index_sources(python)

    def check_installed_wheel(self) -> str:
        """Build the wheel, install it into a throwaway venv, run the CLI."""
        project = self._pyproject()["project"]
        script = next(iter(project.get("scripts", {})), None)
        dist, venv = Path(self._scratch.name) / "dist", Path(self._scratch.name) / "venv"
        self.step_output("uv", "build", "--wheel", "--out-dir", str(dist))
        wheel = next(dist.glob("*.whl"))
        built = _wheel_version(wheel)
        if self.tags() and built.startswith("0.0.0"):
            raise StepFailed(f"built version {built}: the build saw no v* tag (uv-dynamic-versioning fell back)")
        self.wheel, self.release_version = wheel, built
        self.step_output("uv", "venv", "--quiet", str(venv))
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        # The locked set, then the wheel without resolving anything, then
        # check the wheel's requirements are met by what's installed.
        self.install_locked(python)
        self.step_output("uv", "pip", "install", "--quiet", "--no-deps", "--python", str(python), str(wheel))
        self.step_output("uv", "pip", "check", "--python", str(python))
        if script is None:
            tops = self._wheel_tops(wheel)
            return f"{wheel.name}; {self._check_library(python, tops, project['name'], built)}"
        exe = python.parent / (f"{script}.exe" if os.name == "nt" else script)
        reported = self._printed_version(exe)
        if reported != built:
            raise StepFailed(f"`{script} --version` printed {reported!r}, but the wheel is version {built}")
        self.step_output(str(exe), "--help", env=probe_env())
        self.console_script = exe
        return f"{wheel.name}; `{script} --version` = {reported}; `{script} --help` ok"

    def check_fresh_install(self) -> str:
        """Install the package the way a new host does: an empty environment, the dependencies resolved from the index.

        The wheel step installs exactly uv.lock's set and never resolves, so it stays green while a
        dependency's next minor release breaks every fresh install of a released package. This step
        resolves as that install does, in the gate's own scratch: the user's tools stay untouched.
        What it guarantees: the package as a new host would resolve it imports and reports its version, with
        `[tool.uv.sources]` honoured (a tool) or not (a library). A library's dependencies come from the index
        list of the machine, which `uv pip install .` cannot take from [tool.uv.sources]: a library that takes
        a dependency from an explicit index is skipped with a notice, never reported as resolved from there.
        """
        if self.wheel is None or self.release_version is None:
            raise StepFailed(f"the fresh install needs the version '{WHEEL_STEP}' built")
        project = self._pyproject()["project"]
        script = next(iter(project.get("scripts", {})), None)
        scratch = Path(self._scratch.name)
        if script is None:  # a library: no tool to install, a venv of its own
            pinned = self._explicit_sources()
            if pinned:  # `uv pip install .` ignores [tool.uv.sources], and PyPI may hold a same-named package
                sources = ", ".join(f"{name} from `{index}`" for name, index in sorted(pinned.items()))
                return f"skipped: `uv pip install .` cannot honour [tool.uv.sources] for {sources}"
            venv = scratch / "fresh-venv"
            self.step_output("uv", "venv", "--quiet", str(venv))
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            self.step_output("uv", "pip", "install", "--quiet", "--python", str(python), str(self.root))
            detail = self._check_library(python, self._wheel_tops(self.wheel), project["name"], self.release_version)
            return f"resolved from the index; {detail}"
        tool_dir = scratch / "tools"
        env = {**_clean_env(), "UV_TOOL_DIR": str(tool_dir), "UV_TOOL_BIN_DIR": str(scratch / "tools-bin")}
        self.step_output("uv", "tool", "install", "--quiet", str(self.root), env=env)
        exe = Path(env["UV_TOOL_BIN_DIR"]) / (f"{script}.exe" if os.name == "nt" else script)
        reported = self._printed_version(exe)
        if reported != self.release_version:
            raise StepFailed(
                f"`{script} --version` printed {reported!r}, but the release is version {self.release_version}"
            )
        self.step_output(str(exe), "--help", env=probe_env())
        described = self._fresh_describe(script, exe)
        return f"resolved from the index; `{script} --version` = {reported}; `{script} --help` ok; {described}"

    @functools.cached_property
    def _standard_package(self) -> standard.Package:
        return standard.Package(self.root, self.console_script)

    def check_standard(self, rule: standard.Rule) -> str:
        """One mandatory rule of the Standard, checked on the console script the wheel step installed."""
        try:
            return rule.verify(self._standard_package)
        except standard.Broken as exc:
            raise StepFailed(f"Standard, section {rule.section}: {exc}") from exc

    def steps(self) -> list[Step]:
        return [
            Step("secret scan", self.check_secrets),
            *(Step(name, lambda argv=argv: self.run_command(argv)) for name, argv in COMMANDS),
            Step("contracts", self.check_contracts),
            Step("addresses", self.check_addresses),
            Step("existing tests", self.check_existing_tests),
            Step("install section", self.check_install_section),
            Step("external dependencies", self.check_external_deps),
            Step(WHEEL_STEP, self.check_installed_wheel),
            Step(FRESH_INSTALL_STEP, self.check_fresh_install, WHEEL_STEP),
            *(
                Step(
                    f"standard: {rule.step}",
                    lambda rule=rule: self.check_standard(rule),
                    WHEEL_STEP if rule.probes_cli else None,
                )
                for rule in standard.RULES
            ),
            Step(AUDIT_STEP, self.check_vulnerabilities),
        ]

    def run_steps(self, echo: Echo, keep_going: bool = False) -> int:
        """Run the steps, one `release: <step> ...` line each; the exit code: 0 passed, 1 code failed, 3 audit failed.

        Without `keep_going` the first failed step ends the run; with it every step runs.
        """
        with self._scratch:
            return self._run_steps(echo, keep_going)

    def _run_steps(self, echo: Echo, keep_going: bool) -> int:
        failed: list[str] = []
        skipped: list[str] = []
        for step in self.steps():
            echo(f"release: {step.name} ... ", nl=False)
            if step.needs in failed or step.needs in skipped:
                echo(f"skipped (needs '{step.needs}')")
                skipped.append(step.name)
                continue
            try:
                detail = step.run()
            except StepFailed as exc:
                echo("FAILED")
                echo(f"\nrelease: gate step '{step.name}' failed:\n{exc.output}", err=True)
                failed.append(step.name)
                if not keep_going:
                    break
                continue
            echo(f"ok ({detail})" if detail else "ok")
        if not failed:
            echo("release: gate passed")
            return EXIT_PASSED
        if keep_going:
            echo(f"release: failed steps: {', '.join(failed)}", err=True)
            if skipped:
                echo(f"release: skipped steps: {', '.join(skipped)}", err=True)
        # Last line + exit code tell whoever runs the gate (an agent, CI) whether
        # the code is broken or only a dependency needs a security bump.
        audit = failed == [AUDIT_STEP]
        echo(f"release: {'audit' if audit else 'code'} failed", err=True)
        return EXIT_AUDIT_FAILED if audit else EXIT_CODE_FAILED
