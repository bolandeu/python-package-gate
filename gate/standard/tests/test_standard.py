# ruff: noqa: RUF001 - the tests feed the gate help titled in Russian
"""The gate's `standard: <rule>` steps: `gate check` on a fixture CLI that meets every mandatory rule of the
Standard, and on copies of it that each break one rule (one change applied here)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from conftest import PYPROJECT
from rb_gate.cli import app
from standard import CI_ENV

STANDARD_STEPS = ["commands", "json", "errors", "health", "docs", "params", "ci"]
SCRIPT = """
[project.scripts]
demo = "demo:main"
"""
# A stdlib-only CLI: groups list their commands under `Commands:` (Click's plain help), leaf commands list
# their options, an unknown option is exit 2 and, with --json, the error envelope on stdout. Options before the
# command are the root's (ROOT_OPTIONS), options after it are the command's.
COMPLIANT = '''"""A demo CLI that meets the Standard's mandatory rules."""

import importlib.metadata
import json
import sys

COMMANDS = {
    "status": ("Show the status.", ["--json"]),
    "doctor": ("Run the diagnostic checks.", ["--json"]),
    "auth status": ("Report the credentials.", ["--json"]),
}
GROUPS = {"": "A demo CLI.", "auth": "Credentials."}
OUTPUT = {
    "status": {"ok": True},
    "doctor": {"ok": True, "checks": []},
    "auth status": {"ok": True, "credentials": []},
}
BARE_EXIT = 0
USAGE_EXIT = 2
ROOT_OPTIONS = ["--json"]


def children(group: str) -> dict[str, str]:
    """The commands and groups right under `group`, with their one-line help."""
    entries = {**{name: about for name, (about, _) in COMMANDS.items()}, **GROUPS}
    depth = len(group.split()) + 1
    return {
        name.split()[-1]: about
        for name, about in entries.items()
        if name.startswith(group) and len(name.split()) == depth
    }


def group_help(group: str) -> str:
    rows = "\\n".join(f"  {name}  {about}" for name, about in children(group).items())
    options = "".join(f"\\n  {option}" for option in ROOT_OPTIONS if not group)
    return f"Usage: demo {group} COMMAND\\n\\n{GROUPS[group]}\\n\\nCommands:\\n{rows}\\n" + (
        f"\\nOptions:{options}\\n" if options else ""
    )


def error(message: str, as_json: bool) -> int:
    if as_json:
        error = {"code": "INVALID_ARGUMENTS", "message": message}
        print(json.dumps({"ok": False, "error": error}))
    else:
        print(f"Error: {message}", file=sys.stderr)
    return USAGE_EXIT


def run(argv: list[str]) -> int:
    path = " ".join(arg for arg in argv if not arg.startswith("-"))
    options = [arg for arg in argv if arg.startswith("-")]
    start = argv.index(path.split()[0]) if path else len(argv)
    root, local = argv[:start], [arg for arg in argv[start:] if arg.startswith("-")]
    own = [*ROOT_OPTIONS, "--help", "--version"]
    rejected = [option for option in root if option not in own]
    if rejected:
        return error(f"No such option: {rejected[0]}", False)
    if "--version" in options:
        print(importlib.metadata.version("demo"))
        return 0
    if path in GROUPS:
        print(group_help(path))
        return 0 if options or path else BARE_EXIT
    if path not in COMMANDS:
        return error(f"No such command '{path}'.", "--json" in options)
    about, accepted = COMMANDS[path]
    unknown = [option for option in local if option not in [*accepted, "--help"]]
    if unknown:
        as_json = "--json" in root or "--json" in set(local) & set(accepted)
        return error(f"No such option: {unknown[0]}", as_json)
    if "--help" in options:
        rows = "\\n".join(f"  {option}" for option in [*accepted, "--help"])
        print(f"Usage: demo {path} [OPTIONS]\\n\\n{about}\\n\\nOptions:\\n{rows}")
        return 0
    print(json.dumps(OUTPUT[path]))
    return 0


def main() -> None:
    sys.exit(run(sys.argv[1:]))
'''


def _changed(old: str, new: str) -> str:
    """The compliant CLI with one change applied."""
    assert old in COMPLIANT, old
    return COMPLIANT.replace(old, new)


def _check(in_package, module: str = COMPLIANT, remove: str | None = None):
    root = in_package(module, pyproject=PYPROJECT + SCRIPT)
    if remove:
        (root / remove).unlink()
    return CliRunner().invoke(app, ["check"])


def _failed_at(result, step: str, section: str) -> str:
    """The failure output of a gate that stopped at `standard: <step>`, naming `section`."""
    assert result.stdout.splitlines()[-1] == f"release: standard: {step} ... FAILED", result.output
    assert f"release: gate step 'standard: {step}' failed:" in result.stderr
    assert f"Standard, section {section}:" in result.stderr, result.stderr
    assert result.stderr.strip().splitlines()[-1] == "release: code failed"
    assert result.exit_code == 1
    return result.stderr


def test_a_compliant_cli_passes_every_standard_step(in_package) -> None:
    result = _check(in_package)

    lines = result.stdout.splitlines()
    standard = [line for line in lines if line.startswith("release: standard: ")]
    assert [line.split(" ... ")[0] for line in standard] == [f"release: standard: {s}" for s in STANDARD_STEPS]
    assert all(line.split(" ... ")[1].startswith("ok") for line in standard), result.output
    assert lines[-1] == "release: gate passed"
    assert result.exit_code == 0


def test_a_bare_command_that_exits_2_fails_at_commands(in_package) -> None:
    result = _check(in_package, _changed("BARE_EXIT = 0", "BARE_EXIT = 2"))

    assert "`demo` exits 2" in _failed_at(result, "commands", "Commands")


def test_the_standard_steps_probe_the_cli_without_the_ci_variables(in_package, monkeypatch) -> None:
    for name, value in CI_ENV.items():
        monkeypatch.setenv(name, value)
    module = _changed("import json\n", "import json\nimport os\n")
    module = module.replace('    return f"Usage: demo {group}', '    text = f"Usage: demo {group}')
    module = module.replace(
        "\n\n\ndef error",
        '\n    bold = "\\x1b[1m" if os.environ.get("GITHUB_ACTIONS") else ""\n'
        '    return text.replace("\\n  ", "\\n  " + bold)\n\n\ndef error',
    )

    result = _check(in_package, module)

    assert "release: standard: commands ... ok" in result.stdout, result.output
    assert result.exit_code == 0, result.output


def test_a_bare_command_without_a_commands_section_fails_at_commands_under_the_ci_variables(
    in_package, monkeypatch
) -> None:
    for name, value in CI_ENV.items():
        monkeypatch.setenv(name, value)
    module = _changed("\\n\\nCommands:\\n{rows}", "{rows[:0]}")

    result = _check(in_package, module)

    assert "lists no commands" in _failed_at(result, "commands", "Commands")


def test_a_translated_plain_commands_heading_is_found(in_package) -> None:
    result = _check(in_package, _changed("\\n\\nCommands:", "\\n\\nКоманды:").replace("Options:", "Параметры:"))

    assert "release: standard: commands ... ok" in result.stdout, result.output
    assert "release: standard: health ... ok" in result.stdout, result.output


def _rich(commands: str, options: str) -> str:
    """The compliant CLI whose group help is Typer's rich panels, titled `commands` and `options`."""
    module = _changed("def group_help(group: str) -> str:", "def plain_group_help(group: str) -> str:")
    return module.replace(
        "def error(",
        f"""def group_help(group: str) -> str:
    rows = "\\n".join(f"│ {{name}}  {{about}} │" for name, about in children(group).items())
    panel = "╭─ {options} ─╮\\n│ --json │\\n╰─╯\\n" if not group else ""
    return f"Usage: demo {{group}} COMMAND\\n\\n" + panel + f"╭─ {commands} ─╮\\n{{rows}}\\n╰─╯\\n"


def error(""",
        1,
    )


@pytest.mark.parametrize(("commands", "options"), [("Commands", "Options"), ("Команды", "Параметры")])
def test_a_rich_commands_panel_is_found_in_english_and_translated(in_package, commands, options) -> None:
    result = _check(in_package, _rich(commands, options))

    assert result.exit_code == 0, result.output
    assert "release: standard: commands ... ok (3 commands and 1 groups answer --help)" in result.stdout, result.output
    assert "release: standard: health ... ok" in result.stdout


GROUP_USAGE = " Usage: demo [OPTIONS] COMMAND [ARGS]...\n\n"
LEAF_USAGE = " Usage: demo urls [OPTIONS] CRAWL_ID\n\n"


@pytest.mark.parametrize(
    ("options", "commands"), [("Options:", "Commands:"), ("Параметры:", "Команды:"), ("Параметры:", "Commands:")]
)
def test_the_plain_options_section_is_never_taken_for_commands(options, commands) -> None:
    from standard import listed_commands

    help_text = f"Usage: demo [OPTIONS] COMMAND [ARGS]...\n\n{commands}\n  status  Show.\n\n{options}\n  --json  Out.\n"

    assert listed_commands(help_text) == ["status"]


@pytest.mark.parametrize(("options", "commands"), [("Options", "Commands"), ("Параметры", "Команды")])
def test_the_rich_options_panel_is_never_taken_for_commands(options, commands) -> None:
    from standard import listed_commands

    panels = f"╭─ {options} ─╮\n│ --json  Out. │\n│ --help  Help. │\n╰─╯\n╭─ {commands} ─╮\n│ status  Show. │\n╰─╯\n"

    assert listed_commands(GROUP_USAGE + panels) == ["status"]


@pytest.mark.parametrize("arguments", ["Arguments", "Аргументы"])
def test_a_leaf_with_an_arguments_panel_lists_no_commands(arguments) -> None:
    from standard import listed_commands

    panels = f"╭─ {arguments} ─╮\n│ *  crawl_id  TEXT  [required] │\n╰─╯\n"
    required = "╭─ Options ─╮\n│ *  --issue  TEXT  Issue. [required] │\n│    --json        Out.             │\n╰─╯\n"

    assert listed_commands(LEAF_USAGE + panels + required) == []


def test_a_group_error_panel_lists_no_commands() -> None:
    from standard import listed_commands

    error = "Usage: demo [OPTIONS] COMMAND [ARGS]...\nTry 'demo --help' for help.\n"
    error += "╭─ Error ───────────────────╮\n│ No such command 'urlz'.   │\n╰───────────────────────────╯\n"

    assert listed_commands(error) == []


def test_a_group_lists_the_commands_of_every_translated_panel() -> None:
    from standard import listed_commands

    panels = "╭─ Параметры ─╮\n│ --help  Справка. │\n╰─╯\n"
    panels += "╭─ Обход ─╮\n│ crawl      Обойти.         │\n│ sitemaps   Карты сайта.    │\n╰─╯\n"
    panels += "╭─ Отчёты ─╮\n│ report     Отчёт по обходу │\n│            с переносом.    │\n╰─╯\n"

    assert listed_commands(GROUP_USAGE + panels) == ["crawl", "sitemaps", "report"]


def test_a_group_with_its_own_argument_lists_only_its_commands() -> None:
    from standard import listed_commands

    usage = " Usage: semkit read [OPTIONS] [IN] COMMAND [ARGS]...\n\n"
    panels = "╭─ Аргументы ─╮\n│ in  [IN]  Входной файл. │\n╰─╯\n"
    panels += "╭─ Параметры ─╮\n│ --help  Справка. │\n╰─╯\n"
    panels += "╭─ Команды ─╮\n│ csv   Прочитать CSV.  │\n│ xlsx  Прочитать XLSX. │\n╰─╯\n"

    assert listed_commands(usage + panels) == ["csv", "xlsx"]


def test_a_help_with_only_options_lists_no_commands() -> None:
    from standard import listed_commands

    assert listed_commands("Usage: demo [OPTIONS] COMMAND [ARGS]...\n\nOptions:\n  --json  Out.\n") == []


def test_a_command_without_json_fails_at_json(in_package) -> None:
    module = _changed('"status": ("Show the status.", ["--json"])', '"status": ("Show the status.", [])')
    module = module.replace('ROOT_OPTIONS = ["--json"]', "ROOT_OPTIONS = []")

    assert "`demo status`" in _failed_at(_check(in_package, module), "json", "Output")


def test_a_command_takes_json_listed_only_in_the_root_help(in_package) -> None:
    module = _changed('"status": ("Show the status.", ["--json"])', '"status": ("Show the status.", [])')

    result = _check(in_package, module)

    assert "release: standard: json ... ok" in result.stdout
    assert "release: standard: errors ... ok" in result.stdout, result.output
    assert result.exit_code == 0, result.output


def test_a_json_error_in_plain_text_fails_at_errors(in_package) -> None:
    module = _changed('print(json.dumps({"ok": False, "error": error}))', 'print(error["message"])')

    assert "error envelope" in _failed_at(_check(in_package, module), "errors", "Errors")


def test_an_exit_code_outside_the_table_fails_at_errors(in_package) -> None:
    result = _check(in_package, _changed("USAGE_EXIT = 2", "USAGE_EXIT = 7"))

    assert "exit code 7 is not in the Standard's table" in _failed_at(result, "errors", "Errors")


def test_a_cli_without_doctor_fails_at_health(in_package) -> None:
    result = _check(in_package, _changed('    "doctor": ("Run the diagnostic checks.", ["--json"]),\n', ""))

    assert "no `demo doctor` command" in _failed_at(result, "health", "Health")


def test_auth_status_without_credentials_fails_at_health(in_package) -> None:
    module = _changed('"auth status": {"ok": True, "credentials": []}', '"auth status": {"ok": True}')

    assert "`demo auth status --json`" in _failed_at(_check(in_package, module), "health", "Health")


@pytest.mark.parametrize("missing", ["README.md", "AGENTS.md"])
def test_a_package_without_its_docs_fails_at_docs(in_package, missing: str) -> None:
    assert missing in _failed_at(_check(in_package, remove=missing), "docs", "Docs")


def test_a_workflow_that_runs_the_gate_fails_at_ci(in_package) -> None:
    root = in_package(COMPLIANT, pyproject=PYPROJECT + SCRIPT)
    workflow = root / ".gitea" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on: push\njobs:\n  gate:\n    steps:\n      - run: uvx --from git+https://example.invalid/x.git gate check\n"
    )

    assert "the gate runs locally" in _failed_at(CliRunner().invoke(app, ["check"]), "ci", "CI")


def _meta(*pairs: tuple[str, object]) -> list[dict]:
    return [{"name": name, "value": value} for name, value in pairs]


def described() -> dict:
    """An OpenCLI document whose parameter entries meet the Standard's Describe rules."""
    return {
        "opencli": "0.1",
        "command": {
            "name": "demo",
            "options": [
                {"name": "--json", "metadata": _meta(("x-rb-type", "boolean"), ("x-rb-default", None))},
                {
                    "name": "--tag",
                    "metadata": _meta(("x-rb-type", "str"), ("x-rb-default", None), ("x-rb-multiple", True)),
                },
            ],
            "commands": [
                {
                    "name": "status",
                    "arguments": [
                        {"name": "target", "metadata": _meta(("x-rb-type", "path"), ("x-rb-default", "here"))}
                    ],
                }
            ],
        },
    }


def _describe(in_package, document: dict):
    """The gate over the compliant CLI plus a `describe` command that prints `document`."""
    module = _changed(
        '"auth status": ("Report the credentials.", ["--json"]),',
        '"auth status": ("Report the credentials.", ["--json"]),\n    "describe": ("Print the document.", ["--json"]),',
    )
    module = module.replace(
        "BARE_EXIT = 0",
        f"DOCUMENT = json.loads(\n    {json.dumps(document)!r}\n)\nBARE_EXIT = 0",
    )
    module = module.replace(
        "    if path not in COMMANDS:",
        '    if path == "describe":\n'
        '        unknown = [option for option in options if option not in ["--json", "--help"]]\n'
        "        if unknown:\n"
        '            return error(f"No such option: {unknown[0]}", True)\n'
        "        print(json.dumps(DOCUMENT))\n"
        "        return 0\n"
        "    if path not in COMMANDS:",
    )
    return _check(in_package, module)


def test_a_documented_parameter_entry_passes_at_params(in_package) -> None:
    result = _describe(in_package, described())

    assert (
        "release: standard: params ... ok (3 parameter entries carry a type, a default and their repeatability)"
        in result.stdout
    ), result.output
    assert result.exit_code == 0, result.output


def test_a_parameter_without_a_type_fails_at_params(in_package) -> None:
    document = described()
    document["command"]["options"][0]["metadata"] = _meta(("x-rb-default", None))

    assert "`demo --json` has no x-rb-type" in _failed_at(_describe(in_package, document), "params", "Describe")


def test_a_type_outside_the_list_fails_at_params(in_package) -> None:
    document = described()
    document["command"]["options"][1]["metadata"] = _meta(("x-rb-type", "uuid"), ("x-rb-default", None))

    assert "`demo --tag`: x-rb-type 'uuid' is not one of" in _failed_at(
        _describe(in_package, document), "params", "Describe"
    )


def test_a_parameter_without_a_default_fails_at_params(in_package) -> None:
    document = described()
    document["command"]["commands"][0]["arguments"][0]["metadata"] = _meta(("x-rb-type", "path"))

    assert "`demo status target` has no x-rb-default" in _failed_at(
        _describe(in_package, document), "params", "Describe"
    )


def test_a_single_parameter_marked_multiple_fails_at_params(in_package) -> None:
    document = described()
    document["command"]["options"][0]["metadata"].append({"name": "x-rb-multiple", "value": False})

    assert "`demo --json`: x-rb-multiple is False" in _failed_at(_describe(in_package, document), "params", "Describe")


def test_an_unrelated_workflow_that_only_mentions_the_gate_in_a_comment_passes(in_package) -> None:
    root = in_package(COMPLIANT, pyproject=PYPROJECT + SCRIPT)
    workflow = root / ".github" / "workflows" / "release.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on: push\n# never run gate check here\njobs:\n  release:\n    steps:\n      - run: echo release\n"
    )

    result = CliRunner().invoke(app, ["check"])

    assert result.exit_code == 0, result.output
    assert "release: standard: ci ... ok" in result.stdout


def test_a_workflow_one_level_deep_that_runs_the_gate_fails_at_ci(in_package) -> None:
    root = in_package(COMPLIANT, pyproject=PYPROJECT + SCRIPT)
    workflow = root / ".gitea" / "workflows" / "skip" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("on: push\njobs:\n  gate:\n    steps:\n      - run: gate check\n")

    assert "the gate runs locally" in _failed_at(CliRunner().invoke(app, ["check"]), "ci", "CI")


def test_a_library_without_a_console_script_skips_the_cli_rules(in_package) -> None:
    in_package('"""A demo library."""\n')

    result = CliRunner().invoke(app, ["check"])

    lines = {line.split(" ... ")[0]: line.split(" ... ")[1] for line in result.stdout.splitlines() if " ... " in line}
    for step in ("commands", "json", "errors", "health", "params"):
        assert lines[f"release: standard: {step}"] == "ok (skipped: no console script, a library)"
    assert result.exit_code == 0
