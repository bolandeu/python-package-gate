"""The Standard's mandatory rules, checked from outside: the gate's `standard: <step>` steps.

They run after the gate has built the wheel and installed it into a throwaway venv. A rule either probes the
installed console script (a library has none: those rules are skipped) or reads the package's files. A broken
rule raises Broken with what breaks it (the command, the file); the gate names the step and the section.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

# The Standard's table of exit codes (section Errors; in a template package: core/errors.py EXIT_CODES).
EXIT_CODES = frozenset(range(7))
UNKNOWN_OPTION = "--rb-gate-unknown-option"
NO_SCRIPT = "skipped: no console script, a library"
DOCS = ("README.md", "AGENTS.md")
FORGES = (".gitea/workflows/", ".github/workflows/")
GATE_COMMAND = "gate check"
# What a CI runner sets and Typer reads at import (forcing terminal output): the pytest step runs with them,
# every probe of the installed script runs without them.
CI_ENV = {"GITHUB_ACTIONS": "true", "FORCE_COLOR": "1", "PY_COLORS": "1"}

_USAGE = re.compile(r"^\s*Usage: (.*)$", re.MULTILINE)  # Typer and Click print the metavars untranslated
# Loose alone, strict together: a section counts only when every one of its entries is shaped like a command.
_SECTION_HEADING = re.compile(r"^(╭─ .+ ─|\S.*:$)")  # Typer's rich panel, Click's plain heading: in any language
_COMMAND_ENTRY = re.compile(r"\w\S*(\s{2}|$)")  # a name, then its help: not an option (`-…`, `*  -…`), not a message
_JSON_OPTION = re.compile(r"(?<![\w-])--json(?![\w-])")


class Broken(Exception):
    """The package breaks a mandatory rule; the message names the command or the file."""


def _entries(lines: Iterable[str]) -> list[str]:
    """The entries of the section whose heading was just read, up to its end; wrapped description lines are skipped."""
    entries: list[str] = []
    indent = None
    for line in lines:
        body = line.rstrip().removeprefix("│").removesuffix("│").rstrip()
        if not body.strip() or body.startswith("╰"):
            break
        depth = len(body) - len(body.lstrip())
        indent = depth if indent is None else indent
        if depth == indent:  # deeper: a wrapped description line
            entries.append(body.strip())
    return entries


def listed_commands(help_text: str) -> list[str]:
    """The names a group's help lists: the entries of every section whose entries are commands, under any title.

    A help is a group's when its usage line has the COMMAND metavar; any other help lists no commands. An entry
    named like a metavar of the usage line (`[IN]`, `CRAWL_ID`) is the group's own argument, never a command.
    """
    metavars = _usage_metavars(help_text)
    if "command" not in metavars:
        return []
    lines = help_text.splitlines()
    names: list[str] = []
    for number, line in enumerate(lines):
        entries = _entries(lines[number + 1 :]) if _SECTION_HEADING.match(line) else []
        if entries and all(_COMMAND_ENTRY.match(entry) for entry in entries):
            names += [name for name in (entry.split()[0] for entry in entries) if name.lower() not in metavars]
    return names


def _usage_metavars(help_text: str) -> set[str]:
    """The metavars of the help's usage line (`[OPTIONS] [IN] COMMAND`), lowercased, brackets stripped."""
    usage = _USAGE.search(help_text)
    words = (word.strip("[].") for word in usage.group(1).split()) if usage else ()
    return {word.lower() for word in words if word.isupper()}


@dataclass(frozen=True)
class Run:
    """One run of the console script: its command line, exit code and stdout."""

    command: str
    code: int
    stdout: str

    def __str__(self) -> str:
        return f"`{self.command}`"


def probe_env() -> dict[str, str]:
    """The environment for a run of the installed script: the gate's own, without the CI variables."""
    return {name: value for name, value in os.environ.items() if name not in CI_ENV}


class Package:
    """The package at `root` and the console script the gate installed from its wheel (None: a library)."""

    def __init__(self, root: Path, script: Path | None) -> None:
        self.root = root
        self.script = script

    def run(self, *args: str) -> Run:
        assert self.script is not None  # noqa: S101 - Rule.verify skips the CLI rules of a library
        result = subprocess.run(  # noqa: S603 - the script the gate has just installed
            [str(self.script), *args],
            cwd=self.root,
            env=probe_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        return Run(" ".join([self.script.name, *args]), result.returncode, result.stdout)

    def run_each(self, argvs: Iterable[tuple[str, ...]]) -> list[Run]:
        """Run the script once per argv, in parallel; the runs in the order of `argvs`."""
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as pool:
            return list(pool.map(lambda argv: self.run(*argv), argvs))

    @cached_property
    def bare(self) -> Run:
        return self.run()

    @cached_property
    def helps(self) -> dict[tuple[str, ...], Run]:
        """The `--help` run of every command and group the bare script lists, down through the groups."""
        found: dict[tuple[str, ...], Run] = {}
        level = [(name,) for name in listed_commands(self.bare.stdout)]
        while level:
            runs = self.run_each((*path, "--help") for path in level)
            found.update(zip(level, runs, strict=True))
            level = [
                (*path, name) for path, run in zip(level, runs, strict=True) for name in listed_commands(run.stdout)
            ]
        return found

    @cached_property
    def leaves(self) -> list[tuple[str, ...]]:
        """The commands that are not groups: their help lists no commands."""
        return [path for path, run in self.helps.items() if not listed_commands(run.stdout)]

    def command(self, path: tuple[str, ...]) -> str:
        assert self.script is not None  # noqa: S101 - Rule.verify skips the CLI rules of a library
        return f"`{' '.join([self.script.name, *path])}`"


def _in_table(run: Run) -> None:
    if run.code not in EXIT_CODES:
        raise Broken(
            f"{run} exits {run.code}: exit code {run.code} is not in the Standard's table "
            f"({min(EXIT_CODES)} to {max(EXIT_CODES)})"
        )


def _envelope(run: Run, name: str) -> dict:
    """stdout as the envelope: one JSON object, `ok` a bool; `ok: false` carries `error.code` and `error.message`."""
    try:
        payload = json.loads(run.stdout)
    except ValueError:
        payload = None
    if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
        raise Broken(f"{run} printed no {name} on stdout (a JSON object with `ok`): {run.stdout.strip()[:200]!r}")
    error = payload.get("error")
    fields = isinstance(error, dict) and all(isinstance(error.get(key), str) for key in ("code", "message"))
    if not payload["ok"] and not fields:
        raise Broken(f"{run} printed `ok: false` without `error.code` and `error.message` (the {name})")
    return payload


def check_commands(package: Package) -> str:
    bare = package.bare
    if bare.code:
        raise Broken(f"{bare} exits {bare.code}: with no arguments it lists the commands and exits 0")
    if not package.helps:
        raise Broken(f"{bare} lists no commands (no commands section in its output)")
    failing = [run for run in package.helps.values() if run.code]
    if failing:
        raise Broken(f"{failing[0]} exits {failing[0].code}: every command and group answers --help with exit 0")
    groups = len(package.helps) - len(package.leaves)
    return f"{len(package.leaves)} commands and {groups} groups answer --help"


def check_json(package: Package) -> str:
    if _JSON_OPTION.search(package.bare.stdout):
        return f"{len(package.leaves)} commands accept --json (the root lists it)"
    missing = [package.command(path) for path in package.leaves if not _JSON_OPTION.search(package.helps[path].stdout)]
    if missing:
        raise Broken(f"no --json in {', '.join(missing)}: every command accepts it (its --help or the root's lists it)")
    return f"{len(package.leaves)} commands accept --json"


def check_errors(package: Package) -> str:
    for run in package.run_each(("--json", *path, UNKNOWN_OPTION) for path in package.leaves):
        _in_table(run)
        if run.code != 2:
            raise Broken(f"{run} exits {run.code}: an unknown option is exit 2")
        if _envelope(run, "error envelope")["ok"]:
            raise Broken(f"{run} printed `ok: true`: the error envelope has `ok: false`")
    return f"an unknown option: exit 2 and the error envelope, in {len(package.leaves)} commands"


def check_health(package: Package) -> str:
    for path, report in ((("doctor",), None), (("auth", "status"), "credentials")):
        if path not in package.leaves:
            raise Broken(f"no {package.command(path)} command")
        run = package.run(*path, "--json")
        _in_table(run)
        payload = _envelope(run, "envelope")
        if report and not isinstance(payload.get(report), list):
            raise Broken(f"{run} printed no `{report}` list")
    return "doctor --json and auth status --json give the envelope"


def check_docs(package: Package) -> str:
    missing = [name for name in DOCS if not (package.root / name).is_file()]
    if missing:
        raise Broken(f"no {', '.join(missing)} in the package root")
    return ", ".join(DOCS)


# The Standard's closed list of parameter type names (Describe). A new name in the list is an additive change.
PARAM_TYPES = frozenset(
    {"boolean", "str", "int", "float", "choice", "path", "file", "datetime", "int range", "float range"}
)


def _described_commands(command: dict, path: tuple[str, ...] = ()) -> list[tuple[str, dict]]:
    """The document's command and every subcommand below it, each with its command line (`demo db push`)."""
    route = (*path, command["name"])
    return [(" ".join(route), command)] + [
        entry for sub in command.get("commands", []) for entry in _described_commands(sub, route)
    ]


def _param_problems(command: str, entry: dict) -> list[str]:
    """What breaks the Standard's rules for one parameter entry; `command` names the command the parameter is in."""
    meta = {item["name"]: item.get("value") for item in entry.get("metadata") or []}
    where = f"`{command} {entry['name']}`"
    problems: list[str] = []
    kind = meta.get("x-rb-type")
    if kind is None:
        problems.append(f"{where} has no x-rb-type")
    elif kind not in PARAM_TYPES:
        problems.append(f"{where}: x-rb-type {kind!r} is not one of: {', '.join(sorted(PARAM_TYPES))}")
    if "x-rb-default" not in meta:
        problems.append(f"{where} has no x-rb-default (null when the parameter has no default)")
    if "x-rb-multiple" in meta and meta["x-rb-multiple"] is not True:
        problems.append(f"{where}: x-rb-multiple is {meta['x-rb-multiple']!r}; it is true, or absent")
    return problems


def check_params(package: Package) -> str:
    """Every option and argument of `describe --json` names its type, its default and its repeatability."""
    if ("describe",) not in package.leaves:
        return "none: no describe command (the Describe part is off)"
    run = package.run("describe", "--json")
    if run.code:
        raise Broken(f"{run} exits {run.code}: the gate reads its option and argument entries")
    try:
        document = json.loads(run.stdout)
    except ValueError:
        raise Broken(f"{run} printed no JSON document on stdout") from None
    command = document.get("command") if isinstance(document, dict) else None
    if not isinstance(command, dict):
        raise Broken(f"{run} printed no `command` object")
    problems: list[str] = []
    entries = 0
    for name, described in _described_commands(command):
        for kind in ("options", "arguments"):
            for entry in described.get(kind, []):
                entries += 1
                problems += _param_problems(name, entry)
    if problems:
        raise Broken("the parameter entries of `describe --json` break these rules:\n  - " + "\n  - ".join(problems))
    return f"{entries} parameter entries carry a type, a default and their repeatability"


def check_ci(package: Package) -> str:
    for forge in FORGES:
        for path in sorted((package.root / forge).rglob("*")):
            if path.is_file() and path.suffix in (".yml", ".yaml"):
                lines = path.read_text(errors="replace").splitlines()
                if any(GATE_COMMAND in line and not line.lstrip().startswith("#") for line in lines):
                    raise Broken(f"{path.relative_to(package.root)} runs `{GATE_COMMAND}`: the gate runs locally")
    return "no workflow runs the gate: it runs locally"


@dataclass(frozen=True)
class Rule:
    """A mandatory rule: the gate's step `standard: <step>`, the Standard's section that states it, its check."""

    step: str
    section: str
    check: Callable[[Package], str]
    probes_cli: bool = True

    def verify(self, package: Package) -> str:
        """The step's detail line; raises Broken. A rule that probes the CLI is skipped for a library."""
        if self.probes_cli and package.script is None:
            return NO_SCRIPT
        return self.check(package)


RULES = (
    Rule("commands", "Commands", check_commands),
    Rule("json", "Output", check_json),
    Rule("errors", "Errors", check_errors),
    Rule("health", "Health", check_health),
    Rule("docs", "Docs", check_docs, probes_cli=False),
    Rule("params", "Describe", check_params),
    Rule("ci", "CI", check_ci, probes_cli=False),
)
